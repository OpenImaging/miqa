import BluebirdPromise from 'bluebird';
import { createDirectStore } from 'direct-vuex';
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

import djangoRest, { apiClient } from '@/django';
import { Project, Scan, ScanDecision } from '@/types';

const { convertItkToVtkImage } = ITKHelper;

Vue.use(Vuex);

const fileCache = new Map();
const datasetCache = new Map();
let readDataQueue = [];
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
  return new BluebirdPromise((resolve, reject) => {
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
            expandScanRange(id, dataRange);
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
    apiClient,
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
      return BluebirdPromise.resolve({ imageData });
    })
    .catch((error) => {
      const msg = 'loadFileAndGetData caught error getting data';
      console.log(msg);
      console.log(error);
      return BluebirdPromise.reject(msg);
    })
    .finally(() => {
      if (savedWorker) {
        savedWorker.terminate();
        savedWorker = null;
      }
    }));
}

function poolFunction(webWorker, taskInfo) {
  return new BluebirdPromise((resolve, reject) => {
    const { imageId } = taskInfo;

    let filePromise = null;

    if (fileCache.has(imageId)) {
      filePromise = fileCache.get(imageId);
    } else {
      filePromise = ReaderFactory.downloadDataset(
        apiClient,
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
  currentProject: null as Project | null,
  projects: [] as Project[],
  experimentIds: [],
  experiments: {},
  experimentScans: {},
  scans: {},
  scanDatasets: {},
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
  scanCachedPercentage: 0,
  currentAutoEvaluation: {},
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
      const currentDataset = state.currentDatasetId ? state.datasets[state.currentDatasetId] : null;
      const scan = state.scans[currentDataset.scan];
      const experiment = currentDataset.experiment
        ? state.experiments[currentDataset.experiment] : null;
      const project = state.sites.filter((x) => x.id === experiment.project)[0];
      const experimentScansList = state.experimentScans[experiment.id];
      const scanFramesList = state.scanDatasets[scan.id];
      return {
        projectName: project.name,
        experimentId: experiment.id,
        experimentName: experiment.name,
        experimentNote: experiment.note,
        locked: experiment.lockOwner != null,
        lockOwner: experiment.lockOwner,
        scanId: scan.id,
        scanName: scan.name,
        scanDecisions: scan.decisions,
        scanPositionString: `(${experimentScansList.indexOf(scan.id) + 1}/${experimentScansList.length})`,
        framePositionString: `(${scanFramesList.indexOf(currentDataset.id) + 1}/${scanFramesList.length})`,
        backTo: currentDataset.previousDataset,
        forwardTo: currentDataset.nextDataset,
        upTo: currentDataset.firstDatasetInPreviousScan,
        downTo: currentDataset.firstDatasetInNextScan,
        currentAutoEvaluation: currentDataset.auto_evaluation,
      };
    },

    currentDataset(state) {
      const { datasets, currentDatasetId } = state;
      return currentDatasetId ? datasets[currentDatasetId] : null;
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
    currentScan(state, getters) {
      if (getters.currentDataset) {
        const curScanId = getters.currentDataset.scan;
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
    experimentDatasets(state) {
      return (expId) => {
        const experimentScans = state.experimentScans[expId];
        const expDatasets = [];
        experimentScans.forEach((scanId) => {
          const scanDatasets = state.scanDatasets[scanId];
          scanDatasets.forEach((datasetId) => {
            expDatasets.push(datasetId);
          });
        });
        return expDatasets;
      };
    },
    firstDatasetInPreviousScan(state, getters) {
      return getters.currentDataset
        ? getters.currentDataset.firstDatasetInPreviousScan
        : null;
    },
    firstDatasetInNextScan(state, getters) {
      return getters.currentDataset
        ? getters.currentDataset.firstDatasetInNextScan
        : null;
    },
    firstDatasetInPreviousExeriment(state, getters) {
      if (getters.currentExperiment) {
        const expIdx = getters.currentExperiment.index;
        if (expIdx >= 1) {
          const prevExp = state.experiments[state.experimentIds[expIdx - 1]];
          const prevExpScans = state.experimentScans[prevExp.id];
          const prevExpScanDatasets = state.scanDatasets[prevExpScans[0].id];
          return prevExpScanDatasets[0];
        }
      }
      return null;
    },
    firstDatasetInNextExeriment(state, getters) {
      if (getters.currentExperiment) {
        const expIdx = getters.currentExperiment.index;
        if (expIdx < state.experimentIds.length - 1) {
          const nextExp = state.experiments[state.experimentIds[expIdx + 1]];
          const nextExpScans = state.experimentScans[nextExp.id];
          const nextExpScanDatasets = state.scanDatasets[nextExpScans[0].id];
          return nextExpScanDatasets[0];
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
      Object.assign(state, { ...state, ...initState });
    },
    resetProject(state) {
      state.experimentIds = [];
      state.experiments = {};
      state.experimentScans = {};
      state.scans = {};
      state.scanDatasets = {};
      state.datasets = {};
    },
    setCurrentImageId(state, imageId) {
      state.currentDatasetId = imageId;
    },
    setImage(state, { imageId, image }) {
      // Replace with a new object to trigger a Vuex update
      state.datasets = { ...state.datasets };
      state.datasets[imageId] = image;
    },
    setScan(state, { scanId, scan }) {
      // Replace with a new object to trigger a Vuex update
      state.scans = { ...state.scans };
      state.scans[scanId] = scan;
    },
    setCurrentProject(state, project: Project | null) {
      state.currentProject = project;
    },
    setProjects(state, projects: Project[]) {
      state.projects = projects;
    },
    addScanDecision(state, { currentScan, newDecision }) {
      state.scans[currentScan].decisions.push(newDecision);
    },
    setDrawer(state, value: boolean) {
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
    addScanDatasets(state, { sid, id }) {
      state.scanDatasets[sid].push(id);
    },
    addExperimentScans(state, { eid, sid }) {
      state.scanDatasets[sid] = [];
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
    resetScanDatasets(state, id) {
      state.scanDatasets[id] = [];
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

      const numScans = state.experimentScans[experimentID].length + 1;

      commit('addExperimentScans', { eid: experimentID, sid: scanID });
      commit('setScan', {
        scanId: scanID,
        scan: {
          id: scanID,
          name: `local-${numScans}`,
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

        commit('addScanDatasets', { sid: scanID, id: imageID });
        commit('setImage', {
          imageId: imageID,
          image: {
            ...f,
            id: imageID,
            scan: scanID,
            experiment: experimentID,
            index: k,
            previousDataset: prevId,
            // TODO link properly
            // nextDataset: k < images.length - 1 ? images[k + 1].id : null,
            // firstDatasetInPreviousScan: firstInPrev,
            // firstDatasetInNextScan: nextScan ? nextScan.id : null,
            local: true,
          },
        });

        fileCache.set(imageID, BluebirdPromise.resolve(f));

        if (prevId) {
          state.datasets[prevId].nextDataset = imageID;
        }

        prevId = imageID;
      }

      // last image
      state.datasets[prevId].nextDataset = null;
      // Replace with a new object to trigger a Vuex update
      state.datasets = { ...state.datasets };

      dispatch('swapToDataset', state.datasets[state.scanDatasets[scanID][0]]);
    },
    async loadProjects({ commit }) {
      const projects = await djangoRest.projects();
      commit('setProjects', projects);
    },
    async loadProject({ commit }, project: Project) {
      commit('resetProject');

      // Build navigation links throughout the dataset to improve performance.
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

          // Web datasets == Django images
          // TODO these requests *can* be run in parallel, or collapsed into one XHR
          // eslint-disable-next-line no-await-in-loop
          const { images } = scan;

          commit('setScan', {
            scanId: scan.id,
            scan: {
              id: scan.id,
              name: scan.name,
              experiment: experiment.id,
              cumulativeRange: [Number.MAX_VALUE, -Number.MAX_VALUE],
              numDatasets: images.length,
              site: scan.site,
              // The experiment.scans.note serialization does not contain note metadata.
              // Just set notes to [] and let reloadScan set the complete values later.
              notes: [],
              decisions: scan.decisions,
            },
          });

          const nextScan = getNextDataset(experiments, i, j);

          for (let k = 0; k < images.length; k += 1) {
            const image = images[k];
            commit('addScanDatasets', { sid: scan.id, id: image.id });
            commit('setImage', {
              imageId: image.id,
              image: {
                ...image,
                scan: scan.id,
                experiment: experiment.id,
                index: k,
                previousDataset: k > 0 ? images[k - 1].id : null,
                nextDataset: k < images.length - 1 ? images[k + 1].id : null,
                firstDatasetInPreviousScan: firstInPrev,
                firstDatasetInNextScan: nextScan ? nextScan.id : null,
              },
            });
          }

          if (images.length > 0) {
            firstInPrev = images[0].id;
          } else {
            console.error(
              `${experiment.name}/${scan.name} has no datasets`,
            );
          }
        }
      }
    },
    async reloadScan({ commit, getters }) {
      const currentImage = getters.currentDataset;
      // No need to reload if the image doesn't exist or doesn't exist on the server
      if (!currentImage || currentImage.local) {
        return;
      }
      const scanId = currentImage.scan;
      if (!scanId) {
        return;
      }
      const scan = await djangoRest.scan(scanId);
      const images = await djangoRest.images(scanId);
      commit('setScan', {
        scanId: scan.id,
        scan: {
          id: scan.id,
          name: scan.name,
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
      const oldScan = getters.currentScan;
      const newScan = state.scans[dataset.scan];
      const oldExperiment = getters.currentExperiment
        ? getters.currentExperiment
        : null;
      const newExperimentId = state.scans[dataset.scan].experiment;
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
      if (oldScan !== newScan && state.proxyManager) {
        // If we don't "shrinkProxyManager()" and reinitialize it between
        // scans, then we can end up with no image
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
          // initializing the screenshot view resets the render settings, so do it now instead of
          // when a screenshot is taken
          prepareScreenshotViews(state.proxyManager);
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
      const sites = await djangoRest.projects();
      commit('setSites', sites);
    },
    async lockExperiment({ commit }, experiment) {
      try {
        await djangoRest.lockExperiment(experiment.id);
      } catch {
        // Failing to acquire the lock probably means that someone else got the lock before you.
        // The following refresh will disable the button and show who currently owns the lock.
      }
      const {
        id, name, note, project, lock_owner: lockOwner,
      } = await djangoRest.experiment(experiment.id);
      commit('updateExperiment', {
        id,
        name,
        note,
        project,
        index: experiment.index,
        lockOwner,
      });
    },
    async unlockExperiment({ commit }, experiment) {
      try {
        await djangoRest.unlockExperiment(experiment.id);
      } catch {
        // Failing to unlock the lock probably means that someone else unlocked it for you.
        // The following refresh will show who currently owns the lock.
      }
      const {
        id, name, note, project, lock_owner: lockOwner,
      } = await djangoRest.experiment(experiment.id);
      commit('updateExperiment', {
        id,
        name,
        note,
        project,
        index: experiment.index,
        lockOwner,
      });
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

// cache datasets associated with scans of current experiment
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
      const scanDatasets = store.state.scanDatasets[scanId];
      scanDatasets.forEach((datasetId) => {
        fileCache.delete(datasetId);
        datasetCache.delete(datasetId);
      });
    });
  }

  readDataQueue = [];
  const newExperimentScans = store.state.experimentScans[newValue.id];
  newExperimentScans.forEach((scanId) => {
    const scanDatasets = store.state.scanDatasets[scanId];
    scanDatasets.forEach((datasetId) => {
      readDataQueue.push({
        // TODO don't hardcode projectId
        projectId: 1,
        experimentId: newValue.id,
        scanId,
        imageId: datasetId,
      });
    });
  });
  startReaderWorkerPool(); // eslint-disable-line no-use-before-define
}

function progressHandler(completed, total) {
  const percentComplete = completed / total;
  store.commit.setScanCachedPercentage(percentComplete);
}

function startReaderWorkerPool() {
  const taskArgsArray = [];

  store.commit.startLoadingExperiment();

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
      store.commit.stopLoadingExperiment();
      store.state.workerPool.terminateWorkers();
    });
}

function expandScanRange(datasetId, dataRange) {
  if (datasetId in store.state.datasets) {
    const scanId = store.state.datasets[datasetId].scan;
    const scan = store.state.scans[scanId];
    if (dataRange[0] < scan.cumulativeRange[0]) {
      [scan.cumulativeRange[0]] = dataRange;
    }
    if (dataRange[1] > scan.cumulativeRange[1]) {
      [, scan.cumulativeRange[1]] = dataRange;
    }
  }
}

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

// The following lines enable types in the injected store '$store'.
// They are causing linting errors, so they are skipped for now.
// declare module "vuex" {
//   interface Store<S> {
//     direct: AppStore
//   }
// }
