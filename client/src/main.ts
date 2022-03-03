import Vue from 'vue';
import VueCompositionAPI from '@vue/composition-api';
import Vuetify from 'vuetify';

import AsyncComputed from 'vue-async-computed';
import config from 'itk/itkConfig';
import IdleVue from 'idle-vue';
import * as Sentry from '@sentry/vue';
import App from './App.vue';
import router from './router';

import store from './store';
import { STATIC_PATH } from './constants';

import 'vuetify/dist/vuetify.min.css';
import '@mdi/font/css/materialdesignicons.min.css';

import './vtk/ColorMaps';
import vMousetrap from './vue-utilities/v-mousetrap';
import snackbarService from './vue-utilities/snackbar-service';
import promptService from './vue-utilities/prompt-service';

import djangoRest from './django';

Vue.use(Vuetify);

// import proxyConfigGenerator from './store/proxyConfigGenerator';

Vue.use(VueCompositionAPI);
Vue.use(AsyncComputed);
Vue.use(vMousetrap);
Vue.use(IdleVue, { store: store.original, idleTime: 900000 }); // 15 minutes inactive timeout

const vuetify = new Vuetify();

Vue.use(snackbarService(vuetify));
Vue.use(promptService(vuetify));

config.itkModulesPath = STATIC_PATH + config.itkModulesPath;

Vue.config.productionTip = true;

Sentry.init({
  Vue,
  dsn: process.env.VUE_APP_SENTRY_DSN,
});

djangoRest.restoreLogin(store).then(async () => {
  await Promise.all([store.dispatch.loadMe(), store.dispatch.loadConfiguration()]);
  const user = store.state.me;
  const { MIQAConfig } = store.state;
  new Vue({
    vuetify,
    router,
    store: store.original,
    provide: {
      user, MIQAConfig,
    },
    render: (h) => h(App),
  })
    .$mount('#app')
    // @ts-ignore
    .$snackbarAttach()
    .$promptAttach();
});
