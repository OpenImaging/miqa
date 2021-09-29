<script lang="ts">
import { computed, defineComponent, inject } from '@vue/composition-api';
import store from '@/store';
import { GIRDER_URL } from '../constants';
import { User } from '@/types';

export default defineComponent({
  name: 'NavigationTabs',
  data: () => ({
    GIRDER_URL,
  }),
  setup() {
    const user = inject('user') as User;
    const currentDatasetId = computed(
      () => store.state.currentDatasetId,
    );
    const { setDrawer } = store.commit;

    return {
      user,
      currentDatasetId,
      setDrawer,
      datasetTabClick: () => setDrawer(true),
    };
  },

});
</script>

<template>
  <v-tabs
    class="navigation-tabs ml-3"
    background-color="transparent"
  >
    <v-tab
      :to="`/${currentDatasetId || ''}`"
      @click="datasetTabClick"
    >
      <v-icon>view_column</v-icon>
      Experiments
    </v-tab>
    <v-tab
      to="/projects"
    >
      <v-icon>view_column</v-icon>
      Projects
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
