/* eslint-disable no-use-before-define */
import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import vtkProxyManager from 'vtk.js/Sources/Proxy/Core/ProxyManager';
import macro from 'vtk.js/Sources/macros';
import { InterpolationType } from 'vtk.js/Sources/Rendering/Core/ImageProperty/Constants';

import '../utils/registerReaders';

import readImageArrayBuffer from 'itk/readImageArrayBuffer';
import WorkerPool from 'itk/WorkerPool';
import ITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper';
import axios from 'axios';
import djangoRest, { apiClient } from '@/django';
import {
  MIQAStore, Project, ProjectTaskOverview, ProjectSettings, Scan, User,
} from '@/types';
import ReaderFactory from '../utils/ReaderFactory';

import { proxy } from '../vtk';
import { getView } from '../vtk/viewManager';
import { ijkMapping } from '../vtk/constants';

import {
  RESET_STATE, SET_MIQA_CONFIG, SET_ME, SET_SNACKBAR,
  SET_ALL_USERS, RESET_PROJECT_STATE, SET_CURRENT_FRAME_ID,
  SET_FRAME, SET_SCAN, SET_RENDER_ORIENTATION, SET_CURRENT_PROJECT, SET_GLOBAL_SETTINGS,
  SET_TASK_OVERVIEW, SET_PROJECTS, ADD_SCAN_DECISION, SET_FRAME_EVALUATION, SET_CURRENT_SCREENSHOT,
  ADD_SCREENSHOT, REMOVE_SCREENSHOT, UPDATE_LAST_API_REQUEST_TIME, SET_LOADING_FRAME,
  SET_ERROR_LOADING_FRAME, ADD_SCAN_FRAMES, ADD_EXPERIMENT_SCANS, ADD_EXPERIMENT,
  UPDATE_EXPERIMENT, SET_WINDOW_LOCKED, SET_SCAN_CACHED_PERCENTAGE, SET_SLICE_LOCATION,
  SET_CURRENT_VTK_INDEX_SLICES, SET_SHOW_CROSSHAIRS, SET_STORE_CROSSHAIRS, SET_REVIEW_MODE,
} from './mutation-types';

const { convertItkToVtkImage } = ITKHelper;

Vue.use(Vuex);

// Cache of downloaded files
const fileCache = new Map();
// Cache of individual frames within a single scan
const frameCache = new Map();
// Queue of frames to be downloaded
let readDataQueue = [];
// List of frames that have been successfully added to readDataQueue
const loadedData = [];
// Frames that need to be downloaded
const pendingFrameDownloads = new Set();
// Maximum number of workers in WorkerPool
const poolSize = Math.floor(navigator.hardwareConcurrency / 2) || 2;
// Defines the task currently running
let taskRunId = -1;
// Reuse workers for performance
let savedWorker = null;

/** Delete existing VTK.js proxyManager views */
function shrinkProxyManager(proxyManager: vtkProxyManager) {
  proxyManager.getViews().forEach((view) => {
    view.setContainer(null);
    proxyManager.deleteProxy(view);
  });
}

/** Renders each view. Also disables Axes visibility and sets InterpolationType to nearest */
function prepareProxyManager(proxyManager: vtkProxyManager) {
  if (!proxyManager.getViews().length) {
    ['View2D_Z:z', 'View2D_X:x', 'View2D_Y:y'].forEach((type) => {
      const view = getView(proxyManager, type);
      view.setOrientationAxesVisibility(false);
      view.getRepresentations().forEach((representation) => {
        representation.setInterpolationType(InterpolationType.NEAREST);
        representation.onModified(macro.debounce(() => {
          if (view.getRepresentations()) {
            view.render(true);
          }
        }, 0));
        // debounce timer doesn't need a wait time because
        // the many onModified changes that it needs to collapse to a single rerender
        // all happen simultaneously when the input data is changed.
      });
    });
  }
}

/** Array name is file name minus last extension, e.g. image.nii.gz => image.nii */
function getArrayNameFromFilename(filename) {
  const idx = filename.lastIndexOf('.');
  const name = idx > -1 ? filename.substring(0, idx) : filename;
  return `Scalars ${name}`;
}

function getImageData(frameId: string, file, webWorker = null) {
  return new Promise((resolve, reject) => {
    // 1. Check cache for copy of image
    if (frameCache.has(frameId)) {
      // 2a. Load image from cache
      resolve({ frameData: frameCache.get(frameId), webWorker });
    } else {
      // 2b. Download image
      const fileName = file.name;
      const io = new FileReader();

      // 4. Wait until the file has been loaded
      io.onload = function onLoad() {
        // 5. Read image using ITK
        readImageArrayBuffer(webWorker, io.result, fileName)
          // 6. Convert image from ITK to VTK
          .then(({ webWorker, image }) => { // eslint-disable-line no-shadow
            const frameData = convertItkToVtkImage(image, {
              scalarArrayName: getArrayNameFromFilename(fileName),
            });
            // 7. Get metadata about image
            const dataRange = frameData
              .getPointData() // From the image file
              .getArray(0) // Values in the file
              .getRange(); // Range of values in the file, e.g. [0, 3819]
            frameCache.set(frameId, { frameData });
            // eslint-disable-next-line no-use-before-define
            expandScanRange(frameId, dataRange); // Example dataRange: [0, 3819]
            resolve({ frameData, webWorker });
          })
          .catch((error) => {
            reject(error);
          });
      };

      // 3. Load image file
      io.readAsArrayBuffer(file);
    }
  });
}

/** Load file, from cache if possible. */
function loadFile(frame, { onDownloadProgress = null } = {}) {
  if (fileCache.has(frame.id)) {
    return { frameId: frame.id, cachedFile: fileCache.get(frame.id) };
  }

  // Otherwise download the frame
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
  return { frameId: frame.id, cachedFile: promise };
}

/** Gets the data from the selected image file using a webWorker. */
async function loadFileAndGetData(frame, { onDownloadProgress = null } = {}) {
  const loadResult = loadFile(frame, { onDownloadProgress });
  // Once the file has been cached and is available, call getImageData
  return loadResult.cachedFile
    .then((file) => getImageData(frame.id, file, savedWorker))
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
    });
}

/**
 * Use a worker to download image files. Only used by WorkerPool
 * taskInfo  Object  Contains experimentId, scanId, and a frame object
 */
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
        resolve(getImageData(frame.id, file, webWorker));
      })
      .catch((err) => {
        reject(err);
      });
  });
}

/** Calculates the percent downloaded of currently loading frames */
function progressHandler(completed, total) {
  const percentComplete = completed / total;
  store.commit('SET_SCAN_CACHED_PERCENTAGE', percentComplete);
}

/** Creates array of tasks to run then runs tasks in parallel. */
function startReaderWorkerPool() {
  // Get the current array of tasks in readDataQueue
  const taskArgsArray = readDataQueue.map((taskInfo) => [taskInfo]);
  readDataQueue = [];

  const { runId, promise } = store.state.workerPool.runTasks(
    taskArgsArray,
    progressHandler,
  );
  taskRunId = runId; // The number of tasks still running

  promise
    .then(() => {
      taskRunId = -1; // Indicates no tasks are running
    })
    .catch((err) => {
      console.error(err);
    })
    .finally(() => {
      store.state.workerPool.terminateWorkers();
    });
}

/** Queues scan for download, will load all frames for a target
 * scan if the scan has not already been loaded. */
function queueLoadScan(scan, loadNext = 0) {
  // load all frames in target scan
  if (!loadedData.includes(scan.id)) {
    // For each scan in scanFrames
    store.state.scanFrames[scan.id].forEach(
      (frameId) => {
        // Add to readDataQueue a request to get the frames associated with that scan
        readDataQueue.push({
          experimentId: scan.experiment,
          scanId: scan.id,
          frame: store.state.frames[frameId],
        });
      },
    );
    loadedData.push(scan.id);
  }

  if (loadNext > 0) {
    // Get the other scans in the experiment.
    const scansInSameExperiment = store.state.experimentScans[scan.experiment];
    let nextScan;
    if (scan.id === scansInSameExperiment[scansInSameExperiment.length - 1]) {
      // load first scan in next experiment
      const experimentIds = Object.keys(store.state.experimentScans);
      const nextExperimentId = experimentIds[experimentIds.indexOf(scan.experiment) + 1];
      const nextExperimentScans = store.state.experimentScans[nextExperimentId];
      if (nextExperimentScans && nextExperimentScans.length > 0) {
        nextScan = store.state.scans[
          nextExperimentScans[0]
        ];
      }
    } else {
      let newIndex = scansInSameExperiment.indexOf(scan.id) + 1;
      while (
        (!nextScan || !includeScan(nextScan.id))
         && newIndex < scansInSameExperiment.length
         && newIndex > 0
      ) {
        // load next scan in same experiment
        nextScan = store.state.scans[scansInSameExperiment[newIndex]];
        newIndex += 1;
      }
    }
    if (nextScan) queueLoadScan(nextScan, loadNext - 1);
    startReaderWorkerPool();
  }
}

/** Get next frame in specific experiment/scan */
function getNextFrame(experiments, experimentIndex, scanIndex) {
  const experiment = experiments[experimentIndex];
  const { scans } = experiment;

  if (scanIndex === scans.length - 1) {
    // last scan, go to next experiment
    if (experimentIndex === experiments.length - 1) {
      // last experiment, nowhere to go
      return null;
    }
    // get first scan in next experiment
    const nextExperiment = experiments[experimentIndex + 1];
    const nextScan = nextExperiment.scans[0]; // Get the first scan in the next experiment
    return nextScan.frames[0]; // Get the first frame in the nextScan
  }
  // get next scan in current experiment
  const nextScan = scans[scanIndex + 1];
  return nextScan.frames[0];
}

/**
 * Expands individual scan range
 *
 * If the range (e.g. [0, 3819] in a scan is <> the range read from data,
 * ensure that the ranges match
 */
function expandScanRange(frameId, dataRange) {
  if (frameId in store.state.frames) {
    // Get the scanId from the frame.
    const scanId = store.state.frames[frameId].scan;
    // Get the scan of specified scanId
    const scan = store.state.scans[scanId];
    if (scan && dataRange[0] < scan.cumulativeRange[0]) {
      [scan.cumulativeRange[0]] = dataRange;
    }
    if (scan && dataRange[1] > scan.cumulativeRange[1]) {
      [, scan.cumulativeRange[1]] = dataRange;
    }
  }
}

/** Determines whether a scan will be displayed based on its reviewed status */
export function includeScan(scanId) {
  if (store.state.reviewMode) {
    const myRole = store.state.currentTaskOverview?.my_project_role;
    const scanState = store.state.currentTaskOverview?.scan_states[scanId];
    switch (scanState) {
      case 'unreviewed':
        return true;
      case 'complete':
        return false;
      default:
        return myRole === 'tier_2_reviewer';
    }
  }
  return true;
}

const initState = {
  MIQAConfig: {
    version: '',
    artifact_options: [],
    artifact_states: {
      PRESENT: false,
    },
    auto_artifact_threshold: 0,
    NORMAL_USERS_CAN_CREATE_PROJECTS: false,
    S3_SUPPORT: true,
  },
  me: null,
  snackbar: null,
  allUsers: [],
  reviewMode: true,
  globalSettings: undefined as ProjectSettings,
  currentProject: undefined as Project | null,
  currentTaskOverview: null as ProjectTaskOverview | null,
  currentProjectPermissions: {},
  projects: [] as Project[],
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

export const storeConfig:StoreOptions<MIQAStore> = {
  state: {
    ...initState,
    workerPool: new WorkerPool(poolSize, poolFunction),
    lastApiRequestTime: Date.now(),
  },
  getters: {
    /** Returns current view's project, experiments, scans, frames, auto-evaluation, etc. */
    currentViewData(state) {
      const currentFrame = state.currentFrameId ? state.frames[state.currentFrameId] : null;
      const scan = currentFrame ? state.scans[currentFrame.scan] : undefined;
      if (!scan) {
        // scan was removed from list by review mode; do nothing
        return {};
      }
      const experiment = currentFrame.experiment
        ? state.experiments[currentFrame.experiment] : null;
      const project = state.projects.filter((x) => x.id === experiment.project)[0];
      // Get list of scans for current experiment
      const experimentScansList = state.experimentScans[experiment.id];
      // Get list of frames associated with current scan
      const scanFramesList = state.scanFrames[scan.id];

      const scanOrder = Object.values(state.experimentScans).flat().filter(includeScan);
      const currIndexInOrder = scanOrder.indexOf(scan.id);
      const upTo = scanOrder[currIndexInOrder - 1];
      const downTo = scanOrder[currIndexInOrder + 1];
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
        experimentScansList,
        scanFramesList,
        scanPosition: experimentScansList.indexOf(scan.id) + 1,
        framePosition: scanFramesList.indexOf(currentFrame.id) + 1,
        upTo,
        downTo,
        currentFrame,
        currentAutoEvaluation: currentFrame.frame_evaluation,
      };
    },
    /** Gets the current frame when given a frameId */
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
    /** Gets the current scan using the currentFrame */
    currentScan(state, getters) {
      if (getters.currentFrame) {
        const curScanId = getters.currentFrame.scan;
        return state.scans[curScanId];
      }
      return null;
    },
    /** Gets the current experiment using the currentScan */
    currentExperiment(state, getters) {
      if (getters.currentScan) {
        const curExperimentId = getters.currentScan.experiment;
        return state.experiments[curExperimentId];
      }
      return null;
    },
    /** Enumerates permissions of logged-in user */
    myCurrentProjectRoles(state) {
      const projectPerms = Object.entries(state.currentProjectPermissions)
        .filter((entry: [string, Array<User>]): boolean => entry[1].map(
          (user) => user.username,
        ).includes(state.me.username))
        .map((entry) => entry[0]);
      if (state.me.is_superuser) {
        projectPerms.push('superuser');
      }
      return projectPerms;
    },
    /** Returns true if no project has been selected */
    isGlobal(state) {
      return state.currentProject === null;
    },
  },
  mutations: {
    [RESET_STATE](state) {
      Object.assign(state, { ...state, ...initState });
    },
    [SET_MIQA_CONFIG](state, configuration) {
      if (!configuration) configuration = {};
      if (!configuration.version) configuration.version = '';
      state.MIQAConfig = configuration;
    },
    [SET_ME](state, me) {
      state.me = me;
    },
    [SET_SNACKBAR](state, snackbar) {
      state.snackbar = snackbar;
    },
    [SET_ALL_USERS](state, allUsers) {
      state.allUsers = allUsers;
    },
    [RESET_PROJECT_STATE](state) {
      state.experimentIds = [];
      state.experiments = {};
      state.experimentScans = {};
      state.scans = {};
      state.scanFrames = {};
      state.frames = {};
    },
    [SET_CURRENT_FRAME_ID](state, frameId) {
      state.currentFrameId = frameId;
    },
    /** Sets a specified frame at a specific index in the frames array */
    [SET_FRAME](state, { frameId, frame }) {
      // Replace with a new object to trigger a Vuex update
      state.frames = { ...state.frames };
      state.frames[frameId] = frame;
    },
    [SET_SCAN](state, { scanId, scan }) {
      // Replace with a new object to trigger a Vuex update
      state.scans = { ...state.scans };
      state.scans[scanId] = scan;
    },
    [SET_RENDER_ORIENTATION](state, anatomy) {
      state.renderOrientation = anatomy;
    },
    /** Also sets renderOrientation and currentProjectPermissions */
    [SET_CURRENT_PROJECT](state, project: Project | null) {
      state.currentProject = project;
      if (project) {
        state.renderOrientation = project.settings.anatomy_orientation;
        state.currentProjectPermissions = project.settings.permissions;
      }
    },
    [SET_GLOBAL_SETTINGS](state, settings) {
      state.globalSettings = settings;
    },
    [SET_TASK_OVERVIEW](state, taskOverview: ProjectTaskOverview) {
      if (!taskOverview) return;
      // Calculates total scans in project and scans that have been marked complete
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
      // If we have a value in state.currentProject, and it's id is equal to taskOverview's
      // project_id then:
      if (state.currentProject && taskOverview.project_id === state.currentProject.id) {
        state.currentTaskOverview = taskOverview;
        // Iterate over allScans
        Object.values(store.state.scans).forEach((scan: Scan) => {
          // If the scan exists and has been reviewed
          if (taskOverview.scan_states[scan.id] && taskOverview.scan_states[scan.id] !== 'unreviewed') {
            // Reload the scan
            store.dispatch('reloadScan', scan.id);
          }
        });
      }
    },
    [SET_PROJECTS](state, projects: Project[]) {
      state.projects = projects;
    },
    [ADD_SCAN_DECISION](state, { currentScanId, newScanDecision }) {
      state.scans[currentScanId].decisions.push(newScanDecision);
    },
    /** Pass in frame evaluation then attach the evaluation to the current frame */
    [SET_FRAME_EVALUATION](state, frameEvaluation) {
      const currentFrame = state.currentFrameId ? state.frames[state.currentFrameId] : null;
      if (currentFrame) {
        currentFrame.frame_evaluation = frameEvaluation;
      }
    },
    [SET_CURRENT_SCREENSHOT](state, screenshot) {
      state.currentScreenshot = screenshot;
    },
    [ADD_SCREENSHOT](state, screenshot) {
      state.screenshots.push(screenshot);
    },
    [REMOVE_SCREENSHOT](state, screenshot) {
      state.screenshots.splice(state.screenshots.indexOf(screenshot), 1);
    },
    [UPDATE_LAST_API_REQUEST_TIME](state) {
      state.lastApiRequestTime = Date.now();
    },
    [SET_LOADING_FRAME](state, isLoading: boolean) {
      state.loadingFrame = isLoading;
    },
    [SET_ERROR_LOADING_FRAME](state, isErrorLoading: boolean) {
      state.errorLoadingFrame = isErrorLoading;
    },
    /** Adds a scanId and it's corresponding scanFrames state */
    [ADD_SCAN_FRAMES](state, { scanId, frameId }) {
      state.scanFrames[scanId].push(frameId);
    },
    [ADD_EXPERIMENT_SCANS](state, { experimentId, scanId }) {
      state.scanFrames[scanId] = [];
      state.experimentScans[experimentId].push(scanId);
    },
    /**
     * Add an experiment to experiments state, it's id to experimentIds state, and
     * set experimentScans state to an empty array
     */
    [ADD_EXPERIMENT](state, { experimentId, experiment }) {
      state.experimentScans[experimentId] = [];
      if (!state.experimentIds.includes(experimentId)) {
        state.experimentIds.push(experimentId);
      }
      state.experiments[experimentId] = experiment;
    },
    [UPDATE_EXPERIMENT](state, experiment) {
      // Necessary for reactivity
      state.experiments = { ...state.experiments };
      state.experiments[experiment.id] = experiment;
    },
    /** Ensures that a specific image is being reviewed by a single individual */
    [SET_WINDOW_LOCKED](state, lockState) {
      state.windowLocked = lockState;
    },
    [SET_SCAN_CACHED_PERCENTAGE](state, percentComplete) {
      state.scanCachedPercentage = percentComplete;
    },
    /** Saves the location of the cursor click related to a specific scan and decision */
    [SET_SLICE_LOCATION](state, ijkLocation) {
      if (Object.values(ijkLocation).every((value) => value !== undefined)) {
        state.vtkViews.forEach(
          (view) => {
            state.proxyManager.getRepresentation(null, view).setSlice(
              ijkLocation[ijkMapping[view.getName()]],
            );
          },
        );
      }
    },
    [SET_CURRENT_VTK_INDEX_SLICES](state, { indexAxis, value }) {
      state[`${indexAxis}IndexSlice`] = value;
      state.sliceLocation = undefined;
    },
    [SET_SHOW_CROSSHAIRS](state, show: boolean) {
      state.showCrosshairs = show;
    },
    [SET_STORE_CROSSHAIRS](state, value: boolean) {
      state.storeCrosshairs = value;
    },
    [SET_REVIEW_MODE](state, mode) {
      state.reviewMode = mode || false;
    },
  },
  actions: {
    /** Reset the Vuex state of MIQA, cancel any existing tasks in the workerPool, clear file
     * and frame caches */
    reset({ state, commit }) {
      if (taskRunId >= 0) {
        state.workerPool.cancel(taskRunId);
        taskRunId = -1;
      }
      commit('RESET_STATE');
      fileCache.clear();
      frameCache.clear();
    },
    /** Pulls configuration from API and loads it into state */
    async loadConfiguration({ commit }) {
      const configuration = await djangoRest.MIQAConfig();
      commit('SET_MIQA_CONFIG', configuration);
    },
    /** Pulls user from API and loads it into state */
    async loadMe({ commit }) {
      const me = await djangoRest.me();
      commit('SET_ME', me);
    },
    /** Pulls all users from API and loads into state */
    async loadAllUsers({ commit }) {
      const allUsers = await djangoRest.allUsers();
      commit('SET_ALL_USERS', allUsers.results);
    },
    /** Pulls global settings from API and updates currentProject and globalSettings in state */
    async loadGlobal({ commit }) {
      const globalSettings = await djangoRest.globalSettings();
      commit('SET_CURRENT_PROJECT', null);
      commit('SET_GLOBAL_SETTINGS', {
        import_path: globalSettings.import_path,
        export_path: globalSettings.export_path,
      });
      commit('SET_TASK_OVERVIEW', {});
    },
    /** Pulls all projects from API and loads into state */
    async loadProjects({ commit }) {
      const projects = await djangoRest.projects();
      commit('SET_PROJECTS', projects);
    },
    /** Pulls an individual project from API and loads into state */
    async loadProject({ commit }, project: Project) {
      commit('RESET_PROJECT_STATE');

      // Build navigation links throughout the frame to improve performance.
      let firstInPrev = null;

      // Refresh the project from the API
      project = await djangoRest.project(project.id);
      commit('SET_CURRENT_PROJECT', project);

      // place data in state, adds each experiment to experiments
      const { experiments } = project;

      for (let experimentIndex = 0; experimentIndex < experiments.length; experimentIndex += 1) {
        // Get a specific experiment from the project
        const experiment = experiments[experimentIndex];
        // set experimentScans[experiment.id] before registering the experiment.id
        // so ExperimentsView doesn't update prematurely
        commit('ADD_EXPERIMENT', {
          experimentId: experiment.id,
          experiment: {
            id: experiment.id,
            name: experiment.name,
            note: experiment.note,
            project: experiment.project,
            index: experimentIndex,
            lockOwner: experiment.lock_owner,
          },
        });

        // Get the associated scans from the experiment
        // TODO these requests *can* be run in parallel, or collapsed into one XHR
        // eslint-disable-next-line no-await-in-loop
        const { scans } = experiment;
        for (let scanIndex = 0; scanIndex < scans.length; scanIndex += 1) {
          const scan = scans[scanIndex];
          commit('ADD_EXPERIMENT_SCANS', { experimentId: experiment.id, scanId: scan.id });

          // TODO these requests *can* be run in parallel, or collapsed into one XHR
          // eslint-disable-next-line no-await-in-loop
          const { frames } = scan;

          commit('SET_SCAN', {
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

          const nextScan = getNextFrame(experiments, experimentIndex, scanIndex);

          // then this is getting each frame associated with the scan
          for (let frameIndex = 0; frameIndex < frames.length; frameIndex += 1) {
            const frame = frames[frameIndex];
            commit('ADD_SCAN_FRAMES', { scanId: scan.id, frameId: frame.id });
            commit('SET_FRAME', {
              frameId: frame.id,
              frame: {
                ...frame,
                scan: scan.id,
                experiment: experiment.id,
                index: frameIndex,
                previousFrame: frameIndex > 0 ? frames[frameIndex - 1].id : null,
                nextFrame: frameIndex < frames.length - 1 ? frames[frameIndex + 1].id : null,
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
      commit('SET_TASK_OVERVIEW', taskOverview);
    },
    /** Add a scan to scans */
    async reloadScan({ commit, getters }, scanId) {
      const { currentFrame } = getters;
      scanId = scanId || currentFrame.scan;
      if (!scanId) return;
      const scan = await djangoRest.scan(scanId);
      commit('SET_SCAN', {
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
    async loadScan({ state, dispatch }, { scanId, projectId }) {
      if (!scanId || !state.projects) {
        return undefined;
      }
      // If currently loaded frameId does not match frameId to load
      if (!state.scans[scanId] && state.projects) {
        await dispatch('loadProjects');
        if (state.projects) {
          const targetProject = state.projects.filter((proj) => proj.id === projectId)[0];
          await dispatch('loadProject', targetProject);
        } else {
          return undefined;
        }
      }
      return state.scans[scanId];
    },
    /** Handles the process of changing frames */
    async swapToFrame({
      state, getters, commit,
    }, { frame, onDownloadProgress = null, loadAll = true }) {
      if (!frame) {
        throw new Error("frame id doesn't exist");
      }
      commit('SET_LOADING_FRAME', true);
      commit('SET_ERROR_LOADING_FRAME', false);

      if (loadAll) {
        const oldScan = getters.currentScan;
        // frame.scan returns the scan id
        const newScan = state.scans[frame.scan];

        // Queue the new scan to be loaded
        if (newScan !== oldScan && newScan) {
          queueLoadScan(newScan, 3);
        }
        let newProxyManager = false;
        // Create new proxyManager if scans are different, retain if same
        if (oldScan !== newScan && state.proxyManager) {
          // If we don't shrink and reinitialize between scans
          // we sometimes end up with no frame slices displayed.
          // This may be due to the extents changing between scans,
          // the extents do not change from one timestep to another
          // in a single scan.
          shrinkProxyManager(state.proxyManager);
          newProxyManager = true;
        }
        if (!state.proxyManager || newProxyManager) {
          state.proxyManager = vtkProxyManager.newInstance({
            proxyConfiguration: proxy,
          });
          state.vtkViews = [];
        }
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
          const result = await loadFileAndGetData(frame, { onDownloadProgress });
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
        commit('SET_ERROR_LOADING_FRAME', true);
      } finally {
        commit('SET_CURRENT_FRAME_ID', frame.id);
        commit('SET_LOADING_FRAME', false);
      }

      // check for window lock expiry
      if (loadAll && state.windowLocked.lock) {
        const { currentViewData } = getters;
        // Handles unlocking if necessary
        const unlock = () => {
          commit('SET_WINDOW_LOCKED', {
            lock: false,
            duration: undefined,
            target: undefined,
            associatedImage: undefined,
          });
        };
        // Unlocks window if scan, experiment, or project has changed
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
    /** Sets a lock on the current experiment */
    async setLock({ commit }, { experimentId, lock, force }) {
      if (lock) {
        commit(
          'UPDATE_EXPERIMENT',
          await djangoRest.lockExperiment(experimentId, force),
        );
      } else {
        commit(
          'UPDATE_EXPERIMENT',
          await djangoRest.unlockExperiment(experimentId),
        );
      }
    },
  },
};

const store = new Vuex.Store(storeConfig);

export default store;
