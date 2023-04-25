<script lang="ts">
import _ from 'lodash';
import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import UserAvatar from '@/components/UserAvatar.vue';
import djangoRest from '@/django';
import { includeScan } from '@/store';
import { API_URL, decisionOptions } from '@/constants';

export default {
  name: 'ExperimentsView',
  components: { UserAvatar },
  inject: ['user', 'MIQAConfig'],
  props: {
    minimal: {
      type: Boolean,
      default: false,
    },
  },
  data: () => ({
    API_URL,
    showUploadModal: false,
    showDeleteModal: false,
    uploadToExisting: false,
    uploadError: '',
    experimentNameForUpload: '',
    fileSetForUpload: [],
    uploading: false,
    decisionOptions,
  }),
  computed: {
    ...mapState([
      'reviewMode',
      'experiments',
      'experimentIds',
      'experimentScans',
      'loadingExperiment',
      'scans',
      'scanFrames',
      'frames',
      'currentTaskOverview',
      'currentProject',
    ]),
    ...mapGetters([
      'currentScan',
      'currentExperiment',
    ]),
    // Gets the experiments based on the experiment ids
    orderedExperiments() {
      return this.experimentIds.map((expId) => this.experiments[expId]);
    },
    loadingIcon() {
      return this.loadingExperiment
        ? 'mdi-progress-clock'
        : 'mdi-check-circle-outline';
    },
    loadingIconColor() {
      return this.loadingExperiment ? 'red' : 'green';
    },
  },
  watch: {
    /** Begins loading upload modal */
    showUploadModal() {
      this.delayPrepareDropZone();
    },
    /** When the project changes, reset the local state for the project. */
    currentProject() {
      this.showUploadModal = false;
      this.uploadToExisting = false;
      this.uploadError = '';
      this.fileSetForUpload = [];
      this.uploading = false;
    },
  },
  methods: {
    ...mapMutations([
      'SET_REVIEW_MODE',
    ]),
    ...mapActions([
      'loadProject',
    ]),
    includeScan,
    /** Gets all scans associated with the provided experimentId */
    scansForExperiment(expId) {
      const expScanIds = this.experimentScans[expId];
      return expScanIds.filter(
        (scanId) => Object.keys(this.scans).includes(scanId),
      ).map((scanId) => {
        const scan = this.scans[scanId];
        return {
          ...scan,
          ...this.decisionToRating(scan.decisions),
        };
      });
    },
    /** Receives a string like "NCANDA_E08710" (name of an image file),
     * this is used as the experiment name */
    ellipsisText(str) {
      if (!this.minimal) return str;
      if (str.length > 25) {
        return `${str.substr(0, 10)}...${
          str.substr(str.length - 10, str.length)}`;
      }
      return str;
    },
    /** Get the URL of the first frame in the current scan */
    getURLForScan(scanId) {
      return `/${this.currentProject.id}/${scanId}`;
    },
    /** Assigns a color and character if a decision has been rendered on a given scan */
    decisionToRating(decisions) {
      // decisions are an array of objects
      if (decisions.length === 0) return {};
      const rating = _.first(_.sortBy(decisions, (decision) => decision.created)).decision;
      let color = 'grey--text';
      if (rating === 'U') {
        color = 'green--text';
      }
      if (rating === 'UN') {
        color = 'red--text';
      }
      return {
        decision: rating,
        color,
      };
    },
    scanIsCurrent(scan) {
      if (scan === this.currentScan) {
        return ' current';
      }
      return '';
    },
    scanState(scan) {
      let scanTaskState;
      if (this.currentTaskOverview) {
        scanTaskState = this.currentTaskOverview.scan_states[scan.id];
      }
      return scanTaskState || 'unreviewed';
    },
    /** Adds a class to a scan representative of the scan's task state. */
    scanStateClass(scan) {
      let classes = `body-1 state-${this.scanState(scan).replace(/ /g, '-')}`;
      if (scan === this.currentScan) {
        classes = `${classes} current`;
      }
      return classes;
    },
    delayPrepareDropZone() {
      setTimeout(this.prepareDropZone, 500);
    },
    /** Listens for images being dragged into the dropzone */
    prepareDropZone() {
      const dropZone = document.getElementById('dropZone');
      if (dropZone) {
        dropZone.addEventListener('dragenter', (e) => {
          e.preventDefault();
          dropZone.classList.add('hover');
        });
        dropZone.addEventListener('dragleave', (e) => {
          e.preventDefault();
          dropZone.classList.remove('hover');
        });
      }
    },
    /** Gets files dropped into the dropzone */
    addDropFiles(e) {
      this.fileSetForUpload = [...e.dataTransfer.files];
    },
    async uploadToExperiment() {
      let experimentId;
      this.uploading = true;
      try {
        // If we are uploading to a new experiment
        if (!this.uploadToExisting) {
          // Create a new experiment, below returns instance of ResponseData
          const newExperiment = await djangoRest.createExperiment(
            this.currentProject.id,
            this.experimentNameForUpload,
          );
          experimentId = newExperiment.id;
        } else {
          // Find the experiment's id that matches the experiment selected
          experimentId = (Object.values(this.experiments).find(
            (experiment: any) => experiment.name === this.experimentNameForUpload,
          ) as { id: string, name: string }).id;
        }
        await djangoRest.uploadToExperiment(experimentId, this.fileSetForUpload);
        await this.loadProject(this.currentProject);
        this.showUploadModal = false;
      } catch (ex) {
        const text = ex || 'Upload failed due to server error.';
        this.uploadError = text;
      }
      this.uploading = false;
    },
    deleteExperiment(experimentId) {
      djangoRest.deleteExperiment(experimentId).then(
        () => {
          this.loadProject(this.currentProject);
          this.showDeleteModal = false;
        },
      );
    },
  },
};
</script>

<template>
  <v-card
    v-if="currentProject"
    class="flex-card"
  >
    <div
      v-if="currentProject"
      class="d-flex"
      style="justify-content: space-between; align-items: baseline"
    >
      <v-subheader
        v-if="!minimal"
        style="display: inline"
      >
        Experiments
      </v-subheader>
      <v-subheader
        class="mode-toggle"
      >
        <span>All scans</span>
        <v-switch
          :input-value="reviewMode"
          dense
          style="display: inline-block; max-height: 40px; max-width: 60px;"
          class="px-3 ma-0"
          @change="SET_REVIEW_MODE"
        />
        <span>Scans for my review</span>
      </v-subheader>
    </div>
    <div class="scans-view">
      <div v-if="orderedExperiments && orderedExperiments.length">
        <ul class="experiment">
          <li
            v-for="experiment of orderedExperiments"
            :key="`e.${experiment.id}`"
            class="body-2 pb-5"
          >
            <v-card
              flat
              class="d-flex pr-2"
            >
              <v-card flat>
                {{ ellipsisText(experiment.name) }}
                <UserAvatar
                  v-if="experiment.lock_owner"
                  :target-user="experiment.lock_owner"
                  as-editor
                />
                <v-dialog
                  v-else-if="!minimal"
                  :value="showDeleteModal === experiment.id"
                  width="600px"
                >
                  <template #activator="{ attrs }">
                    <div
                      v-bind="attrs"
                      style="display: inline"
                      @click="showDeleteModal = experiment.id"
                      @keydown="showDeleteModal = experiment.id"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </div>
                  </template>

                  <v-card>
                    <v-btn
                      icon
                      style="float:right"
                      @click="showDeleteModal = false"
                    >
                      <v-icon>mdi-close</v-icon>
                    </v-btn>
                    <v-card-title class="text-h6">
                      Confirmation
                    </v-card-title>
                    <v-card-text>
                      Are you sure you want to delete experiment {{ experiment.name }}?
                    </v-card-text>
                    <v-divider />
                    <v-card-actions>
                      <v-btn
                        :loading="uploading"
                        color="gray"
                        text
                        @click="() => showDeleteModal = false"
                      >
                        Cancel
                      </v-btn>
                      <v-btn
                        :loading="uploading"
                        color="red"
                        text
                        @click="() => deleteExperiment(experiment.id)"
                      >
                        Delete
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </v-card>
              <v-card flat>
                <v-icon
                  v-show="experiment === currentExperiment"
                  :color="loadingIconColor"
                  class="pl-5"
                >
                  {{ loadingIcon }}
                </v-icon>
              </v-card>
            </v-card>
            <ul class="scans">
              <li
                v-for="scan of scansForExperiment(experiment.id)"
                :key="`s.${scan.id}`"
                :class="scanStateClass(scan)"
              >
                <v-tooltip right>
                  <template #activator="{ on, attrs }">
                    <v-btn
                      v-bind="attrs"
                      :to="getURLForScan(scan.id)"
                      :disabled="!includeScan(scan.id)"
                      class="ml-0 px-1 scan-name"
                      href
                      text
                      small
                      active-class=""
                      v-on="on"
                    >
                      {{ ellipsisText(scan.name) }}
                      <span
                        v-if="scan.decisions.length !== 0"
                        :class="scan.color + ' pl-3'"
                        small
                      >({{ scan.decision }})</span>
                    </v-btn>
                  </template>
                  <span>
                    {{ scan.decision ? decisionOptions[scan.decision] + ', ' : '' }}
                    {{ scanState(scan) }}
                  </span>
                </v-tooltip>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      <div
        v-else-if="currentProject.experiments.length"
        class="pa-5"
        style="width: 60%; text-align: center"
      >
        <v-progress-circular indeterminate />
      </div>
      <div
        v-else
        class="pa-5"
        style="width: max-content"
      >
        <span class="px-5">No imported data.</span>
      </div>
      <v-dialog
        v-if="!minimal && MIQAConfig.S3_SUPPORT"
        v-model="showUploadModal"
        width="600px"
      >
        <template #activator="{ on, attrs }">
          <div
            v-bind="attrs"
            class="add-scans"
            v-on="on"
          >
            <v-btn
              class="green white--text"
              @click="() => { experimentNameForUpload = '' }"
            >
              + Add Scans...
            </v-btn>
          </div>
        </template>

        <v-card>
          <v-btn
            icon
            style="float:right"
            @click="showUploadModal = false"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-card-title class="text-h6">
            Upload Image Files to Experiment
          </v-card-title>
          <div
            class="d-flex px-6"
            style="align-items: baseline; justify-content: space-between;"
          >
            <div
              class="d-flex mode-toggle"
            >
              <span>Upload to New</span>
              <v-switch
                :value="uploadToExisting"
                :disabled="!(orderedExperiments && orderedExperiments.length)"
                inset
                dense
                style="display: inline-block; max-height: 40px; max-width: 60px;"
                class="px-3 ma-0"
                @change="(value) => { uploadToExisting = value; experimentNameForUpload = '' }"
              />
              <span
                :class="!(orderedExperiments && orderedExperiments.length) ? 'grey--text' : ''"
              >
                Upload to Existing
              </span>
            </div>
            <div style="max-width:200px">
              <v-select
                v-if="orderedExperiments && orderedExperiments.length && uploadToExisting"
                v-model="experimentNameForUpload"
                :items="orderedExperiments"
                item-text="name"
                label="Select Experiment"
                dense
              />
              <v-text-field
                v-else
                v-model="experimentNameForUpload"
                label="Name new Experiment"
              />
            </div>
          </div>
          <div class="ma-5">
            <v-file-input
              v-model="fileSetForUpload"
              label="Image files (.nii.gz, .nii, .mgz, .nrrd)"
              prepend-icon="mdi-paperclip"
              multiple
              chips
              @click:clear="delayPrepareDropZone"
            >
              <template #selection="{ index, text }">
                <v-chip
                  v-if="index < 2"
                  small
                >
                  {{ text }}
                </v-chip>

                <span
                  v-else-if="index === 2"
                  class="text-overline grey--text text--darken-3 mx-2"
                >
                  +{{ fileSetForUpload.length - 2 }}
                  file{{ fileSetForUpload.length - 2 > 1 ? 's' : '' }}
                </span>
              </template>
            </v-file-input>
            <div
              v-if="fileSetForUpload.length == 0"
              id="dropZone"
              style="text-align: center"
              class="pa-3 drop-zone"
              @drop.prevent="addDropFiles"
              @dragover.prevent
            >
              or drag and drop here
            </div>
          </div>
          <v-divider />
          <v-card-actions>
            <div
              v-if="uploadError"
              style="color: red;"
            >
              {{ uploadError }}
            </div>
            <v-spacer />
            <v-btn
              :loading="uploading"
              :disabled="fileSetForUpload.length < 1 || !experimentNameForUpload"
              color="primary"
              text
              @click="uploadToExperiment()"
            >
              Upload
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>
  </v-card>
</template>

<style lang="scss" scoped>
.current {
  background: rgb(206, 206, 206);
}
.state-unreviewed::marker {
  color: #1460A3;
  content: '\25C8';
}
.state-needs-tier-2-review::marker {
  color: #6DB1ED;
  content: '\25C8'
}
.state-complete::marker {
  color: #00C853;
  content: '\25C8'
}
li.cached {
  list-style-type: disc;
}
ul.experiment {
  list-style: none;
}
ul.scans {
  padding-left: 15px;
}
.scans-view {
  text-transform: none;
  display: flex;
  flex-flow: row wrap-reverse;
  align-items: baseline;
  justify-content: space-between;
}
.scans-view > div {
  width: min-content;
}
.scan-name .v-btn__content {
  text-transform: none;
}
.mode-toggle {
  align-items: baseline;
  display: inline-block;
}
.add-scans {
  min-width: 150px;
  text-align: right;
  padding-right: 15px;
}
.drop-zone {
  border: 1px dashed #999999;
}
.drop-zone.hover {
  background-color: rgba(92, 167, 247, 0.5);
}
</style>
