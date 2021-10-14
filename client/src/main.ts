import Vue from 'vue';
import VueCompositionAPI from '@vue/composition-api';
import Vuetify from 'vuetify';

import AsyncComputed from 'vue-async-computed';
import Girder, { vuetifyConfig } from '@girder/components/src';
import config from 'itk/itkConfig';
import IdleVue from 'idle-vue';
import App from './App.vue';
import router from './router';

import store from './store';
import { STATIC_PATH } from './constants';

import 'vuetify/dist/vuetify.min.css';

import './vtk/ColorMaps';
import vMousetrap from './vue-utilities/v-mousetrap';
import snackbarService from './vue-utilities/snackbar-service';
import promptService from './vue-utilities/prompt-service';

import djangoRest from './django';

Vue.use(Vuetify);

// import proxyConfigGenerator from './store/proxyConfigGenerator';

Vue.use(VueCompositionAPI);
Vue.use(AsyncComputed);
Vue.use(Girder);
Vue.use(vMousetrap);
Vue.use(IdleVue, { store: store.original, idleTime: 900000 }); // 15 minutes inactive timeout

// Merge our own (currently empty) configuration with the one provided by
// Girder web components (needed for the login dialog to render properly)
const vuetifyOptions = { ...vuetifyConfig };
const vuetify = new Vuetify(vuetifyOptions);

Vue.use(snackbarService(vuetify));
Vue.use(promptService(vuetify));

config.itkModulesPath = STATIC_PATH + config.itkModulesPath;

Vue.config.productionTip = true;

djangoRest.restoreLogin(store).then(async () => {
  const user = await djangoRest.me();
  new Vue({
    vuetify,
    router,
    store: store.original,
    render: (h) => h(App),
    provide: {
      user,
    },
  })
    .$mount('#app')
    // @ts-ignore
    .$snackbarAttach()
    .$promptAttach();
});
