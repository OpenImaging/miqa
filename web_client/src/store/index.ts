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
  Project, ProjectTaskOverview, User, ProjectSettings, Scan,
} from '@/types';
import axios from 'axios';
import ReaderFactory from '../utils/ReaderFactory';

import { proxy } from '../vtk';
import { getView } from '../vtk/viewManager';
import { ijkMapping } from '../vtk/constants';

const { convertItkToVtkImage } = ITKHelper;

Vue.use(Vuex);

const fileCache = new Map();
const frameCache = new Map();
let readDataQueue = [];
const pendingFrameDownloads = new Set<any>();
const poolSize = Math.floor(navigator.hardwareConcurrency / 2) || 2;
let taskRunId = -1;
let savedWorker = null;

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
            reject(error);
          });
      };

      io.readAsArrayBuffer(file);
    }
  });
}

function loadFile(frame, { onDownloadProgress = null } = {}) {
  if (fileCache.has(frame.id)) {
    return { frameId: frame.id, fileP: fileCache.get(frame.id) };
  }
  let client = apiClient;
  let downloadURL = `/frames/${frame.id}/download`;
  if (frame.download_url) {
    client = axios.create();
    downloadURL = frame.download_url;
  }
  const { promise } = ReaderFactory.downloadFrame(
    client,
    `image${frame.extension}`,
    downloadURL,
    { onDownloadProgress },
  );
  fileCache.set(frame.id, promise);
  return { frameId: frame.id, fileP: promise };
}

function loadFileAndGetData(frame, { onDownloadProgress = null } = {}) {
  const loadResult = loadFile(frame, { onDownloadProgress });
  return loadResult.fileP.then((file) => getData(frame.id, file, savedWorker)
    .then(({ webWorker, frameData }) => {
      savedWorker = webWorker;
      return Promise.resolve({ frameData });
    })
    .catch(() => {
      const msg = 'loadFileAndGetData caught error getting data';
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
    const { frame } = taskInfo;

    let filePromise = null;

    if (fileCache.has(frame.id)) {
      filePromise = fileCache.get(frame.id);
    } else {
      let client = apiClient;
      let downloadURL = `/frames/${frame.id}/download`;
      if (frame.download_url) {
        client = axios.create();
        downloadURL = frame.download_url;
      }
      const download = ReaderFactory.downloadFrame(
        client,
        `image${frame.extension}`,
        downloadURL,
      );
      filePromise = download.promise;
      fileCache.set(frame.id, filePromise);
      pendingFrameDownloads.add(download);
      filePromise.then(() => {
        pendingFrameDownloads.delete(download);
      }).catch(() => {
        pendingFrameDownloads.delete(download);
      });
    }

    filePromise
      .then((file) => {
        resolve(getData(frame.id, file, webWorker));
      })
      .catch((err) => {
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
  ) {
    return;
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
        frame,
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
  globalSettings: undefined as ProjectSettings,
  currentProject: undefined as Project | null,
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
  storeCrosshairs: true,
  sliceLocation: {},
  iIndexSlice: 0,
  jIndexSlice: 0,
  kIndexSlice: 0,
  currentWindowWidth: 256,
  currentWindowLevel: 150,
  windowLocked: {
    lock: false,
    duration: undefined,
    target: undefined,
    associatedImage: undefined,
  },
  renderOrientation: 'LPS',
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
    lastApiRequestTime: Date.now(),
  },
  getters: {
    wholeState(state) {
      return state;
    },
    currentViewData(state) {
      const currentFrame = state.currentFrameId ? state.frames[state.currentFrameId] : null;
      const scan = state.scans[currentFrame.scan];
      if (!scan) {
        // scan was removed from list by review mode; do nothing
        return {};
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
        scanSession: scan.sessionID,
        scanSubject: scan.subjectID,
        scanLink: scan.link,
        scanDecisions: scan.decisions,
        scanPositionString: `(${experimentScansList.indexOf(scan.id) + 1}/${experimentScansList.length})`,
        framePositionString: `(${scanFramesList.indexOf(currentFrame.id) + 1}/${scanFramesList.length})`,
        backTo: currentFrame.previousFrame,
        forwardTo: currentFrame.nextFrame,
        upTo,
        downTo,
        currentFrame,
        currentAutoEvaluation: currentFrame.frame_evaluation,
      };
    },
    currentFrame(state) {
      return state.currentFrameId ? state.frames[state.currentFrameId] : null;
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
      return state.currentProject === null;
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
    setRenderOrientation(state, anatomy) {
      state.renderOrientation = anatomy;
    },
    setCurrentProject(state, project: Project | null) {
      state.currentProject = project;
      if (project) {
        state.renderOrientation = project.settings.anatomy_orientation;
        state.currentProjectPermissions = project.settings.permissions;
      }
    },
    setGlobalSettings(state, settings) {
      state.globalSettings = settings;
    },
    setTaskOverview(state, taskOverview: ProjectTaskOverview) {
      if (!taskOverview) return;
      if (taskOverview.scan_states) {
        state.projects.find(
          (project) => project.id === taskOverview.project_id,
        ).status = {
          total_scans: taskOverview.total_scans,
          total_complete: Object.values(taskOverview.scan_states).filter(
            (scanState) => scanState === 'complete',
          ).length,
        };
      }
      if (state.currentProject && taskOverview.project_id === state.currentProject.id) {
        state.currentTaskOverview = taskOverview;
        Object.values(store.state.allScans).forEach((scan: Scan) => {
          if (taskOverview.scan_states[scan.id] && taskOverview.scan_states[scan.id] !== 'unreviewed') {
            store.dispatch.reloadScan(scan.id);
          }
        });
      }
    },
    setProjects(state, projects: Project[]) {
      state.projects = projects;
    },
    addScanDecision(state, { currentScan, newDecision }) {
      state.scans[currentScan].decisions.push(newDecision);
    },
    setFrameEvaluation(state, evaluation) {
      const currentFrame = state.currentFrameId ? state.frames[state.currentFrameId] : null;
      if (currentFrame) {
        currentFrame.frame_evaluation = evaluation;
      }
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
    updateLastApiRequestTime(state) {
      state.lastApiRequestTime = Date.now();
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
    setWindowLocked(state, lockState) {
      state.windowLocked = lockState;
    },
    setScanCachedPercentage(state, percentComplete) {
      state.scanCachedPercentage = percentComplete;
    },
    setSliceLocation(state, ijkLocation) {
      if (!Object.keys(ijkLocation).some((value) => value === undefined)) {
        state.vtkViews.forEach(
          (view) => {
            state.proxyManager.getRepresentation(null, view).setSlice(
              ijkLocation[ijkMapping[view.getName()]],
            );
          },
        );
      }
    },
    setCurrentVtkIndexSlices(state, { indexAxis, value }) {
      state[`${indexAxis}IndexSlice`] = value;
      state.sliceLocation = undefined;
    },
    setCurrentWindowWidth(state, value) {
      state.currentWindowWidth = value;
    },
    setCurrentWindowLevel(state, value) {
      state.currentWindowLevel = value;
    },
    setShowCrosshairs(state, show) {
      state.showCrosshairs = show;
    },
    setStoreCrosshairs(state, value) {
      state.storeCrosshairs = value;
    },
    switchReviewMode(state, mode) {
      state.reviewMode = mode || false;
      if (mode) {
        const myRole = state.currentTaskOverview.my_project_role;
        state.scans = Object.fromEntries(
          Object.entries(state.allScans).filter(
            ([scanId]) => {
              const scanState = state.currentTaskOverview.scan_states[scanId];
              switch (scanState) {
                case 'unreviewed':
                  return true;
                case 'complete':
                  return false;
                default:
                  return myRole === 'tier_2_reviewer';
              }
            },
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
    async loadGlobal({ commit }) {
      const globalSettings = await djangoRest.globalSettings();
      commit('setCurrentProject', null);
      commit('setGlobalSettings', {
        import_path: globalSettings.import_path,
        export_path: globalSettings.export_path,
      });
      commit('setTaskOverview', {});
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
              decisions: scan.decisions,
              sessionID: scan.session_id,
              subjectID: scan.subject_id,
              link: scan.scan_link,
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
    async reloadScan({ commit, getters }, scanId) {
      const { currentFrame } = getters;
      scanId = scanId || currentFrame.scan;
      if (!scanId) return;
      const scan = await djangoRest.scan(scanId);
      commit('setScan', {
        scanId: scan.id,
        scan: {
          id: scan.id,
          name: scan.name,
          experiment: scan.experiment,
          cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
          notes: scan.notes,
          decisions: scan.decisions,
          sessionID: scan.session_id,
          subjectID: scan.subject_id,
          link: scan.scan_link,
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
    async setCurrentFrame({ commit }, frameId) {
      commit('setCurrentFrameId', frameId);
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
            frame, { onDownloadProgress },
          );
          frameData = result.frameData;
        }
        sourceProxy.setInputData(frameData);
        if (needPrep || !state.proxyManager.getViews().length) {
          prepareProxyManager(state.proxyManager);
          state.vtkViews = state.proxyManager.getViews();
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

      // check for window lock expiry
      if (state.windowLocked.lock) {
        const { currentViewData } = getters;
        const unlock = () => {
          commit('setWindowLocked', {
            lock: false,
            duration: undefined,
            target: undefined,
            associatedImage: undefined,
          });
        };
        switch (state.windowLocked.duration) {
          case 'scan':
            if (currentViewData.scanId !== state.windowLocked.target) unlock();
            break;
          case 'experiment':
            if (currentViewData.experimentId !== state.windowLocked.target) unlock();
            break;
          case 'project':
            if (currentViewData.projectId !== state.windowLocked.target) unlock();
            break;
          default:
            break;
        }
      }
    },
    async setLock({ commit }, { experimentId, lock, force }) {
      if (lock) {
        commit(
          'updateExperiment',
          await djangoRest.lockExperiment(experimentId, force),
        );
      } else {
        commit(
          'updateExperiment',
          await djangoRest.unlockExperiment(experimentId),
        );
      }
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
