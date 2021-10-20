<script>
import _ from 'lodash';

import {
  NavigationFailureType,
  isNavigationFailure,
} from 'vue-router/src/util/errors';

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
import DataImportExport from '../components/DataImportExport.vue';
import djangoRest from '@/django';

export default {
  name: 'Dataset',
  components: {
    NavbarTitle,
    UserButton,
    Layout,
    DataImportExport,
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
    newNote: '',
    decision: null,
    decisionChanged: false,
    unsavedDialog: false,
    unsavedDialogResolve: null,
    emailDialog: false,
    showNotePopup: false,
    keyboardShortcutDialog: false,
    scanning: false,
    advanceTimeoutId: null,
    nextAnimRequest: null,
  }),
  computed: {
    ...mapState([
      'currentDatasetId',
      'vtkViews',
      'loadingDataset',
      'errorLoadingDataset',
      'drawer',
      'screenshots',
      'scanCachedPercentage',
      'scanDatasets',
    ]),
    ...mapGetters([
      'nextDataset',
      'getDataset',
      'currentDataset',
      'currentExperiment',
      'currentScan',
      'previousDataset',
      'firstDatasetInPreviousScan',
      'firstDatasetInNextScan',
      'getSiteDisplayName',
      'getExperimentDisplayName',
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
    lastNoteTruncated() {
      if (this.notes.length > 0) {
        const lastNote = this.notes.slice(-1)[0];
        return `${lastNote.note.substring(0, 32)}...`;
      }
      return '';
    },
    lockOwned() {
      const { lockOwner } = this.currentExperiment;
      return !!lockOwner && lockOwner.username === this.user.username;
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
    const result = await this.beforeLeaveScan(toDataset);
    next(result);
    if (result && toDataset) {
      this.swapToDataset(toDataset);
    }
  },
  async beforeRouteLeave(to, from, next) {
    const result = await this.beforeLeaveScan();
    next(result);
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
    handleNavigationError(fail) {
      let failureType = 'unknown';
      if (isNavigationFailure(fail, NavigationFailureType.redirected)) {
        failureType = 'redirected';
      } else if (isNavigationFailure(fail, NavigationFailureType.aborted)) {
        failureType = 'aborted';
      } else if (isNavigationFailure(fail, NavigationFailureType.cancelled)) {
        failureType = 'cancelled';
      } else if (isNavigationFailure(fail, NavigationFailureType.duplicated)) {
        failureType = 'duplicated';
      }
      this.scanning = false;
      console.log(`Caught navigation error (${failureType})`);
    },
    beforeLeaveScan(toDataset) {
      if (
        this.currentDataset
        && toDataset
        && (this.decisionChanged || this.newNote)
      ) {
        this.unsavedDialog = true;
        return new Promise((resolve) => {
          this.unsavedDialogResolve = resolve;
        });
      }
      return Promise.resolve(true);
    },
    async save() {
      if (this.newNote && this.newNote.trim()) {
        await djangoRest.addScanNote(this.currentScan.id, this.newNote);
        this.newNote = '';
      }
      if (this.decisionChanged) {
        await djangoRest.setDecision(
          this.currentScan.id,
          this.decision,
        );
        this.decisionChanged = false;
      }
      this.reloadScan();
    },
    async unsavedDialogYes() {
      await this.save();
      this.unsavedDialogResolve(true);
      this.unsavedDialog = false;
    },
    unsavedDialogNo() {
      this.unsavedDialogResolve(true);
      this.unsavedDialog = false;
    },
    unsavedDialogCancel() {
      this.unsavedDialogResolve(false);
      this.unsavedDialog = false;
    },
    setDecision(decision) {
      if (decision !== this.decision) {
        this.decision = decision;
        this.onDecisionChanged();
      }
    },
    creatorName(note) {
      if (note.creator) {
        return `${note.creator.first_name} ${note.creator.last_name}`;
      }
      return note.initials;
    },
    setNote(e) {
      this.newNote = e;
    },
    async onDecisionChanged() {
      const last = _.head(this.currentScan.decisions);
      const lastDecision = last ? last.decision : null;
      if (this.decision && this.decision !== lastDecision) {
        this.decisionChanged = true;
        await this.save();

        if (this.firstDatasetInNextScan) {
          const { currentDatasetId } = this;

          this.$router
            .push(this.firstDatasetInNextScan)
            .catch(this.handleNavigationError);

          this.$snackbar({
            text: 'Proceeded to next scan',
            button: 'Go back',
            timeout: 6000,
            immediate: true,
            callback: () => {
              this.$router
                .push(currentDatasetId)
                .catch(this.handleNavigationError);
            },
          });
        }
      }
    },
    focusNote(el, e) {
      this.$refs.note.focus();
      e.preventDefault();
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
      :value="drawer"
      @input="setDrawer($event)"
      app
      temporary
      width="350"
    >
      <div class="scans-bar">
        <v-toolbar
          dense
          flat
          max-height="48px"
        >
          <v-toolbar-title>Experiments</v-toolbar-title>
        </v-toolbar>
        <DataImportExport />
        <ExperimentsView
          class="mt-1"
          minimal
        />
      </div>
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
    <v-dialog
      v-model="unsavedDialog"
      persistent
      max-width="400"
    >
      <v-card>
        <v-card-title class="title">
          Review is not saved
        </v-card-title>
        <v-card-text>Do you want save before continue?</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            v-mousetrap="{ bind: 'y', handler: el => el.focus() }"
            @click="unsavedDialogYes"
            text
            color="primary"
          >
            Yes
          </v-btn>
          <v-btn
            v-mousetrap="{ bind: 'n', handler: el => el.focus() }"
            @click="unsavedDialogNo"
            text
            color="primary"
          >
            no
          </v-btn>
          <v-btn
            v-mousetrap="{ bind: 'esc', handler: unsavedDialogCancel }"
            @click="unsavedDialogCancel"
            text
          >
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
