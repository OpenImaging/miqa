/* eslint-disable consistent-return */
import axios from 'axios';
import OAuthClient from '@girder/oauth-client';
import S3FileFieldClient from 'django-s3-file-field';

import {
  ResponseData, Project, ProjectTaskOverview, ProjectSettings, User, Email, Experiment, Scan, Frame,
} from './types';
import { API_URL, OAUTH_API_ROOT, OAUTH_CLIENT_ID } from './constants';

interface Paginated<T> {
  count: number,
  next: string,
  previous: string,
  results: T[],
}

class ErrorResponseDetail extends Error {
  constructor(message) {
    super(message);
    this.name = 'Server Error';
  }
}

const apiClient = axios.create({ baseURL: API_URL });
let s3ffClient;

const oauthClient = new OAuthClient(OAUTH_API_ROOT, OAUTH_CLIENT_ID);
const djangoClient = {
  async restoreLogin(store) {
    await oauthClient.maybeRestoreLogin();
    if (oauthClient.isLoggedIn) {
      Object.assign(
        apiClient.defaults.headers.common,
        oauthClient.authHeaders,
      );
      s3ffClient = new S3FileFieldClient({
        baseUrl: `${API_URL}/s3-upload/`,
        apiConfig: {
          headers: apiClient.defaults.headers.common,
        },
      });
    } else {
      await this.login();
    }

    // mark user not-idle
    apiClient.interceptors.request.use(async (config) => {
      await oauthClient.maybeRestoreLogin();
      await store.commit('UPDATE_LAST_API_REQUEST_TIME');

      return config;
    }, (error) => Promise.reject(error));
  },
  async login() {
    await oauthClient.redirectToLogin();
  },
  async logout() {
    try {
      await apiClient.post('/logout/', undefined, { withCredentials: true });
    } finally {
      await oauthClient.logout().then(
        async () => {
          await oauthClient.redirectToLogin();
        },
      );
    }
  },
  async MIQAConfig() {
    const response = await apiClient.get('/configuration/');
    return response?.data;
  },
  async globalSettings() {
    const response = await apiClient.get('/global/settings');
    return response?.data;
  },
  async globalImport(): Promise<ResponseData> {
    const response = await apiClient.post('/global/import');
    return response?.data;
  },
  async projectImport(projectId: string): Promise<ResponseData> {
    const response = await apiClient.post(`/projects/${projectId}/import`);
    return response?.data;
  },
  async globalExport(): Promise<ResponseData> {
    const response = await apiClient.post('/global/export');
    return response?.data;
  },
  async projectExport(projectId: string): Promise<ResponseData> {
    if (!projectId) return undefined;
    const response = await apiClient.post(`/projects/${projectId}/export`);
    return response?.data;
  },
  async createProject(projectName: string): Promise<Project> {
    if (!projectName) return undefined;
    const response = await apiClient.post('/projects', { name: projectName });
    return response?.data;
  },
  async deleteProject(projectId: string): Promise<ResponseData> {
    if (!projectId) return undefined;
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response?.data;
  },
  async projects(): Promise<Project[]> {
    const response = await apiClient.get('/projects');
    return response?.data?.results;
  },
  async project(projectId: string): Promise<Project> {
    if (!projectId) return undefined;
    const response = await apiClient.get(`/projects/${projectId}`);
    return response?.data;
  },
  async projectTaskOverview(projectId: string): Promise<ProjectTaskOverview> {
    if (!projectId) return undefined;
    const response = await apiClient.get(`/projects/${projectId}/task_overview`);
    return response?.data;
  },
  async settings(projectId: string): Promise<ProjectSettings> {
    if (!projectId) return undefined;
    const response = await apiClient.get(`/projects/${projectId}/settings`);
    return response?.data;
  },
  async setGlobalSettings(settings: ProjectSettings): Promise<ResponseData> {
    if (!settings) return undefined;
    const response = await apiClient.put('/global/settings', settings);
    return response?.data;
  },
  async setProjectSettings(projectId: string, settings): Promise<ResponseData> {
    if (!projectId || !settings) return undefined;
    const response = await apiClient.put(`/projects/${projectId}/settings`, settings);
    return response?.data;
  },
  async experiments(projectId: string): Promise<Experiment[]> {
    if (!projectId) return undefined;
    const response = await apiClient.get('/experiments', {
      params: { project: projectId },
    });
    return response?.data?.results;
  },
  async experiment(experimentId: string): Promise<Experiment> {
    if (!experimentId) return undefined;
    const response = await apiClient.get(`/experiments/${experimentId}`);
    return response?.data;
  },
  async createExperiment(projectId:string, experimentName: string): Promise<ResponseData> {
    if (!projectId || !experimentName) return undefined;
    const response = await apiClient.post('/experiments', {
      // This returns id, name, lock_owner, scans, project, note - why we do
      // only have project and name specified here?
      project: projectId,
      name: experimentName,
    });
    if (response.status === 500 && response?.data?.detail) {
      throw new ErrorResponseDetail(response.data.detail);
    }
    return response?.data;
  },
  async uploadToExperiment(experimentId: string, files: File[]) {
    if (!experimentId || !files) return undefined;
    // Promise.all maintains order so we can reference filenames by index
    const uploadResponses = await Promise.all(files.map(
      (file) => s3ffClient.uploadFile(file, 'core.Frame.content'),
    ));
    await Promise.all(uploadResponses.map(
      async (uploadResponse, index) => apiClient.post('/frames', {
        experiment: experimentId,
        content: uploadResponse.value,
        filename: files[index].name,
      }),
    ));
  },
  async setExperimentNote(experimentId: string, note: string): Promise<ResponseData> {
    if (!experimentId) return undefined;
    const response = await apiClient.post(`/experiments/${experimentId}/note`, { note });
    return response?.data;
  },
  async lockExperiment(experimentId: string, force: boolean): Promise<ResponseData> {
    if (!experimentId) return undefined;
    const response = await apiClient.post(`/experiments/${experimentId}/lock`, { force });
    return response?.data;
  },
  async unlockExperiment(experimentId: string): Promise<ResponseData> {
    if (!experimentId) return undefined;
    const response = await apiClient.delete(`/experiments/${experimentId}/lock`);
    return response?.data;
  },
  async deleteExperiment(experimentId: string): Promise<ResponseData> {
    if (!experimentId) return undefined;
    const response = await apiClient.delete(`/experiments/${experimentId}`);
    return response?.data;
  },
  async scans(experimentId: string): Promise<Scan[]> {
    if (!experimentId) return undefined;
    const response = await apiClient.get('/scans', {
      params: { experiment: experimentId },
    });
    return response?.data?.results;
  },
  async scan(scanId: string): Promise<Scan> {
    if (!scanId) return undefined;
    const response = await apiClient.get(`/scans/${scanId}`);
    return response?.data;
  },
  async setDecision(
    scanId: string,
    decision: string,
    comment: string,
    userIdentifiedArtifacts: object,
    location: object,
  ): Promise<ResponseData> {
    if (!scanId) return undefined;
    const response = await apiClient.post('/scan-decisions', {
      scan: scanId, decision, note: comment, artifacts: userIdentifiedArtifacts, location,
    });
    return response?.data;
  },
  async frames(scanId: string): Promise<Frame[]> {
    if (!scanId) return undefined;
    const response = await apiClient.get('/frames', {
      params: { scan: scanId },
    });
    return response?.data?.results;
  },
  async frame(frameId: string): Promise<Frame> {
    if (!frameId) return undefined;
    const response = await apiClient.get(`/frames/${frameId}`);
    return response?.data;
  },
  async me(): Promise<User> {
    const response = await apiClient.get('/users/me');
    return response?.data;
  },
  async allUsers(): Promise<Paginated<User>> {
    const response = await apiClient.get('/users');
    return response?.data;
  },
  async sendEmail(email: Email) {
    await apiClient.post('/email', email);
  },
};

apiClient.interceptors.response.use(null, (error) => {
  if (error?.response?.status === 401) {
    dispatchEvent(new Event('unauthorized'));
  }
  return error.response;
});

export { apiClient, oauthClient };
export default djangoClient;
