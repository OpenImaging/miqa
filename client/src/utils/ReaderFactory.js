import { CancelToken } from 'axios';
import Promise from 'bluebird';

Promise.config({
  longStackTraces: false,
  warnings: false, // note, run node with --trace-warnings to see full stack traces for warnings,
  cancellation: true,
});

const READER_MAPPING = {};

const FETCH_DATA = {
  readAsArrayBuffer(axios, url, source) {
    return axios
      .get(url, {
        cancelToken: source.token,
        responseType: 'arraybuffer',
      })
      .then(({ data }) => data);
  },
};

function registerReader({
  extension,
  name,
  vtkReader,
  readMethod,
  parseMethod,
  fileNameMethod,
  fileSeriesMethod,
  sourceType,
  binary,
}) {
  READER_MAPPING[extension] = {
    name,
    vtkReader,
    readMethod: readMethod || binary ? 'readAsArrayBuffer' : 'readAsText',
    parseMethod: parseMethod || binary ? 'parseAsArrayBuffer' : 'parseAsText',
    fileNameMethod,
    fileSeriesMethod,
    sourceType,
  };
}

function getReader({ name }) {
  const lowerCaseName = name.toLowerCase();
  const extToUse = Object.keys(READER_MAPPING).find((ext) => lowerCaseName.endsWith(ext));
  return READER_MAPPING[extToUse];
}

function readRawData({ fileName, data }) {
  return new Promise((resolve, reject) => {
    const readerMapping = getReader({ name: fileName });
    if (readerMapping) {
      const {
        vtkReader,
        parseMethod,
        fileNameMethod,
        sourceType,
      } = readerMapping;
      const reader = vtkReader.newInstance();
      if (fileNameMethod) {
        reader[fileNameMethod](fileName);
      }
      const ds = reader[parseMethod](data);
      Promise.resolve(ds)
        .then((dataset) => resolve({
          dataset,
          reader,
          sourceType,
          name: fileName,
        }))
        .catch(reject);
    } else {
      reject();
    }
  });
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const readerMapping = getReader(file);
    if (readerMapping) {
      const { readMethod } = readerMapping;
      const io = new FileReader();
      io.onload = function onLoad() {
        readRawData({ fileName: file.name, data: io.result })
          .then((result) => resolve(result))
          .catch((error) => reject(error));
      };
      io[readMethod](file);
    } else {
      reject(new Error('No reader mapping'));
    }
  });
}

function loadFiles(files) {
  const promises = [];
  for (let i = 0; i < files.length; i += 1) {
    promises.push(readFile(files[i]));
  }
  return Promise.all(promises);
}

function downloadDataset(axios, fileName, url) {
  return new Promise((resolve, reject, onCancel) => {
    const readerMapping = getReader({ name: fileName });
    if (readerMapping) {
      const { readMethod } = readerMapping;
      const source = CancelToken.source();
      FETCH_DATA[readMethod](axios, url, source)
        .then((rawData) => {
          if (rawData) {
            resolve(new File([rawData], fileName));
          } else {
            throw new Error(`No data for ${fileName}`);
          }
        })
        .catch(reject);
      onCancel(() => {
        source.cancel('navigated away');
      });
    } else {
      throw new Error(`No reader found for ${fileName}`);
    }
  });
}

export default {
  downloadDataset,
  loadFiles,
  registerReader,
};
