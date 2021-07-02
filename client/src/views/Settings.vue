<script>
// import { mapState, mapActions } from "vuex";

import GenericNavigationBar from '@/components/GenericNavigationBar.vue';
import JSONConfig from '@/components/JSONConfig.vue';
import SiteConfig from '@/components/SiteConfig.vue';

export default {
  name: 'Settings',
  components: {
    GenericNavigationBar,
    JSONConfig,
    SiteConfig,
  },
};
</script>

<template>
  <div class="sites">
    <GenericNavigationBar />
    <v-container grid-list-md>
      <div class="subheading">
        JSON path
      </div>
      <v-layout>
        <v-flex>
          <JSONConfig />
        </v-flex>
      </v-layout>
      <div class="subheading mt-4">
        Sites
      </div>
      <v-layout justify-center>
        <v-flex>
          <SiteConfig />
        </v-flex>
      </v-layout>
    </v-container>
  </div>
</template>

<style lang="scss" scoped></style>
