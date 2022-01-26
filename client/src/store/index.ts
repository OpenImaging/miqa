/* eslint-disable no-use-before-define */

import { createDirectStore } from 'direct-vuex';
import Vue from 'vue';
import Vuex from 'vuex';
import vtkProxyManager from 'vtk.js/Sources/Proxy/Core/ProxyManager';
import { InterpolationType } from 'vtk.js/Sources/Rendering/Core/ImageProperty/Constants';

import '../utils/registerReaders';

import readImageArrayBuffer from 'itk/readImageArrayBuffer';
import WorkerPool from 'itk/WorkerPool';
import ITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper';
import djangoRest, { apiClient } from '@/django';
import {
  Project, ProjectTaskOverview, User, Frame, ScanState,
} from '@/types';
import ReaderFactory from '../utils/ReaderFactory';

import { proxy } from '../vtk';
import { getView } from '../vtk/viewManager';

const { convertItkToVtkImage } = ITKHelper;

Vue.use(Vuex);

const fileCache = new Map();
const frameCache = new Map();
let readDataQueue = [];
const pendingFrameDownloads = new Set();
const poolSize = Math.floor(navigator.hardwareConcurrency / 2) || 2;
let taskRunId = -1;
let savedWorker = null;

const actiontime = 1800000; // 30 minute no action timeout

function shrinkProxyManager(proxyManager) {
  proxyManager.getViews().forEach((view) => {
    view.setContainer(null);
    proxyManager.deleteProxy(view);
  });
}

function prepareProxyManager(proxyManager) {
  if (!proxyManager.getViews().length) {
    ['View2D_Z:z', 'View2D_X:x', 'View2D_Y:y'].forEach((type) => {
      const view = getView(proxyManager, type);
      view.setOrientationAxesVisibility(false);
      view.getRepresentations().forEach((representation) => {
        representation.setInterpolationType(InterpolationType.NEAREST);
        representation.onModified(() => {
          view.render(true);
        });
      });
    });
  }
}

function prepareScreenshotViews(proxyManager) {
  ['ScreenshotView2D_x:x', 'ScreenshotView2D_y:y', 'ScreenshotView2D_z:z'].forEach((type) => {
    getView(proxyManager, type, null);
  });
}

function getArrayName(filename) {
  const idx = filename.lastIndexOf('.');
  const name = idx > -1 ? filename.substring(0, idx) : filename;
  return `Scalars ${name}`;
}

function getData(id, file, webWorker = null) {
  return new Promise((resolve, reject) => {
    if (frameCache.has(id)) {
      resolve({ frameData: frameCache.get(id), webWorker });
    } else {
      const fileName = file.name;
      const io = new FileReader();

      io.onload = function onLoad() {
        readImageArrayBuffer(webWorker, io.result, fileName)
          .then(({ webWorker, image }) => { // eslint-disable-line no-shadow
            const frameData = convertItkToVtkImage(image, {
              scalarArrayName: getArrayName(fileName),
            });
            const dataRange = frameData
              .getPointData()
              .getArray(0)
              .getRange();
            frameCache.set(id, { frameData });
            // eslint-disable-next-line no-use-before-define
            expandScanRange(id, dataRange);
            resolve({ frameData, webWorker });
          })
          .catch((error) => {
            console.log('Problem reading image array buffer');
            console.log('webworker', webWorker);
            console.log('fileName', fileName);
            console.log(error);
            reject(error);
          });
      };

      io.readAsArrayBuffer(file);
    }
  });
}

function loadFile(frameId, frameExtension, { onDownloadProgress = null } = {}) {
  if (fileCache.has(frameId)) {
    return { frameId, fileP: fileCache.get(frameId) };
  }
  const { promise } = ReaderFactory.downloadFrame(
    apiClient,
    `image${frameExtension}`,
    `/frames/${frameId}/download`,
    { onDownloadProgress },
  );
  fileCache.set(frameId, promise);
  return { frameId, fileP: promise };
}

function loadFileAndGetData(frameId, frameExtension, { onDownloadProgress = null } = {}) {
  const loadResult = loadFile(frameId, frameExtension, { onDownloadProgress });
  return loadResult.fileP.then((file) => getData(frameId, file, savedWorker)
    .then(({ webWorker, frameData }) => {
      savedWorker = webWorker;
      return Promise.resolve({ frameData });
    })
    .catch((error) => {
      const msg = 'loadFileAndGetData caught error getting data';
      console.log(msg);
      console.log(error);
      return Promise.reject(msg);
    })
    .finally(() => {
      if (savedWorker) {
        savedWorker.terminate();
        savedWorker = null;
      }
    }));
}

function poolFunction(webWorker, taskInfo) {
  return new Promise((resolve, reject) => {
    const { frameId, frameExtension } = taskInfo;

    let filePromise = null;

    if (fileCache.has(frameId)) {
      filePromise = fileCache.get(frameId);
    } else {
      const download = ReaderFactory.downloadFrame(
        apiClient,
        `image${frameExtension}`,
        `/frames/${frameId}/download`,
      );
      filePromise = download.promise;
      fileCache.set(frameId, filePromise);
      pendingFrameDownloads.add(download);
      filePromise.then(() => {
        pendingFrameDownloads.delete(download);
      }).catch(() => {
        pendingFrameDownloads.delete(download);
      });
    }

    filePromise
      .then((file) => {
        resolve(getData(frameId, file, webWorker));
      })
      .catch((err) => {
        console.log('poolFunction: fileP error of some kind');
        console.log(err);
        reject(err);
      });
  });
}

function progressHandler(completed, total) {
  const percentComplete = completed / total;
  store.commit.setScanCachedPercentage(percentComplete);
}

function startReaderWorkerPool() {
  const taskArgsArray = readDataQueue.map((taskInfo) => [taskInfo]);
  readDataQueue = [];

  const { runId, promise } = store.state.workerPool.runTasks(
    taskArgsArray,
    progressHandler,
  );
  taskRunId = runId;

  promise
    .then(() => {
      taskRunId = -1;
    })
    .catch((err) => {
      console.error(err);
    })
    .finally(() => {
      store.state.workerPool.terminateWorkers();
    });
}

// cache frames associated with scans of current experiment
function checkLoadExperiment(oldValue, newValue) {
  if (
    !newValue
    || newValue === oldValue
    || (newValue && oldValue && newValue.folderId === oldValue.folderId)
  ) {
    return;
  }

  if (oldValue) {
    const oldExperimentScans = store.state.experimentScans[oldValue.id];
    oldExperimentScans.forEach((scanId) => {
      const scanFrames = store.state.scanFrames[scanId];
      scanFrames.forEach((frameId) => {
        fileCache.delete(frameId);
        frameCache.delete(frameId);
      });
    });
  }

  readDataQueue = [];
  const newExperimentScans = store.state.experimentScans[newValue.id];
  newExperimentScans.forEach((scanId) => {
    const scanFrames = store.state.scanFrames[scanId].map(
      (frameId) => store.state.frames[frameId],
    );
    scanFrames.forEach((frame) => {
      readDataQueue.push({
        // TODO don't hardcode projectId
        projectId: 1,
        experimentId: newValue.id,
        scanId,
        frameId: frame.id,
        frameExtension: frame.extension,
      });
    });
  });
  startReaderWorkerPool();
}

// get next frame (across experiments and scans)
function getNextFrame(experiments, i, j) {
  const experiment = experiments[i];
  const { scans } = experiment;

  if (j === scans.length - 1) {
    // last scan, go to next experiment
    if (i === experiments.length - 1) {
      // last experiment, nowhere to go
      return null;
    }
    // get first scan in next experiment
    const nextExperiment = experiments[i + 1];
    const nextScan = nextExperiment.scans[0];
    return nextScan.frames[0];
  }
  // get next scan in current experiment
  const nextScan = scans[j + 1];
  return nextScan.frames[0];
}

function expandScanRange(frameId, dataRange) {
  if (frameId in store.state.frames) {
    const scanId = store.state.frames[frameId].scan;
    const scan = store.state.scans[scanId];
    if (scan && dataRange[0] < scan.cumulativeRange[0]) {
      [scan.cumulativeRange[0]] = dataRange;
    }
    if (scan && dataRange[1] > scan.cumulativeRange[1]) {
      [, scan.cumulativeRange[1]] = dataRange;
    }
  }
}

const initState = {
  MIQAConfig: {},
  me: null,
  allUsers: [],
  reviewMode: false,
  currentProject: null as Project | null,
  currentTaskOverview: null as ProjectTaskOverview | null,
  currentProjectPermissions: {},
  projects: [] as Project[],
  allScans: {},
  experimentIds: [],
  experiments: {},
  experimentScans: {},
  scans: {},
  scanFrames: {},
  frames: {},
  proxyManager: null,
  vtkViews: [],
  currentFrameId: null,
  loadingFrame: false,
  errorLoadingFrame: false,
  loadingExperiment: false,
  currentScreenshot: null,
  screenshots: [],
  scanCachedPercentage: 0,
  showCrosshairs: true,
  sliceLocation: {},
  iIndexSlice: 0,
  jIndexSlice: 0,
  kIndexSlice: 0,
};

const {
  store,
  rootActionContext,
  moduleActionContext,
  rootGetterContext,
  moduleGetterContext,
} = createDirectStore({
  state: {
    ...initState,
    workerPool: new WorkerPool(poolSize, poolFunction),
    actionTimer: null,
    actionTimeout: false,
  },
  getters: {
    wholeState(state) {
      return state;
    },
    currentViewData(state) {
      const currentFrame = state.currentFrameId ? state.frames[state.currentFrameId] : null;
      const scan = state.scans[currentFrame.scan];
      if (!scan) {
        const nextFrame = Object.entries(state.frames).map(
          ([, frameInfo]) => frameInfo,
        ).filter(
          (frameInfo: Frame) => frameInfo.scan === Object.keys(state.scans)[0],
        )[0][0];
        // Scan removed from list by review mode, return sparse object
        // and let the component navigate away
        // since navigation should not happen in the store
        return {
          downTo: nextFrame,
        };
      }
      const experiment = currentFrame.experiment
        ? state.experiments[currentFrame.experiment] : null;
      const project = state.projects.filter((x) => x.id === experiment.project)[0];
      const experimentScansList = state.experimentScans[experiment.id];
      const scanFramesList = state.scanFrames[scan.id];
      let upTo = currentFrame.firstFrameInPreviousScan;
      let downTo = currentFrame.firstFrameInNextScan;
      if (upTo && !Object.keys(state.scans).includes(state.frames[upTo].scan)) {
        upTo = null;
      }
      if (downTo && !Object.keys(state.scans).includes(state.frames[downTo].scan)) {
        downTo = null;
      }
      return {
        projectId: project.id,
        projectName: project.name,
        experimentId: experiment.id,
        experimentName: experiment.name,
        experimentNote: experiment.note,
        lockOwner: experiment.lock_owner || experiment.lockOwner,
        scanId: scan.id,
        scanName: scan.name,
        scanDecisions: scan.decisions,
        scanPositionString: `(${experimentScansList.indexOf(scan.id) + 1}/${experimentScansList.length})`,
        framePositionString: `(${scanFramesList.indexOf(currentFrame.id) + 1}/${scanFramesList.length})`,
        backTo: currentFrame.previousFrame,
        forwardTo: currentFrame.nextFrame,
        upTo,
        downTo,
        currentAutoEvaluation: currentFrame.frame_evaluation,
        autoWindow: experiment.autoWindow,
        autoLevel: experiment.autoLevel,
      };
    },
    currentFrame(state) {
      const { frames, currentFrameId } = state;
      return currentFrameId ? frames[currentFrameId] : null;
    },
    previousFrame(state, getters) {
      return getters.currentFrame
        ? getters.currentFrame.previousFrame
        : null;
    },
    nextFrame(state, getters) {
      return getters.currentFrame ? getters.currentFrame.nextFrame : null;
    },
    currentScan(state, getters) {
      if (getters.currentFrame) {
        const curScanId = getters.currentFrame.scan;
        return state.scans[curScanId];
      }
      return null;
    },
    currentExperiment(state, getters) {
      if (getters.currentScan) {
        const curExperimentId = getters.currentScan.experiment;
        return state.experiments[curExperimentId];
      }
      return null;
    },
    myCurrentProjectRoles(state) {
      const projectPerms = Object.entries(state.currentProjectPermissions)
        .filter((entry: [string, Array<User>]): Boolean => entry[1].map(
          (user) => user.username,
        ).includes(state.me.username))
        .map((entry) => entry[0]);
      if (state.me.is_superuser) {
        projectPerms.push('superuser');
      }
      return projectPerms;
    },
    isGlobal(state) {
      return state.currentProject?.id === 'global';
    },
  },
  mutations: {
    reset(state) {
      Object.assign(state, { ...state, ...initState });
    },
    setMIQAConfig(state, configuration) {
      state.MIQAConfig = configuration;
    },
    setMe(state, me) {
      state.me = me;
    },
    setAllUsers(state, allUsers) {
      state.allUsers = allUsers;
    },
    resetProject(state) {
      state.experimentIds = [];
      state.experiments = {};
      state.experimentScans = {};
      state.scans = {};
      state.scanFrames = {};
      state.frames = {};
    },
    setCurrentFrameId(state, frameId) {
      state.currentFrameId = frameId;
    },
    setFrame(state, { frameId, frame }) {
      // Replace with a new object to trigger a Vuex update
      state.frames = { ...state.frames };
      state.frames[frameId] = frame;
    },
    setScan(state, { scanId, scan }) {
      // Replace with a new object to trigger a Vuex update
      state.scans = { ...state.scans };
      state.scans[scanId] = scan;
      state.allScans = Object.assign(state.allScans, state.scans);
    },
    setCurrentProject(state, project: Project | null) {
      state.currentProject = project;
      if (project) {
        state.currentProjectPermissions = project.settings.permissions;
      }
    },
    setTaskOverview(state, taskOverview: ProjectTaskOverview) {
      state.currentTaskOverview = taskOverview;
    },
    setProjects(state, projects: Project[]) {
      state.projects = projects;
    },
    addScanDecision(state, { currentScan, newDecision }) {
      state.scans[currentScan].decisions.push(newDecision);
    },
    setCurrentScreenshot(state, screenshot) {
      state.currentScreenshot = screenshot;
    },
    addScreenshot(state, screenshot) {
      state.screenshots.push(screenshot);
    },
    removeScreenshot(state, screenshot) {
      state.screenshots.splice(state.screenshots.indexOf(screenshot), 1);
    },
    setActionTimeout(state, value) {
      state.actionTimeout = value;
    },
    setLoadingFrame(state, value) {
      state.loadingFrame = value;
    },
    setErrorLoadingFrame(state, value) {
      state.errorLoadingFrame = value;
    },
    addScanFrames(state, { sid, id }) {
      state.scanFrames[sid].push(id);
    },
    addExperimentScans(state, { eid, sid }) {
      state.scanFrames[sid] = [];
      state.experimentScans[eid].push(sid);
    },
    addExperiment(state, { id, value }) {
      state.experimentScans[id] = [];
      state.experimentIds.push(id);
      state.experiments[id] = value;
    },
    updateExperiment(state, experiment) {
      // Necessary for reactivity
      state.experiments = { ...state.experiments };
      state.experiments[experiment.id] = experiment;
    },
    setExperimentAutoWindow(state, { experimentId, autoWindow }) {
      state.experiments[experimentId].autoWindow = autoWindow;
    },
    setExperimentAutoLevel(state, { experimentId, autoLevel }) {
      state.experiments[experimentId].autoLevel = autoLevel;
    },
    setScanCachedPercentage(state, percentComplete) {
      state.scanCachedPercentage = percentComplete;
    },
    startLoadingExperiment(state) {
      state.loadingExperiment = true;
    },
    stopLoadingExperiment(state) {
      state.loadingExperiment = false;
    },
    setSliceLocation(state, ijkLocation) {
      if (!Object.keys(ijkLocation).some((value) => value === undefined)) {
        state.sliceLocation = ijkLocation;
      }
    },
    setCurrentVtkIndexSlices(state, { indexAxis, value }) {
      state[`${indexAxis}IndexSlice`] = value;
    },
    setShowCrosshairs(state, show) {
      state.showCrosshairs = show;
    },
    switchReviewMode(state, mode) {
      state.reviewMode = mode || false;
      if (mode) {
        const myRole = state.currentTaskOverview.my_project_role;
        let scanStateForMyReview: string = null;
        if (myRole === 'tier_2_reviewer') {
          [, scanStateForMyReview] = Object.keys(ScanState);
        } else if (myRole === 'tier_1_reviewer') {
          [scanStateForMyReview] = Object.keys(ScanState);
        }
        const scanIdsForMyReview = Object.entries(state.currentTaskOverview.scan_states).filter(
          ([, scanState]) => scanStateForMyReview.replace(/_/g, ' ') === scanState,
        ).map(
          ([scanId]) => scanId,
        );
        state.scans = Object.fromEntries(
          Object.entries(state.allScans).filter(
            ([scanId]) => scanIdsForMyReview.includes(scanId),
          ),
        );
      } else {
        state.scans = state.allScans;
      }
    },
  },
  actions: {
    reset({ state, commit }) {
      if (taskRunId >= 0) {
        state.workerPool.cancel(taskRunId);
        taskRunId = -1;
      }
      commit('reset');
      fileCache.clear();
      frameCache.clear();
    },
    async loadConfiguration({ commit }) {
      const configuration = await djangoRest.MIQAConfig();
      commit('setMIQAConfig', configuration);
    },
    async loadMe({ commit }) {
      const me = await djangoRest.me();
      commit('setMe', me);
    },
    async loadAllUsers({ commit }) {
      const allUsers = await djangoRest.allUsers();
      commit('setAllUsers', allUsers.results);
    },
    async logout({ dispatch }) {
      dispatch('reset');
      await djangoRest.logout();
    },
    async loadGlobal({ commit }) {
      const globalSettings = await djangoRest.globalSettings();
      const pseudoProject = {
        id: 'global',
        name: null,
        experiments: null,
        settings: {
          importPath: globalSettings.import_path,
          exportPath: globalSettings.export_path,
          permissions: null,
        },
        status: null,
      };
      commit('setCurrentProject', pseudoProject);
    },
    async loadProjects({ commit }) {
      const projects = await djangoRest.projects();
      commit('setProjects', projects);
    },
    async loadProject({ commit }, project: Project) {
      commit('resetProject');

      // Build navigation links throughout the frame to improve performance.
      let firstInPrev = null;

      // Refresh the project from the API
      project = await djangoRest.project(project.id);
      commit('setCurrentProject', project);

      // place data in state
      const { experiments } = project;

      for (let i = 0; i < experiments.length; i += 1) {
        const experiment = experiments[i];
        // set experimentScans[experiment.id] before registering the experiment.id
        // so ExperimentsView doesn't update prematurely
        commit('addExperiment', {
          id: experiment.id,
          value: {
            id: experiment.id,
            name: experiment.name,
            note: experiment.note,
            project: experiment.project,
            index: i,
            lockOwner: experiment.lock_owner,
          },
        });

        // TODO these requests *can* be run in parallel, or collapsed into one XHR
        // eslint-disable-next-line no-await-in-loop
        const { scans } = experiment;
        for (let j = 0; j < scans.length; j += 1) {
          const scan = scans[j];
          commit('addExperimentScans', { eid: experiment.id, sid: scan.id });

          // TODO these requests *can* be run in parallel, or collapsed into one XHR
          // eslint-disable-next-line no-await-in-loop
          const { frames } = scan;

          commit('setScan', {
            scanId: scan.id,
            scan: {
              id: scan.id,
              name: scan.name,
              experiment: experiment.id,
              cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
              numFrames: frames.length,
              // The experiment.scans.note serialization does not contain note metadata.
              // Just set notes to [] and let reloadScan set the complete values later.
              notes: [],
              decisions: scan.decisions,
            },
          });

          const nextScan = getNextFrame(experiments, i, j);

          for (let k = 0; k < frames.length; k += 1) {
            const frame = frames[k];
            commit('addScanFrames', { sid: scan.id, id: frame.id });
            commit('setFrame', {
              frameId: frame.id,
              frame: {
                ...frame,
                scan: scan.id,
                experiment: experiment.id,
                index: k,
                previousFrame: k > 0 ? frames[k - 1].id : null,
                nextFrame: k < frames.length - 1 ? frames[k + 1].id : null,
                firstFrameInPreviousScan: firstInPrev,
                firstFrameInNextScan: nextScan ? nextScan.id : null,
              },
            });
          }

          if (frames.length > 0) {
            firstInPrev = frames[0].id;
          } else {
            console.error(
              `${experiment.name}/${scan.name} has no frames`,
            );
          }
        }
      }
      // get the task overview for this project
      const taskOverview = await djangoRest.projectTaskOverview(project.id);
      commit('setTaskOverview', taskOverview);
    },
    async reloadScan({ commit, getters }) {
      const { currentFrame } = getters;
      // No need to reload if the frame doesn't exist or doesn't exist on the server
      if (!currentFrame || currentFrame.local) {
        return;
      }
      const scanId = currentFrame.scan;
      if (!scanId) {
        return;
      }
      const scan = await djangoRest.scan(scanId);
      const frames = await djangoRest.frames(scanId);
      commit('setScan', {
        scanId: scan.id,
        scan: {
          id: scan.id,
          name: scan.name,
          experiment: scan.experiment,
          cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
          numFrames: frames.length,
          notes: scan.notes,
          decisions: scan.decisions,
        },
      });
    },
    async getFrame({ state, dispatch }, { frameId, projectId }) {
      if (!frameId) {
        return undefined;
      }
      if (!state.frames[frameId]) {
        await dispatch('loadProjects');
        const targetProject = state.projects.filter((proj) => proj.id === projectId)[0];
        await dispatch('loadProject', targetProject);
      }
      return state.frames[frameId];
    },
    async setCurrentFrame({ commit, dispatch }, frameId) {
      commit('setCurrentFrameId', frameId);
      if (frameId) {
        dispatch('reloadScan');
      }
    },
    async swapToFrame({
      state, dispatch, getters, commit,
    }, { frame, onDownloadProgress = null }) {
      if (!frame) {
        throw new Error("frame id doesn't exist");
      }
      if (getters.currentFrame === frame) {
        return;
      }
      commit('setLoadingFrame', true);
      commit('setErrorLoadingFrame', false);
      const oldScan = getters.currentScan;
      const newScan = state.scans[frame.scan];
      const oldExperiment = getters.currentExperiment
        ? getters.currentExperiment
        : null;
      const newExperimentId = state.scans[frame.scan].experiment;
      const newExperiment = state.experiments[newExperimentId];

      // Check if we should cancel the currently loading experiment
      if (
        newExperiment
        && oldExperiment
        && newExperiment.id !== oldExperiment.id
        && taskRunId >= 0
      ) {
        state.workerPool.cancel(taskRunId);
        pendingFrameDownloads.forEach(({ abortController }) => {
          abortController.abort();
        });
        pendingFrameDownloads.clear();
        taskRunId = -1;
      }

      let newProxyManager = false;
      if (oldScan !== newScan && state.proxyManager) {
        // If we don't "shrinkProxyManager()" and reinitialize it between
        // scans, then we can end up with no frame
        // slices displayed, even though we have the data and attempted
        // to render it.  This may be due to frame extents changing between
        // scans, which is not the case from one timestep of a single scan
        // to tne next.
        shrinkProxyManager(state.proxyManager);
        newProxyManager = true;
      }

      if (!state.proxyManager || newProxyManager) {
        state.proxyManager = vtkProxyManager.newInstance({
          proxyConfiguration: proxy,
        });
        state.vtkViews = [];
      }

      let sourceProxy = state.proxyManager.getActiveSource();
      let needPrep = false;
      if (!sourceProxy) {
        sourceProxy = state.proxyManager.createProxy(
          'Sources',
          'TrivialProducer',
        );
        needPrep = true;
      }

      // This try catch and within logic are mainly for handling data doesn't exist issue
      try {
        let frameData = null;
        if (frameCache.has(frame.id)) {
          frameData = frameCache.get(frame.id).frameData;
        } else {
          const result = await loadFileAndGetData(
            frame.id, frame.extension, { onDownloadProgress },
          );
          frameData = result.frameData;
        }
        sourceProxy.setInputData(frameData);
        if (needPrep || !state.proxyManager.getViews().length) {
          prepareProxyManager(state.proxyManager);
          state.vtkViews = state.proxyManager.getViews();
          // initializing the screenshot view resets the render settings, so do it now instead of
          // when a screenshot is taken
          prepareScreenshotViews(state.proxyManager);
        }
        if (!state.vtkViews.length) {
          state.vtkViews = state.proxyManager.getViews();
        }
      } catch (err) {
        console.log('Caught exception loading next frame');
        console.log(err);
        state.vtkViews = [];
        commit('setErrorLoadingFrame', true);
      } finally {
        dispatch('setCurrentFrame', frame.id);
        commit('setLoadingFrame', false);
      }

      // If necessary, queue loading scans of new experiment
      checkLoadExperiment(oldExperiment, newExperiment);
    },
    async setLock({ commit }, { experimentId, lock }) {
      if (lock) {
        commit(
          'updateExperiment',
          await djangoRest.lockExperiment(experimentId),
        );
      } else {
        commit(
          'updateExperiment',
          await djangoRest.unlockExperiment(experimentId),
        );
      }
    },
    startActionTimer({ state, commit }) {
      state.actionTimer = setTimeout(() => {
        commit('setActionTimeout', true);
      }, actiontime);
    },
    resetActionTimer({ state, dispatch }) {
      clearTimeout(state.actionTimer);
      dispatch('startActionTimer');
    },
  },
});

// Export the direct-store instead of the classic Vuex store.
export default store;

// The following exports will be used to enable types in the
// implementation of actions and getters.
export {
  rootActionContext,
  moduleActionContext,
  rootGetterContext,
  moduleGetterContext,
};

export type AppStore = typeof store;
