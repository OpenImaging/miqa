import Vue from 'vue';
import Router from 'vue-router';

import Projects from './views/Projects.vue';
import Scan from './views/Scan.vue';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/',
      name: 'projects',
      component: Projects,
    },
    // Order matters
    {
      path: '/:projectId?/complete',
      name: 'projectComplete',
      component: Projects,
    },
    {
      path: '/:projectId?/:scanId?',
      name: 'scan',
      component: Scan,
    },
    {
      path: '*',
      redirect: '/',
    },
  ],
});
