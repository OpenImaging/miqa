<script>
export default {
  name: 'App',
  components: {},
};
</script>

<template>
  <v-app id="app">
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
