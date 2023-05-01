<script lang="ts">
import { defineComponent, computed, watch } from 'vue';
import store from '@/store';

export default defineComponent({
  name: 'App',
  setup() {
    const snackbarText = computed(() => store.state.snackbar);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);

    watch(snackbarText, () => {
      if (snackbarText.value) {
        setTimeout(() => {
          setSnackbar(null);
        }, 5000);
      }
    });
    return {
      snackbarText,
    };
  },
});
</script>

<template>
  <v-app id="app">
    <v-snackbar :value="snackbarText">
      {{ snackbarText }}
    </v-snackbar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<style lang="scss">
html {
  overflow-y: auto !important;
}
</style>
