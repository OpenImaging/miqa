import axios from 'axios';
import OAuthClient from '@girder/oauth-client';
import { Project, ProjectTaskOverview, Settings, User } from './types';
import { API_URL, OAUTH_API_ROOT, OAUTH_CLIENT_ID } from './constants';

interface Paginated<T> {
  count: number,
  next: string,
  previous: string,
  results: T[],
}

const apiClient = axios.create({ baseURL: API_URL });
apiClient.interceptors.response.use(null, (error) => {
  throw new Error(error.response.data.detail);
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
  async import(projectId: string) {
    await apiClient.post(`/projects/${projectId}/import`);
  },
  async export(projectId: string) {
    return apiClient.post(`/projects/${projectId}/export`);
  },
  async createProject(projectName: string): Promise<Project>{
    const { data } = await apiClient.post('/projects', {name: projectName});
    return data;
  },
  async deleteProject(projectId: string){
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
  async settings(projectId: string): Promise<Settings> {
    const { data } = await apiClient.get(`/projects/${projectId}/settings`);
    return data;
  },
  async setSettings(projectId: string, settings: Settings) {
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
  ) {
    const { data } = await apiClient.post('/scan-decisions', {
      scan: scanId, decision, note: comment, artifacts: userIdentifiedArtifacts,
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
