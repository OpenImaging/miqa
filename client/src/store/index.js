import Promise from 'bluebird';
import Vue from 'vue';
import Vuex from 'vuex';
import vtkProxyManager from 'vtk.js/Sources/Proxy/Core/ProxyManager';
import { InterpolationType } from 'vtk.js/Sources/Rendering/Core/ImageProperty/Constants';
import _ from 'lodash';
import { v4 as uuid } from 'uuid';

import '../utils/registerReaders';

import readImageArrayBuffer from 'itk/readImageArrayBuffer';
import WorkerPool from 'itk/WorkerPool';
import ITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper';
import ReaderFactory from '../utils/ReaderFactory';

import { proxy } from '../vtk';
import { getView } from '../vtk/viewManager';

import djangoRest from '../django';

const { convertItkToVtkImage } = ITKHelper;

Vue.use(Vuex);

const fileCache = new Map();
const datasetCache = new Map();
let readDataQueue = [];

const poolSize = navigator.hardwareConcurrency / 2 || 2;
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

function getArrayName(filename) {
  const idx = filename.lastIndexOf('.');
  const name = idx > -1 ? filename.substring(0, idx) : filename;
  return `Scalars ${name}`;
}

function getData(id, file, webWorker = null) {
  return new Promise((resolve, reject) => {
    if (datasetCache.has(id)) {
      resolve({ imageData: datasetCache.get(id), webWorker });
    } else {
      const fileName = file.name;
      const io = new FileReader();

      io.onload = function onLoad() {
        readImageArrayBuffer(webWorker, io.result, fileName)
          .then(({ webWorker, image }) => { // eslint-disable-line no-shadow
            const imageData = convertItkToVtkImage(image, {
              scalarArrayName: getArrayName(fileName),
            });
            const dataRange = imageData
              .getPointData()
              .getArray(0)
              .getRange();
            datasetCache.set(id, { imageData });
            // eslint-disable-next-line no-use-before-define
            expandSessionRange(id, dataRange);
            resolve({ imageData, webWorker });
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

function loadFile(imageId) {
  if (fileCache.has(imageId)) {
    return { imageId, fileP: fileCache.get(imageId) };
  }
  const p = ReaderFactory.downloadDataset(
    djangoRest.apiClient,
    'nifti.nii.gz',
    `/images/${imageId}/download`,
  );
  fileCache.set(imageId, p);
  return { imageId, fileP: p };
}

function loadFileAndGetData(imageId) {
  return loadFile(imageId).fileP.then((file) => getData(imageId, file, savedWorker)
    .then(({ webWorker, imageData }) => {
      savedWorker = webWorker;
      return Promise.resolve({ imageData });
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
    const { imageId } = taskInfo;

    let filePromise = null;

    if (fileCache.has(imageId)) {
      filePromise = fileCache.get(imageId);
    } else {
      filePromise = ReaderFactory.downloadDataset(
        djangoRest.apiClient,
        'nifti.nii.gz',
        `/images/${imageId}/download`,
      );
      fileCache.set(imageId, filePromise);
    }

    filePromise
      .then((file) => {
        resolve(getData(imageId, file, webWorker));
      })
      .catch((err) => {
        console.log('poolFunction: fileP error of some kind');
        console.log(err);
        reject(err);
      });
  });
}

// get next scan (across experiments)
function getNextDataset(experiments, i, j) {
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
    return nextScan.images[0];
  }
  // get next scan in current experiment
  const nextScan = scans[j + 1];
  return nextScan.images[0];
}

const initState = {
  drawer: false,
  experimentIds: [],
  experiments: {},
  experimentSessions: {},
  sessions: {},
  sessionDatasets: {},
  datasets: {},
  proxyManager: null,
  vtkViews: [],
  currentDatasetId: null,
  loadingDataset: false,
  errorLoadingDataset: false,
  loadingExperiment: false,
  currentScreenshot: null,
  screenshots: [],
  sites: null,
  sessionCachedPercentage: 0,
  sessionStatus: null,
};

const store = new Vuex.Store({
  state: {
    ...initState,
    workerPool: new WorkerPool(poolSize, poolFunction),
    actionTimer: null,
    actionTimeout: false,
  },
  getters: {
    currentDataset(state) {
      return state.currentDatasetId
        ? state.datasets[state.currentDatasetId]
        : null;
    },
    previousDataset(state, getters) {
      return getters.currentDataset
        ? getters.currentDataset.previousDataset
        : null;
    },
    nextDataset(state, getters) {
      return getters.currentDataset ? getters.currentDataset.nextDataset : null;
    },
    getDataset(state) {
      return (datasetId) => {
        if (!datasetId || !state.datasets[datasetId]) {
          return undefined;
        }
        return state.datasets[datasetId];
      };
    },
    currentSession(state, getters) {
      if (getters.currentDataset) {
        const curSessionId = getters.currentDataset.session;
        return state.sessions[curSessionId];
      }
      return null;
    },
    currentExperiment(state, getters) {
      if (getters.currentSession) {
        const curExperimentId = getters.currentSession.experiment;
        return state.experiments[curExperimentId];
      }
      return null;
    },
    experimentDatasets(state) {
      return (expId) => {
        const experimentSessions = state.experimentSessions[expId];
        const expDatasets = [];
        experimentSessions.forEach((sessionId) => {
          const sessionDatasets = state.sessionDatasets[sessionId];
          sessionDatasets.forEach((datasetId) => {
            expDatasets.push(datasetId);
          });
        });
        return expDatasets;
      };
    },
    getTodoById: (state) => (id) => state.todos.find((todo) => todo.id === id),
    firstDatasetInPreviousSession(state, getters) {
      return getters.currentDataset
        ? getters.currentDataset.firstDatasetInPreviousSession
        : null;
    },
    firstDatasetInNextSession(state, getters) {
      return getters.currentDataset
        ? getters.currentDataset.firstDatasetInNextSession
        : null;
    },
    firstDatasetInPreviousExeriment(state, getters) {
      if (getters.currentExperiment) {
        const expIdx = getters.currentExperiment.index;
        if (expIdx >= 1) {
          const prevExp = state.experiments[state.experimentIds[expIdx - 1]];
          const prevExpSessions = state.experimentSessions[prevExp.id];
          const prevExpSessionDatasets = state.sessionDatasets[prevExpSessions[0].id];
          return prevExpSessionDatasets[0];
        }
      }
      return null;
    },
    firstDatasetInNextExeriment(state, getters) {
      if (getters.currentExperiment) {
        const expIdx = getters.currentExperiment.index;
        if (expIdx < state.experimentIds.length - 1) {
          const nextExp = state.experiments[state.experimentIds[expIdx + 1]];
          const nextExpSessions = state.experimentSessions[nextExp.id];
          const nextExpSessionDatasets = state.sessionDatasets[nextExpSessions[0].id];
          return nextExpSessionDatasets[0];
        }
      }
      return null;
    },
    siteMap(state) {
      if (!state.sites) {
        return {};
      }
      return _.keyBy(state.sites, 'id');
    },
    getSiteDisplayName(state, getters) {
      return (id) => {
        const { siteMap } = getters;
        if (siteMap[id]) {
          return siteMap[id].name;
        }
        return id;
      };
    },
    getExperimentDisplayName(state) {
      return (id) => {
        if (state.experiments[id]) {
          return state.experiments[id].name;
        }
        return id;
      };
    },
  },
  mutations: {
    reset(state) {
      Vue.set(state, { ...state, ...initState });
    },
    resetSession(state) {
      state.experimentIds = [];
      state.experiments = {};
      state.experimentSessions = {};
      state.sessions = {};
      state.sessionDatasets = {};
      state.datasets = {};
    },
    setCurrentImageId(state, imageId) {
      state.currentDatasetId = imageId;
    },
    setImage(state, { imageId, image }) {
      state.datasets[imageId] = image;
    },
    setScan(state, { scanId, scan }) {
      // Replace with a new object to trigger a Vuex update
      state.sessions = { ...state.sessions };
      state.sessions[scanId] = scan;
    },
    setDrawer(state, value) {
      state.drawer = value;
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
    setLoadingDataset(state, value) {
      state.loadingDataset = value;
    },
    setErrorLoadingDataset(state, value) {
      state.errorLoadingDataset = value;
    },
    setSites(state, sites) {
      state.sites = sites;
    },
    addSessionDatasets(state, { sid, id }) {
      state.sessionDatasets[sid].push(id);
    },
    addExperimentSessions(state, { eid, sid }) {
      state.sessionDatasets[sid] = [];
      state.experimentSessions[eid].push(sid);
    },
    addExperiment(state, { id, value }) {
      state.experimentSessions[id] = [];
      state.experimentIds.push(id);
      state.experiments[id] = value;
    },
    resetSessionDatasets(state, id) {
      state.sessionDatasets[id] = [];
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
      datasetCache.clear();
    },
    async logout({ dispatch }) {
      dispatch('reset');
      await djangoRest.logout();
    },
    // load all nifti files into a single experiment + single scan
    async loadLocalDataset({ state, commit, dispatch }, files) {
      // Use a static UUID for the experiment which contains all local scans
      const experimentID = '276be8dd-aa3c-4ee7-a3a9-581783717a50';
      const scanID = uuid();

      if (!(experimentID in state.experiments)) {
        commit('addExperiment', {
          id: experimentID,
          value: {
            id: experimentID,
            name: 'LOCAL',
            index: 0,
          },
        });
      }

      const numSessions = state.experimentSessions[experimentID].length + 1;

      commit('addExperimentSessions', { eid: experimentID, sid: scanID });
      commit('setScan', {
        scanId: scanID,
        scan: {
          id: scanID,
          name: `local-${numSessions}`,
          experiment: experimentID,
          cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
          numDatasets: files.length,
          site: 'local',
          notes: [],
          decisions: [],
        },
      });

      let prevId = null;

      for (let k = 0; k < files.length; k += 1) {
        const imageID = uuid();
        const f = files[k];

        commit('addSessionDatasets', { sid: scanID, id: imageID });
        commit('setImage', {
          imageId: imageID,
          image: {
            ...f,
            id: imageID,
            session: scanID,
            experiment: experimentID,
            index: k,
            previousDataset: prevId,
            // TODO link properly
            // nextDataset: k < images.length - 1 ? images[k + 1].id : null,
            // firstDatasetInPreviousSession: firstInPrev,
            // firstDatasetInNextSession: nextScan ? nextScan.id : null,
            local: true,
          },
        });

        fileCache.set(imageID, Promise.resolve(f));

        if (prevId) {
          state.datasets[prevId].nextDataset = imageID;
        }

        prevId = imageID;
      }

      // last image
      state.datasets[prevId].nextDataset = null;

      dispatch('swapToDataset', state.datasets[state.sessionDatasets[scanID][0]]);
    },
    async loadSession({ commit }, session) {
      commit('resetSession');

      // Build navigation links throughout the dataset to improve performance.
      let firstInPrev = null;

      if (session) {
        // load first available session
        session = await djangoRest.session(session.id);
      } else {
        // no sessions: can't load any
        return;
      }

      // place data in state
      const { experiments } = session;

      for (let i = 0; i < experiments.length; i += 1) {
        const experiment = experiments[i];
        // set experimentSessions[experiment.id] before registering the experiment.id
        // so SessionsView doesn't update prematurely
        commit('addExperiment', {
          id: experiment.id,
          value: {
            id: experiment.id,
            name: experiment.name,
            index: i,
          },
        });

        // Web sessions == Django scans
        // TODO these requests *can* be run in parallel, or collapsed into one XHR
        // eslint-disable-next-line no-await-in-loop
        const { scans } = experiment;
        for (let j = 0; j < scans.length; j += 1) {
          const scan = scans[j];
          commit('addExperimentSessions', { eid: experiment.id, sid: scan.id });

          // Web datasets == Django images
          // TODO these requests *can* be run in parallel, or collapsed into one XHR
          // eslint-disable-next-line no-await-in-loop
          const { images } = scan;

          commit('setScan', {
            scanId: scan.id,
            scan: {
              id: scan.id,
              name: scan.scan_type,
              experiment: experiment.id,
              cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
              numDatasets: images.length,
              site: scan.site,
              notes: scan.notes,
              decisions: scan.decisions,
            },
          });

          const nextScan = getNextDataset(experiments, i, j);

          for (let k = 0; k < images.length; k += 1) {
            const image = images[k];
            commit('addSessionDatasets', { sid: scan.id, id: image.id });
            commit('setImage', {
              imageId: image.id,
              image: {
                ...image,
                session: scan.id,
                experiment: experiment.id,
                index: k,
                previousDataset: k > 0 ? images[k - 1].id : null,
                nextDataset: k < images.length - 1 ? images[k + 1].id : null,
                firstDatasetInPreviousSession: firstInPrev,
                firstDatasetInNextSession: nextScan ? nextScan.id : null,
              },
            });
          }

          if (images.length > 0) {
            firstInPrev = images[0].id;
          } else {
            console.error(
              `${experiment.name}/${scan.scan_type} has no datasets`,
            );
          }
        }
      }
    },
    // This would be called reloadSession, but session is being renamed to scan
    async reloadScan({ commit, getters }) {
      const currentImage = getters.currentDataset;
      // No need to reload if the image doesn't exist or doesn't exist on the server
      if (!currentImage || currentImage.local) {
        return;
      }
      const scanId = currentImage.session;
      if (!scanId) {
        return;
      }
      const scan = await djangoRest.scan(scanId);
      const images = await djangoRest.images(scanId);
      commit('setScan', {
        scanId: scan.id,
        scan: {
          id: scan.id,
          name: scan.scan_type,
          experiment: scan.experiment,
          cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
          numDatasets: images.length,
          site: scan.site,
          notes: scan.notes,
          decisions: scan.decisions,
        },
      });
    },
    async setCurrentImage({ commit, dispatch }, imageId) {
      commit('setCurrentImageId', imageId);
      if (imageId) {
        dispatch('reloadScan');
      }
    },
    async swapToDataset({
      state, dispatch, getters, commit,
    }, dataset) {
      if (!dataset) {
        throw new Error("dataset id doesn't exist");
      }
      if (getters.currentDataset === dataset) {
        return;
      }
      commit('setLoadingDataset', true);
      commit('setErrorLoadingDataset', false);
      const oldSession = getters.currentSession;
      const newSession = state.sessions[dataset.session];
      const oldExperiment = getters.currentExperiment
        ? getters.currentExperiment
        : null;
      const newExperimentId = state.sessions[dataset.session].experiment;
      const newExperiment = state.experiments[newExperimentId];

      // Check if we should cancel the currently loading experiment
      if (
        newExperiment
        && oldExperiment
        && newExperiment.folderId !== oldExperiment.folderId
        && taskRunId >= 0
      ) {
        state.workerPool.cancel(taskRunId);
        taskRunId = -1;
      }

      let newProxyManager = false;
      if (oldSession !== newSession && state.proxyManager) {
        // If we don't "shrinkProxyManager()" and reinitialize it between
        // "sessions" (a.k.a "scans"), then we can end up with no image
        // slices displayed, even though we have the data and attempted
        // to render it.  This may be due to image extents changing between
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
        let imageData = null;
        if (datasetCache.has(dataset.id)) {
          imageData = datasetCache.get(dataset.id).imageData;
        } else {
          const result = await loadFileAndGetData(dataset.id);
          imageData = result.imageData;
        }
        sourceProxy.setInputData(imageData);
        if (needPrep || !state.proxyManager.getViews().length) {
          prepareProxyManager(state.proxyManager);
          state.vtkViews = state.proxyManager.getViews();
        }
        if (!state.vtkViews.length) {
          state.vtkViews = state.proxyManager.getViews();
        }
      } catch (err) {
        console.log('Caught exception loading next image');
        console.log(err);
        state.vtkViews = [];
        commit('setErrorLoadingDataset', true);
      } finally {
        dispatch('setCurrentImage', dataset.id);
        commit('setLoadingDataset', false);
      }

      // If necessary, queue loading scans of new experiment
      // eslint-disable-next-line no-use-before-define
      checkLoadExperiment(oldExperiment, newExperiment);
    },
    async loadSites({ commit }) {
      const sites = await djangoRest.sites();
      commit('setSites', sites);
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

// cache datasets associated with sessions of current experiment
function checkLoadExperiment(oldValue, newValue) {
  if (
    !newValue
    || newValue === oldValue
    || (newValue && oldValue && newValue.folderId === oldValue.folderId)
  ) {
    return;
  }

  if (oldValue) {
    const oldExperimentSessions = store.state.experimentSessions[oldValue.id];
    oldExperimentSessions.forEach((sessionId) => {
      const sessionDatasets = store.state.sessionDatasets[sessionId];
      sessionDatasets.forEach((datasetId) => {
        fileCache.delete(datasetId);
        datasetCache.delete(datasetId);
      });
    });
  }

  readDataQueue = [];
  const newExperimentSessions = store.state.experimentSessions[newValue.id];
  newExperimentSessions.forEach((sessionId) => {
    const sessionDatasets = store.state.sessionDatasets[sessionId];
    sessionDatasets.forEach((datasetId) => {
      readDataQueue.push({
        // TODO don't hardcode sessionId
        sessionId: 1,
        experimentId: newValue.id,
        scanId: sessionId,
        imageId: datasetId,
      });
    });
  });
  startReaderWorkerPool(); // eslint-disable-line no-use-before-define
}

function progressHandler(completed, total) {
  const percentComplete = completed / total;
  store.state.sessionCachedPercentage = percentComplete;
}

function startReaderWorkerPool() {
  const taskArgsArray = [];

  store.state.loadingExperiment = true;

  readDataQueue.forEach((taskInfo) => {
    taskArgsArray.push([taskInfo]);
  });

  readDataQueue = [];

  const { runId, promise } = store.state.workerPool.runTasks(
    taskArgsArray,
    progressHandler,
  );
  taskRunId = runId;

  promise
    .then((results) => {
      console.log(`WorkerPool finished with ${results.length} results`);
      taskRunId = -1;
    })
    .catch((err) => {
      console.log('startReaderWorkerPool: workerPool error');
      console.log(err);
    })
    .finally(() => {
      store.state.loadingExperiment = false;
      store.state.workerPool.terminateWorkers();
    });
}

function expandSessionRange(datasetId, dataRange) {
  if (datasetId in store.state.datasets) {
    const sessionId = store.state.datasets[datasetId].session;
    const session = store.state.sessions[sessionId];
    if (dataRange[0] < session.cumulativeRange[0]) {
      [session.cumulativeRange[0]] = dataRange;
    }
    if (dataRange[1] > session.cumulativeRange[1]) {
      [, session.cumulativeRange[1]] = dataRange;
    }
  }
}

export default store;
