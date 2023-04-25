import Vue from 'vue';
import Vuetify from 'vuetify';
import 'polyfill-object.fromentries';

import AsyncComputed from 'vue-async-computed';
import config from 'itk/itkConfig';
import * as Sentry from '@sentry/vue';
import App from './App.vue';
import router from './router';

import store from './store';
import { STATIC_PATH } from './constants';

import vMousetrap from './vue-utilities/v-mousetrap';
import snackbarService from './vue-utilities/snackbar-service';
import promptService from './vue-utilities/prompt-service';

import djangoRest, { oauthClient } from './django';
import { setupHeartbeat } from './heartbeat';

Vue.use(Vuetify);

Vue.use(AsyncComputed);
Vue.use(vMousetrap);

const vuetify = new Vuetify();

Vue.use(snackbarService(vuetify));
Vue.use(promptService(vuetify));

config.itkModulesPath = STATIC_PATH + config.itkModulesPath;

Vue.config.productionTip = true;

Sentry.init({
  Vue,
  dsn: process.env.VUE_APP_SENTRY_DSN,
});

(async () => {
  // If user closes the tab, we want them to be logged out if they return to the page
  await setupHeartbeat('miqa_logout_heartbeat', async () => { oauthClient.logout(); });
  await djangoRest.restoreLogin(store);
  await Promise.all([
    store.dispatch('reset'),
    store.dispatch('loadMe'),
    store.dispatch('loadConfiguration'),
  ]);

  new Vue({
    vuetify,
    router,
    store,
    provide: {
      user: store.state.me,
      MIQAConfig: store.state.MIQAConfig,
    },
    mounted() {
      this.$snackbarAttach();
      this.$promptAttach();
    },
    render: (h) => h(App),

  })
    .$mount('#app');
})();
