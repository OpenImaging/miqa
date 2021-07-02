<script>
import { mapState, mapMutations } from 'vuex';

import { GIRDER_URL } from '../constants';

export default {
  name: 'NavigationTabs',
  data: () => ({
    GIRDER_URL,
  }),
  inject: ['user'],
  computed: {
    ...mapState(['currentDatasetId']),
  },
  methods: {
    ...mapMutations(['setDrawer']),
    datasetTabClick() {
      this.setDrawer(true);
    },
  },
};
</script>

<template>
  <v-tabs
    class="navigation-tabs ml-3"
    background-color="transparent"
  >
    <v-tab
      :to="`/${currentDatasetId ? currentDatasetId : ''}`"
      @click="datasetTabClick"
    >
      <v-icon>view_column</v-icon>
      Experiments
    </v-tab>
    <v-tab
      v-if="user.is_superuser"
      to="/settings"
    >
      <v-icon>settings</v-icon>
      Settings
    </v-tab>
  </v-tabs>
</template>

<style lang="scss">
.v-toolbar .navigation-tabs.v-tabs {
  width: unset;

  .v-tabs__container--icons-and-text .v-tabs__div {
    min-width: 120px;
  }
}
</style>
