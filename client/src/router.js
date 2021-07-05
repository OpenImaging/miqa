import Vue from 'vue';
import Router from 'vue-router';

import django from './django';
import Settings from './views/Settings.vue';
import Dataset from './views/Dataset.vue';
import Login from './views/Login.vue';

Vue.use(Router);

async function beforeEnterAdmin(to, from, next) {
  const user = await django.me();
  if (user && user.is_superuser) {
    // logged in && admin
    next();
  } else if (user) {
    // logged in, but not admin
    next('/');
  } else {
    // not logged in
    next(false);
  }
}

export default new Router({
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings,
      beforeEnter: beforeEnterAdmin,
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
