import axios from 'axios';
import Vue from 'vue';
import OAuthClient from '@girder/oauth-client';
import { API_URL, OAUTH_API_ROOT, OAUTH_CLIENT_ID } from './constants';

const apiClient = axios.create({ baseURL: API_URL });
const oauthClient = new OAuthClient(OAUTH_API_ROOT, OAUTH_CLIENT_ID);
const djangoClient = new Vue({
  data: () => ({
    store: null,
    apiClient,
  }),
  methods: {
    async restoreLogin() {
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
        this.store.dispatch('resetActionTimer');

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
    async import(sessionId) {
      await apiClient.post(`/sessions/${sessionId}/import`);
    },
    async export(sessionId) {
      return apiClient.post(`/sessions/${sessionId}/export`);
    },
    async tasks() {
      const { data } = await apiClient.get('/tasks/me');
      return data;
    },
    async sessions() {
      const { data } = await apiClient.get('/sessions');
      const { results } = data;
      return results;
    },
    async session(sessionId) {
      const { data } = await apiClient.get(`/sessions/${sessionId}`);
      return data;
    },
    async settings(sessionId) {
      const { data } = await apiClient.get(`/sessions/${sessionId}/settings`);
      return data;
    },
    async setSettings(sessionId, settings) {
      await apiClient.put(`/sessions/${sessionId}/settings`, settings);
    },
    async sites() {
      const { data } = await apiClient.get('/sites');
      const { results } = data;
      return results;
    },
    async experiments(sessionId) {
      const { data } = await apiClient.get('/experiments', {
        params: { session: sessionId },
      });
      const { results } = data;
      return results;
    },
    async experiment(experimentId) {
      const { data } = await apiClient.get(`/experiments/${experimentId}/deep`);
      return data;
    },
    async lockExperiment(experimentId) {
      await apiClient.post(`/experiments/${experimentId}/lock`);
    },
    async unlockExperiment(experimentId) {
      await apiClient.delete(`/experiments/${experimentId}/lock`);
    },
    async scans(experimentId) {
      const { data } = await apiClient.get('/scans', {
        params: { experiment: experimentId },
      });
      const { results } = data;
      return results;
    },
    async scan(scanId) {
      const { data } = await apiClient.get(`/scans/${scanId}`);
      return data;
    },
    async setDecision(scanId, decision) {
      await apiClient.post('/annotations', { scan: scanId, decision });
    },
    async addScanNote(scanId, note) {
      await apiClient.post('/scan_notes', {
        scan: scanId,
        note,
      });
    },
    async setScanNote(scanNoteId, note) {
      await apiClient.put(`/scan_notes/${scanNoteId}`, { note });
    },
    async images(scanId) {
      const { data } = await apiClient.get('/images', {
        params: { scan: scanId },
      });
      const { results } = data;
      return results;
    },
    async me() {
      const resp = await apiClient.get('/users/me');
      return resp.status === 200 ? resp.data : null;
    },
    async sendEmail(email) {
      await apiClient.post('/email', email);
    },
  },
});

export default djangoClient;
