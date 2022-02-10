import axios from 'axios';
import OAuthClient from '@girder/oauth-client';
import S3FileFieldClient from 'django-s3-file-field';

import {
  Project, ProjectTaskOverview, ProjectSettings, User,
} from './types';
import { API_URL, OAUTH_API_ROOT, OAUTH_CLIENT_ID } from './constants';

interface Paginated<T> {
  count: number,
  next: string,
  previous: string,
  results: T[],
}

const apiClient = axios.create({ baseURL: API_URL });
let s3ffClient;

apiClient.interceptors.response.use(null, (error) => {
  const msg = error?.response?.data?.detail || 'No response from server';
  throw new Error(msg);
});
const oauthClient = new OAuthClient(OAUTH_API_ROOT, OAUTH_CLIENT_ID);
const djangoClient = {
  // TODO importing the actual AppStore type results in a dependency cycle
  async restoreLogin(store: any) {
    await oauthClient.maybeRestoreLogin();
    if (oauthClient.isLoggedIn) {
      Object.assign(
        apiClient.defaults.headers.common,
        oauthClient.authHeaders,
      );
      s3ffClient = new S3FileFieldClient({
        baseUrl: API_URL + '/s3-upload/',
        apiConfig: {
          headers: apiClient.defaults.headers.common,
        },
      });
    } else {
      this.login();
    }

    // mark user not-idle
    apiClient.interceptors.request.use(async (config) => {
      await oauthClient.maybeRestoreLogin();
      await store.dispatch.resetActionTimer();

      return config;
    }, (error) => Promise.reject(error));
  },
  async login() {
    await oauthClient.redirectToLogin();
  },
  async logout() {
    await apiClient.post('/logout/', undefined, { withCredentials: true });
    await oauthClient.logout();
  },
  async MIQAConfig() {
    const { data } = await apiClient.get('/configuration/');
    return data;
  },
  async globalSettings() {
    const { data } = await apiClient.get('/global/settings');
    return data;
  },
  async globalImport() {
    await apiClient.post('/global/import');
  },
  async projectImport(projectId: string) {
    await apiClient.post(`/projects/${projectId}/import`);
  },
  async globalExport() {
    return apiClient.post('/global/export');
  },
  async projectExport(projectId: string) {
    return apiClient.post(`/projects/${projectId}/export`);
  },
  async createProject(projectName: string): Promise<Project> {
    const { data } = await apiClient.post('/projects', { name: projectName });
    return data;
  },
  async deleteProject(projectId: string) {
    const { data } = await apiClient.delete(`/projects/${projectId}`);
    return data;
  },
  async projects(): Promise<Project[]> {
    const { data } = await apiClient.get('/projects');
    const { results } = data;
    return results;
  },
  async project(projectId: string): Promise<Project> {
    const { data } = await apiClient.get(`/projects/${projectId}`);
    return data;
  },
  async projectTaskOverview(projectId: string): Promise<ProjectTaskOverview> {
    const { data } = await apiClient.get(`/projects/${projectId}/task_overview`);
    return data;
  },
  async settings(projectId: string): Promise<ProjectSettings> {
    const { data } = await apiClient.get(`/projects/${projectId}/settings`);
    return data;
  },
  async setGlobalSettings(settings: ProjectSettings) {
    const resp = await apiClient.put('/global/settings', settings);
    return resp.status === 200 ? resp.data : null;
  },
  async setProjectSettings(projectId: string, settings: ProjectSettings) {
    const resp = await apiClient.put(`/projects/${projectId}/settings`, settings);
    return resp.status === 200 ? resp.data : null;
  },
  async experiments(projectId: string) {
    const { data } = await apiClient.get('/experiments', {
      params: { project: projectId },
    });
    const { results } = data;
    return results;
  },
  async experiment(experimentId: string) {
    const { data } = await apiClient.get(`/experiments/${experimentId}`);
    return data;
  },
  async createExperiment(projectId:string, experimentName: string) {
    const { data } = await apiClient.post(`/experiments`, {
      project: projectId,
      name: experimentName
    });
    return data;
  },
  async uploadToExperiment(experimentId: string, files: File[]) {
    // Promise.all maintains order so we can reference filenames by index
    const uploadResponses = await Promise.all(files.map(
      (file) => s3ffClient.uploadFile(file, 'core.Frame.content')
    ))
    await Promise.all(uploadResponses.map(
      async (uploadResponse, index) => {
      return apiClient.post(`/frames`, {
        experiment: experimentId,
        content: uploadResponse.value,
        filename: files[index].name,
      });
    }));
  },
  async setExperimentNote(experimentId: string, note: string) {
    const { data } = await apiClient.post(`/experiments/${experimentId}/note`, { note });
    return data;
  },
  async lockExperiment(experimentId: string) {
    const { data } = await apiClient.post(`/experiments/${experimentId}/lock`);
    return data;
  },
  async unlockExperiment(experimentId: string) {
    const { data } = await apiClient.delete(`/experiments/${experimentId}/lock`);
    return data;
  },
  async scans(experimentId: string) {
    const { data } = await apiClient.get('/scans', {
      params: { experiment: experimentId },
    });
    const { results } = data;
    return results;
  },
  async scan(scanId: string) {
    const { data } = await apiClient.get(`/scans/${scanId}`);
    return data;
  },
  async setDecision(
    scanId: string,
    decision: string,
    comment: string,
    userIdentifiedArtifacts: Object,
    location: Object,
  ) {
    const { data } = await apiClient.post('/scan-decisions', {
      scan: scanId, decision, note: comment, artifacts: userIdentifiedArtifacts, location,
    });
    return data;
  },
  async frames(scanId: string) {
    const { data } = await apiClient.get('/frames', {
      params: { scan: scanId },
    });
    const { results } = data;
    return results;
  },
  async me(): Promise<User> {
    const resp = await apiClient.get('/users/me');
    return resp.status === 200 ? resp.data : null;
  },
  async allUsers(): Promise<Paginated<User>> {
    const resp = await apiClient.get('/users');
    return resp.status === 200 ? resp.data : null;
  },
  async sendEmail(email: string) {
    await apiClient.post('/email', email);
  },
};

export { apiClient };
export default djangoClient;
