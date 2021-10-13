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
import ProjectsView from '@/components/ProjectsView.vue';
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
    ProjectsView,
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
      'scanDatasets',
    ]),
    ...mapGetters([
      'nextDataset',
      'getDataset',
      'previousDataset',
      'currentDataset',
    ]),
    currentscanDatasets() {
      return this.scanDatasets[this.currentProject.id];
    },
    notes() {
      if (this.currentProject) {
        return this.currentProject.notes;
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
    currentProject(project) {
      if (project) {
        const last = _.head(project.decisions);
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
    const result = await this.beforeLeaveProject(toDataset);
    next(result);
    if (result && toDataset) {
      this.swapToDataset(toDataset);
    }
  },
  async beforeRouteLeave(to, from, next) {
    const result = await this.beforeLeaveProject();
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
    beforeLeaveProject(toDataset) {
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
        await djangoRest.addScanNote(this.currentProject.id, this.newNote);
        this.newNote = '';
      }
      if (this.decisionChanged) {
        await djangoRest.setDecision(
          this.currentProject.id,
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
      const last = _.head(this.currentProject.decisions);
      const lastDecision = last ? last.decision : null;
      if (this.decision && this.decision !== lastDecision) {
        this.decisionChanged = true;
        await this.save();

        if (this.firstDatasetInNextProject) {
          const { currentDatasetId } = this;

          this.$router
            .push(this.firstDatasetInNextProject)
            .catch(this.handleNavigationError);

          this.$snackbar({
            text: 'Proceeded to next project',
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
      const datasetId = this.currentscanDatasets[index];
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
      <div class="projects-bar">
        <v-toolbar
          dense
          flat
          max-height="48px"
        >
          <v-toolbar-title>Experiments</v-toolbar-title>
        </v-toolbar>
        <DataImportExport />
        <ProjectsView
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

      <!-- </v-layout>
              <v-layout
                align-center
                class="bottom-row ml-3 mr-1"
              >
                <v-row justify="center">
                  <div class="load-completion">
                    {{ Math.round(projectCachedPercentage * 100) }}%
                  </div>
                </v-row>
              </v-layout>
            </v-flex>
            <v-flex
              xs4
              class="mx-2"
            >
              <v-container class="pa-0">
                <v-row>
                  <v-col
                    cols="12"
                    class="pb-1 pt-0"
                  >
                    <v-container class="pa-0">
                      <v-row>
                        <v-col
                          cols="3"
                          class="pb-1 pt-0"
                        >
                          Site
                        </v-col>
                        <v-col
                          cols="9"
                          class="pb-1 pt-0 justifyRight"
                        >
                          {{ getSiteDisplayName(currentProject.site) }}
                        </v-col>
                      </v-row>
                      <v-row>
                        <v-col
                          cols="3"
                          class="pb-1 pt-0"
                        >
                          Experiment
                        </v-col>
                        <v-col
                          cols="9"
                          class="pb-1 pt-0 justifyRight"
                        >
                          <a
                            :href="'/xnat/app/action/DisplayItemAction/search_value' +
                              `/${currentProject.experiment}/search_element/xnat:mrProjectData` +
                              '/search_field/xnat:mrProjectData.ID'"
                            target="_blank"
                          >
                            {{
                              getExperimentDisplayName(
                                currentProject.experiment
                              )
                            }}
                          </a>
                        </v-col>
                      </v-row>
                      <v-row>
                        <v-col
                          cols="3"
                          class="pb-1 pt-0"
                        >
                          Scan
                        </v-col>
                        <v-col
                          cols="9"
                          class="pb-1 pt-0 justifyRight"
                        >
                          {{ currentProject.name }}
                        </v-col>
                      </v-row>
                    </v-container>
                  </v-col>
                </v-row>
                <template v-if="!currentDataset.local">
                  <v-row>
                    <v-col
                      class="pb-1 pt-0"
                      cols="10"
                    >
                      Note history: {{ lastNoteTruncated }}
                    </v-col>
                    <v-col
                      class="pb-1 pt-0"
                      cols="1"
                    >
                      <v-menu
                        ref="historyMenu"
                        v-model="showNotePopup"
                        :close-on-content-click="false"
                        offset-y
                        open-on-hover
                        top
                        left
                      >
                        <template v-slot:activator="{ on }">
                          <v-btn
                            v-mousetrap="{
                              bind: 'h',
                              handler: () => (showNotePopup = !showNotePopup)
                            }"
                            :disabled="notes.length < 1"
                            v-on="on"
                            text
                            small
                            icon
                            class="ma-0"
                          >
                            <v-icon>arrow_drop_up</v-icon>
                          </v-btn>
                        </template>
                        <v-card>
                          <v-list-item
                            v-for="note in notes"
                            :key="note.id"
                          >
                            <v-list-item-content class="note-history">
                              <v-list-item-title class="grey--text darken-2">
                                {{ creatorName(note) }}: {{ note.created }}
                              </v-list-item-title>
                              {{ note.note }}
                            </v-list-item-content>
                          </v-list-item>
                        </v-card>
                      </v-menu>
                    </v-col>
                  </v-row>
                  <v-row
                    class="pb-1 pt-1"
                  >
                    <v-col
                      cols="11"
                      class="pb-1 pt-0 pr-0"
                    >
                      <v-text-field
                        ref="note"
                        v-mousetrap="{ bind: 'n', handler: focusNote }"
                        v-mousetrap.element="{
                          bind: 'esc',
                          handler: () => $refs.note.blur()
                        }"
                        :value="newNote"
                        :disabled="!lockOwned"
                        @input="setNote($event)"
                        class="note-field"
                        label="Note"
                        solo
                        hide-details
                      />
                    </v-col>
                    <v-col
                      cols="1"
                      class="pb-1 pt-0"
                    >
                      <v-tooltip top>
                        <template v-slot:activator="{ on }">
                          <v-btn
                            :disabled="!decisionChanged"
                            v-on="on"
                            @click="reloadScan"
                            text
                            icon
                            small
                            color="grey"
                            class="my-0"
                          >
                            <v-icon>undo</v-icon>
                          </v-btn>
                        </template>
                        <span>Revert</span>
                      </v-tooltip>
                    </v-col>
                  </v-row>
                  <v-row
                    no-gutters
                    justify="space-between"
                    class="pb-1"
                  >
                    <v-col
                      cols="6"
                      class="pb-1 pt-0"
                    >
                      <v-btn-toggle
                        v-model="decision"
                        @change="onDecisionChanged"
                        class="buttons"
                      >
                        <v-btn
                          v-mousetrap="{
                            bind: 'b',
                            handler: () => setDecision('BAD')
                          }"
                          :disabled="(!lockOwned) || (!newNote && notes.length === 0)"
                          text
                          small
                          value="BAD"
                          color="red"
                        >
                          Bad
                        </v-btn>
                        <v-btn
                          v-mousetrap="{
                            bind: 'g',
                            handler: () => setDecision('GOOD')
                          }"
                          :disabled="!lockOwned"
                          text
                          small
                          value="GOOD"
                          color="green"
                        >
                          Good
                        </v-btn>
                        <v-btn
                          v-mousetrap="{
                            bind: 'u',
                            handler: () => setDecision('USABLE_EXTRA')
                          }"
                          :disabled="!lockOwned"
                          text
                          small
                          value="USABLE_EXTRA"
                          color="light-green"
                        >
                          Extra
                        </v-btn>
                      </v-btn-toggle>
                    </v-col>
                    <v-col
                      cols="1"
                      class="pb-1 pt-0"
                    >
                      <ExperimentLockIcon :experiment="currentExperiment" />
                    </v-col>
                    <v-col
                      cols="2"
                      class="pb-1 pt-0"
                    >
                      <v-btn
                        v-mousetrap="{ bind: 'alt+s', handler: save }"
                        :disabled="(!lockOwned) || (!decisionChanged && !newNote)"
                        @click="save"
                        color="primary"
                        class="ma-0"
                        style="height: 36px"
                        small
                      >
                        Save
                        <v-icon right>
                          save
                        </v-icon>
                      </v-btn>
                    </v-col>
                  </v-row>
                </template>
              </v-container>
            </v-flex>
            <v-flex
              xs4
              class="mx-2"
            >
              <WindowControl
                v-if="vtkViews.length"
                class="py-0"
              />
            </v-flex> -->
      <!-- </v-layout> -->
    </template>
    <v-layout
      v-if="!currentDataset && !loadingDataset"
      align-center
      justify-center
      fill-height
    >
      <div class="title">
        Select a project
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
  .projects-bar {
    display: flex;
    flex-direction: column;
    height: 100%;

    .projects-view {
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

// .panel-label {
//   background-color: #e6e6e6;
//   color: #575757;
//   font-size: 12px;
//   padding: 5px 10px!important;
// }

// tbody {
//     tr:hover {
//       background-color: transparent !important;
//     }
// }
</style>
