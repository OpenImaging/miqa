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

const apiClient = axios.create({ baseURL: API_URL });
let s3ffClient;

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
        baseUrl: `${API_URL}/s3-upload/`,
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
      await store.commit.updateLastApiRequestTime();

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
      await oauthClient.logout();
      window.location.reload();
    }
  },
  async MIQAConfig() {
    const { data } = await apiClient.get('/configuration/');
    return data;
  },
  async globalSettings() {
    const { data } = await apiClient.get('/global/settings');
    return data;
  },
  async globalImport(): Promise<ResponseData> {
    return (await apiClient.post('/global/import')).data;
  },
  async projectImport(projectId: string): Promise<ResponseData> {
    return (await apiClient.post(`/projects/${projectId}/import`)).data;
  },
  async globalExport(): Promise<ResponseData> {
    return (await apiClient.post('/global/export')).data;
  },
  async projectExport(projectId: string): Promise<ResponseData> {
    return (await apiClient.post(`/projects/${projectId}/export`)).data;
  },
  async createProject(projectName: string): Promise<Project> {
    const { data } = await apiClient.post('/projects', { name: projectName });
    return data;
  },
  async deleteProject(projectId: string): Promise<ResponseData> {
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
  async setGlobalSettings(settings: ProjectSettings): Promise<ResponseData> {
    const resp = await apiClient.put('/global/settings', settings);
    return resp.status === 200 ? resp.data : null;
  },
  async setProjectSettings(projectId: string, settings: ProjectSettings): Promise<ResponseData> {
    const resp = await apiClient.put(`/projects/${projectId}/settings`, settings);
    return resp.status === 200 ? resp.data : null;
  },
  async experiments(projectId: string): Promise<Experiment[]> {
    const { data } = await apiClient.get('/experiments', {
      params: { project: projectId },
    });
    const { results } = data;
    return results;
  },
  async experiment(experimentId: string): Promise<Experiment> {
    const { data } = await apiClient.get(`/experiments/${experimentId}`);
    return data;
  },
  async createExperiment(projectId:string, experimentName: string): Promise<ResponseData> {
    const { data } = await apiClient.post('/experiments', {
      project: projectId,
      name: experimentName,
    });
    return data;
  },
  async uploadToExperiment(experimentId: string, files: File[]) {
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
    const { data } = await apiClient.post(`/experiments/${experimentId}/note`, { note });
    return data;
  },
  async lockExperiment(experimentId: string, force: boolean): Promise<ResponseData> {
    const { data } = await apiClient.post(`/experiments/${experimentId}/lock`, { force });
    return data;
  },
  async unlockExperiment(experimentId: string): Promise<ResponseData> {
    const { data } = await apiClient.delete(`/experiments/${experimentId}/lock`);
    return data;
  },
  async scans(experimentId: string): Promise<Scan[]> {
    const { data } = await apiClient.get('/scans', {
      params: { experiment: experimentId },
    });
    const { results } = data;
    return results;
  },
  async scan(scanId: string): Promise<Scan> {
    const { data } = await apiClient.get(`/scans/${scanId}`);
    return data;
  },
  async setDecision(
    scanId: string,
    decision: string,
    comment: string,
    userIdentifiedArtifacts: Object,
    location: Object,
  ): Promise<ResponseData> {
    const { data } = await apiClient.post('/scan-decisions', {
      scan: scanId, decision, note: comment, artifacts: userIdentifiedArtifacts, location,
    });
    return data;
  },
  async frames(scanId: string): Promise<Frame[]> {
    const { data } = await apiClient.get('/frames', {
      params: { scan: scanId },
    });
    const { results } = data;
    return results;
  },
  async frame(frameId: string): Promise<Frame> {
    const { data } = await apiClient.get(`/frames/${frameId}`);
    return data;
  },
  async me(): Promise<User> {
    const resp = await apiClient.get('/users/me');
    return resp.status === 200 ? resp.data : null;
  },
  async allUsers(): Promise<Paginated<User>> {
    const resp = await apiClient.get('/users');
    return resp.status === 200 ? resp.data : null;
  },
  async sendEmail(email: Email) {
    await apiClient.post('/email', email);
  },
};

apiClient.interceptors.response.use(null, (error) => {
  if (error?.response?.status === 401) {
    djangoClient.logout();
  }
  let msg = error?.response?.data?.detail || 'No response from server';
  if (error?.response?.status === 403) {
    msg = 'You are not allowed to perform this action.';
  }
  throw new Error(msg);
});

export { apiClient, oauthClient };
export default djangoClient;
