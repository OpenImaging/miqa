import Vue from 'vue';
import Router from 'vue-router';

import Projects from './views/Projects.vue';
import Frame from './views/Frame.vue';
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
      path: '/:frameId?',
      name: 'frame',
      component: Frame,
    },
    {
      path: '*',
      redirect: '/',
    },
  ],
});
