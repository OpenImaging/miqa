import Vue from 'vue';
import Router from 'vue-router';

import Projects from './views/Projects.vue';
import Frame from './views/Frame.vue';

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
      path: '/:projectId?/:frameId?',
      name: 'frame',
      component: Frame,
    },
    {
      path: '*',
      redirect: '/',
    },
  ],
});
