<script>
import _ from 'lodash';
import {
  mapState, mapActions, mapGetters, mapMutations,
} from 'vuex';

import Layout from '@/components/Layout.vue';
import NavbarTitle from '@/components/NavbarTitle.vue';
import ControlPanel from '@/components/ControlPanel.vue';
import UserButton from '@/components/girder/UserButton.vue';
import ExperimentsView from '@/components/ExperimentsView.vue';
import ScreenshotDialog from '@/components/ScreenshotDialog.vue';
import EmailDialog from '@/components/EmailDialog.vue';
import TimeoutDialog from '@/components/TimeoutDialog.vue';
import KeyboardShortcutDialog from '@/components/KeyboardShortcutDialog.vue';
import NavigationTabs from '@/components/NavigationTabs.vue';
import { cleanDatasetName } from '@/utils/helper';

export default {
  name: 'Dataset',
  components: {
    NavbarTitle,
    UserButton,
    Layout,
    ExperimentsView,
    ScreenshotDialog,
    EmailDialog,
    TimeoutDialog,
    KeyboardShortcutDialog,
    NavigationTabs,
    ControlPanel,
  },
  inject: ['user'],
  data: () => ({
    emailDialog: false,
    keyboardShortcutDialog: false,
    advanceTimeoutId: null,
  }),
  computed: {
    ...mapState([
      'vtkViews',
      'drawer',
      'screenshots',
      'scanCachedPercentage',
      'scanDatasets',
      'loadingDataset',
      'errorLoadingDataset',
    ]),
    ...mapGetters([
      'getDataset',
      'currentDataset',
    ]),
    currentScanDatasets() {
      return this.scanDatasets[this.currentScan.id];
    },
    notes() {
      if (this.currentScan) {
        return this.currentScan.notes;
      }
      return [];
    },
  },
  watch: {
    currentScan(scan) {
      if (scan) {
        const last = _.head(scan.decisions);
        this.decision = last ? last.decision : null;
        this.decisionChanged = false;
        this.newNote = '';
      }
    },
  },
  async created() {
    this.debouncedDatasetSliderChange = _.debounce(
      this.debouncedDatasetSliderChange,
      30,
    );
    await this.loadSites();
    const { datasetId } = this.$route.params;
    const dataset = this.getDataset(datasetId);
    if (dataset) {
      await this.swapToDataset(dataset);
    } else {
      this.$router.replace('/').catch(this.handleNavigationError);
      this.setDrawer(true);
    }
  },
  async beforeRouteUpdate(to, from, next) {
    const toDataset = this.getDataset(to.params.datasetId);
    next(true);
    if (toDataset) {
      this.swapToDataset(toDataset);
    }
  },
  async beforeRouteLeave(to, from, next) {
    next(true);
  },
  methods: {
    ...mapMutations(['setDrawer']),
    ...mapActions([
      'loadProject',
      'reloadScan',
      'loadSites',
      'logout',
      'swapToDataset',
    ]),
    cleanDatasetName,
    async logoutUser() {
      await this.logout();
      this.$router.go('/'); // trigger re-render into oauth flow
    },
    debouncedDatasetSliderChange(index) {
      const datasetId = this.currentScanDatasets[index];
      this.$router.push(datasetId).catch(this.handleNavigationError);
    },
    advanceLoop() {
      if (this.scanning) {
        this.updateImage();
        this.nextAnimRequest = window.requestAnimationFrame(this.advanceLoop);
      }
    },
  },
};
</script>

<template>
  <v-layout
    class="dataset"
    fill-height
    column
  >
    <v-app-bar
      app
      dense
    >
      <NavbarTitle />
      <NavigationTabs />
      <v-spacer />
      <v-btn
        @click="keyboardShortcutDialog = true"
        icon
        class="mr-4"
      >
        <v-icon>keyboard</v-icon>
      </v-btn>
      <v-btn
        :disabled="!currentDataset"
        @click="emailDialog = true"
        icon
        class="mr-4"
      >
        <v-badge
          :value="screenshots.length"
          right
        >
          <span
            slot="badge"
            dark
          >{{ screenshots.length }}</span>
          <v-icon>email</v-icon>
        </v-badge>
      </v-btn>
      <UserButton
        @user="logoutUser()"
        @login="djangoRest.login()"
      />
    </v-app-bar>
    <v-navigation-drawer
      expand-on-hover
      app
      width="350"
    >
      <v-list>
        <v-list-item>
          <v-icon>fas fa-list</v-icon>
          <v-toolbar-title class="pl-5">
            Experiments
          </v-toolbar-title>
        </v-list-item>
        <v-list-item>
          <v-icon />
          <ExperimentsView
            class="mt-1"
            minimal
          />
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-layout
      v-if="loadingDataset"
      class="loading-indicator-container"
      align-center
      justify-center
      row
      fill-height
    >
      <v-progress-circular
        :width="4"
        :size="50"
        color="primary"
        indeterminate
      />
    </v-layout>
    <template v-if="currentDataset">
      <v-flex class="layout-container">
        <Layout />
        <v-layout
          v-if="errorLoadingDataset"
          align-center
          justify-center
          fill-height
        >
          <div class="title">
            Error loading this dataset
          </div>
        </v-layout>
      </v-flex>
      <ControlPanel />
    </template>
    <v-layout
      v-if="!currentDataset && !loadingDataset"
      align-center
      justify-center
      fill-height
    >
      <div class="title">
        Select a scan
      </div>
    </v-layout>
    <ScreenshotDialog />
    <EmailDialog
      v-model="emailDialog"
      :notes="notes"
    />
    <TimeoutDialog />
    <KeyboardShortcutDialog v-model="keyboardShortcutDialog" />
  </v-layout>
</template>

<style lang="scss" scoped>
.dataset {
  .scans-bar {
    display: flex;
    flex-direction: column;
    height: 100%;

    .scans-view {
      overflow: auto;
    }
  }

  .experiment-note {
    max-width: 250px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .loading-indicator-container {
    background: #ffffff57;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1;
  }

  .layout-container {
    position: relative;
  }

  .v-btn.smaller {
    height: 35px;
    width: 35px;
  }

  .bottom {
    > .container {
      position: relative;
    }

    .buttons {
      width: 100%;

      .v-btn {
        height: 36px;
        opacity: 1;
        flex: 1;
      }
    }
  }
}

.theme--light.v-btn.v-btn--disabled:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.theme--light.v-btn:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.v-btn::before {
  background-color: transparent !important;
}

</style>

<style lang="scss">
.load-completion {
  font-size: 1.1em;
  /*font-weight: bold;*/
}

.justifyRight {
  text-align: right;
}

.dataset {
  .v-text-field.small .v-input__control {
    min-height: 36px !important;
  }

  .note-field .v-input__control {
    min-height: 36px !important;
  }

  .v-input--slider.dataset-slider {
    margin-top: 0;
  }
}

.v-list-item__content.note-history {
  width: 500px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
