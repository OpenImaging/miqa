import axios from 'axios';
import Vue from 'vue';
import OAuthClient from '@girder/oauth-client';
import { User } from './types';
import { API_URL, OAUTH_API_ROOT, OAUTH_CLIENT_ID } from './constants';

const apiClient = axios.create({ baseURL: API_URL });
const oauthClient = new OAuthClient(OAUTH_API_ROOT, OAUTH_CLIENT_ID);
const djangoClient = new Vue({
  data: () => ({
    apiClient,
  }),
  methods: {
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
    async import(sessionId: string) {
      await apiClient.post(`/sessions/${sessionId}/import`);
    },
    async export(sessionId: string) {
      return apiClient.post(`/sessions/${sessionId}/export`);
    },
    async sessions() {
      const { data } = await apiClient.get('/sessions');
      const { results } = data;
      return results;
    },
    async session(sessionId: string) {
      const { data } = await apiClient.get(`/sessions/${sessionId}`);
      return data;
    },
    async settings(sessionId: string) {
      const { data } = await apiClient.get(`/sessions/${sessionId}/settings`);
      return data;
    },
    async setSettings(sessionId: string, settings: Object) {
      await apiClient.put(`/sessions/${sessionId}/settings`, settings);
    },
    async sites() {
      const { data } = await apiClient.get('/sites');
      const { results } = data;
      return results;
    },
    async experiments(sessionId: string) {
      const { data } = await apiClient.get('/experiments', {
        params: { session: sessionId },
      });
      const { results } = data;
      return results;
    },
    async experiment(experimentId: string) {
      const { data } = await apiClient.get(`/experiments/${experimentId}`);
      return data;
    },
    async lockExperiment(experimentId: string) {
      await apiClient.post(`/experiments/${experimentId}/lock`);
    },
    async unlockExperiment(experimentId: string) {
      await apiClient.delete(`/experiments/${experimentId}/lock`);
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
    async setDecision(scanId: string, decision: string) {
      await apiClient.post('/annotations', { scan: scanId, decision });
    },
    async addScanNote(scanId: string, note: string) {
      await apiClient.post('/scan_notes', {
        scan: scanId,
        note,
      });
    },
    async setScanNote(scanNoteId: string, note: string) {
      await apiClient.put(`/scan_notes/${scanNoteId}`, { note });
    },
    async images(scanId: string) {
      const { data } = await apiClient.get('/images', {
        params: { scan: scanId },
      });
      const { results } = data;
      return results;
    },
    async me(): Promise<User> {
      const resp = await apiClient.get('/users/me');
      return resp.status === 200 ? resp.data : null;
    },
    async sendEmail(email: string) {
      await apiClient.post('/email', email);
    },
  },
});

export default djangoClient;
