<script lang="ts">
import {
  defineComponent,
  ref,
  computed,
  watch,
} from 'vue';
import _ from 'lodash';
import UserAvatar from '@/components/UserAvatar.vue';
import djangoRest from '@/django';
import store, { includeScan } from '@/store';
import { decisionOptions } from '@/constants';
import { Experiment } from '@/types';

export default defineComponent({
  name: 'ExperimentsView',
  components: { UserAvatar },
  props: {
    minimal: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const showUploadModal = ref(false);
    const showDeleteModal = ref();
    const uploadToExisting = ref(false);
    const uploading = ref(false);
    const uploadError = ref('');
    const experimentNameForUpload = ref('');
    const fileSetForUpload = ref([]);

    const miqaConfig = computed(() => store.state.MIQAConfig);
    const currentProject = computed(() => store.state.currentProject);
    const currentTaskOverview = computed(() => store.state.currentTaskOverview);
    const frames = computed(() => store.state.frames);
    const scanFrames = computed(() => store.state.scanFrames);
    const scans = computed(() => store.state.scans);
    const loadingExperiment = computed(() => store.state.loadingExperiment);
    const experimentScans = computed(() => store.state.experimentScans);
    const experimentIds = computed(() => store.state.experimentIds);
    const experiments = computed(() => store.state.experiments);
    const reviewMode = computed(() => store.state.reviewMode);
    const currentScan = computed(() => store.getters.currentScan);
    const currentExperiment = computed(() => store.getters.currentExperiment);
    // Gets the experiments based on the experiment ids
    const orderedExperiments = computed(
      () => experimentIds.value.map((expId) => experiments.value[expId]),
    );
    const loadingIcon = computed(() => (loadingExperiment.value
      ? 'mdi-progress-clock'
      : 'mdi-check-circle-outline'));
    const loadingIconColor = computed(() => (loadingExperiment.value ? 'red' : 'green'));

    const setReviewMode = (mode) => store.commit('SET_REVIEW_MODE', mode);
    const loadProject = (project) => store.dispatch('loadProject', project);

    /** Assigns a color and character if a decision has been rendered on a given scan */
    function decisionToRating(decisions) {
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
    }
    /** Gets all scans associated with the provided experimentId */
    function scansForExperiment(expId) {
      const expScanIds = experimentScans.value[expId];
      return expScanIds.filter(
        (scanId) => Object.keys(scans.value).includes(scanId),
      ).map((scanId) => {
        const scan = scans.value[scanId];
        return {
          ...scan,
          ...decisionToRating(scan.decisions),
        };
      });
    }
    /** Receives a string like "NCANDA_E08710" (name of an image file),
     * this is used as the experiment name */
    function ellipsisText(str) {
      if (!props.minimal) return str;
      if (str.length > 25) {
        return `${str.substr(0, 10)}...${
          str.substr(str.length - 10, str.length)}`;
      }
      return str;
    }
    /** Get the URL of the first frame in the current scan */
    function getURLForScan(scanId) {
      return `/${currentProject.value.id}/${scanId}`;
    }
    function scanState(scan) {
      let scanTaskState;
      if (currentTaskOverview.value) {
        scanTaskState = currentTaskOverview.value.scan_states[scan.id];
      }
      return scanTaskState || 'unreviewed';
    }
    /** Adds a class to a scan representative of the scan's task state. */
    function scanStateClass(scan) {
      let classes = `body-1 state-${scanState(scan).replace(/ /g, '-')}`;
      if (scan === currentScan.value) {
        classes = `${classes} current`;
      }
      return classes;
    }
    /** Listens for images being dragged into the dropzone */
    function prepareDropZone() {
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
    }
    function delayPrepareDropZone() {
      setTimeout(prepareDropZone, 500);
    }
    /** Gets files dropped into the dropzone */
    function addDropFiles(e) {
      fileSetForUpload.value = [...e.dataTransfer.files];
    }
    async function uploadToExperiment() {
      let experimentId;
      uploading.value = true;
      try {
        // If we are uploading to a new experiment
        if (!uploadToExisting.value) {
          // Create a new experiment, below returns instance of ResponseData
          const newExperiment = await djangoRest.createExperiment(
            currentProject.value.id,
            experimentNameForUpload.value,
          );
          experimentId = newExperiment.id;
        } else {
          // Find the experiment's id that matches the experiment selected
          experimentId = (Object.values(experiments.value).find(
            (experiment: Experiment) => experiment.name === experimentNameForUpload.value,
          ) as { id: string, name: string }).id;
        }
        await djangoRest.uploadToExperiment(experimentId, fileSetForUpload.value);
        await loadProject(currentProject.value);
        showUploadModal.value = false;
      } catch (ex) {
        const text = ex || 'Upload failed due to server error.';
        uploadError.value = text;
      }
      uploading.value = false;
    }
    function deleteExperiment(experimentId) {
      djangoRest.deleteExperiment(experimentId).then(
        () => {
          loadProject(currentProject.value);
          showDeleteModal.value = false;
        },
      );
    }

    watch(showUploadModal, () => {
      /** Begins loading upload modal */
      delayPrepareDropZone();
    });
    watch(currentProject, () => {
      /** When the project changes, reset the local state for the project. */
      showUploadModal.value = false;
      uploadToExisting.value = false;
      uploadError.value = '';
      fileSetForUpload.value = [];
      uploading.value = false;
    });

    return {
      miqaConfig,
      showUploadModal,
      showDeleteModal,
      uploadToExisting,
      uploading,
      uploadError,
      experimentNameForUpload,
      fileSetForUpload,
      currentProject,
      currentTaskOverview,
      frames,
      scanFrames,
      scans,
      loadingExperiment,
      experimentScans,
      experimentIds,
      experiments,
      reviewMode,
      currentScan,
      currentExperiment,
      orderedExperiments,
      loadingIcon,
      loadingIconColor,
      setReviewMode,
      ellipsisText,
      deleteExperiment,
      scansForExperiment,
      scanStateClass,
      getURLForScan,
      includeScan,
      decisionOptions,
      scanState,
      delayPrepareDropZone,
      addDropFiles,
      uploadToExperiment,
    };
  },
});
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
          @change="setReviewMode"
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
        v-if="!minimal && miqaConfig.S3_SUPPORT"
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
