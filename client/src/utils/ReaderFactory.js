import { CancelToken } from 'axios';

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

function downloadFrame(axios, fileName, url) {
  return new Promise((resolve, reject) => {
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
    } else {
      throw new Error(`No reader found for ${fileName}`);
    }
  });
}

export default {
  downloadFrame,
  registerReader,
};
