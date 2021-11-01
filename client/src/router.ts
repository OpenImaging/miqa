import Vue from 'vue';
import Router from 'vue-router';

import Projects from './views/Projects.vue';
import Dataset from './views/Dataset.vue';
import Login from './views/Login.vue';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
    },
    {
      path: '/',
      name: 'projects',
      component: Projects,
    },
    // Order matters
    {
      path: '/:datasetId?',
      name: 'dataset',
      component: Dataset,
    },
    {
      path: '*',
      redirect: '/',
    },
  ],
});
