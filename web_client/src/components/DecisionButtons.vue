<script lang="ts">
import {
  defineComponent,
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
} from 'vue';
import _ from 'lodash';
import djangoRest from '@/django';
import store from '@/store';
import EvaluationResults from '@/components/EvaluationResults.vue';
import { AUTO_ADVANCE } from '@/constants';
import UserAvatar from './UserAvatar.vue';

export default defineComponent({
  name: 'DecisionButtons',
  components: {
    EvaluationResults,
    UserAvatar,
  },
  props: {
    experimentIsEditable: {
      type: Boolean,
      default: false,
    },
    editRights: {
      type: Boolean,
      default: false,
    },
    lockOwner: {
      type: Object,
      default: undefined,
    },
    loadingLock: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, context) {
    const warnDecision = ref(false);
    const newComment = ref('');
    const confirmedPresent = ref([]);
    const confirmedAbsent = ref([]);
    const pollInterval = ref();
    const decisionShortcuts = {
      U: 'u',
      UE: 'i',
      'Q?': 'o',
      UN: 'p',
    };

    const user = computed(() => store.state.me);
    const miqaConfig = computed(() => store.state.MIQAConfig);
    const currentProject = computed(() => store.state.currentProject);
    const proxyManager = computed(() => store.state.proxyManager);
    const vtkViews = computed(() => store.state.vtkViews);
    const storeCrosshairs = computed(() => store.state.storeCrosshairs);
    const currentViewData = computed(() => store.getters.currentViewData);
    const myCurrentProjectRoles = computed(() => store.getters.myCurrentProjectRoles);

    const addScanDecision = (decision) => store.commit('ADD_SCAN_DECISION', decision);
    const updateExperiment = (experiment) => store.commit('UPDATE_EXPERIMENT', experiment);
    const setTaskOverview = (overview) => store.commit('SET_TASK_OVERVIEW', overview);
    const setFrameEvaluation = (evaluation) => store.commit('SET_FRAME_EVALUATION', evaluation);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);

    /** Takes an artifact name, e.g. 'something_artifact' and converts to 'Something artifact' */
    function convertValueToLabel(artifactName) {
      return artifactName
        .replace('susceptibility_metal', 'metal_susceptibility')
        .replace('partial_brain_coverage', 'partial_coverage')
        .replace(/_/g, ' ')
        .replace(
          /\w\S*/g,
          (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase(),
        );
    }

    /** The list of artifacts generally should not change unless the project changes */
    const artifacts = computed(() => miqaConfig.value.artifact_options.map((name) => ({
      value: name,
      labelText: convertValueToLabel(name),
    })));
    /** Determines which artifacts are suggested.
     * Artifacts are suggested either: 1. By a prior user decision or 2. By auto evaluation
     */
    const suggestedArtifacts = computed(() => {
      if (currentViewData.value.scanDecisions && currentViewData.value.scanDecisions.length > 0) {
        const lastDecision = _.sortBy(
          currentViewData.value.scanDecisions,
          (decision) => { Date.parse(decision.created); },
        )[0];
        // Gets the artifacts associated with the most recent decision
        const lastDecisionArtifacts = lastDecision.user_identified_artifacts;
        // Of the artifacts chosen in the last scanDecision,
        // include only those marked as present.
        return Object.entries(lastDecisionArtifacts).filter(
          ([, present]) => present === miqaConfig.value.artifact_states.PRESENT,
        ).map(([artifactName]) => artifactName);
      // If a current auto evaluation exists
      } if (currentViewData.value.currentAutoEvaluation) {
        const predictedArtifacts = currentViewData.value.currentAutoEvaluation.results;
        // Of the results from the NN, filter these to
        // exclude overall_quality and normal_variants (not real artifacts)
        // and exclude anything under the suggestion threshold set by the server.
        // Then map these to display the negative connotation version of the artifact.
        return Object.entries(predictedArtifacts).filter(
          ([artifactName, percentCertainty]) => artifactName !== 'overall_quality'
            && artifactName !== 'normal_variants'
            && percentCertainty as number < miqaConfig.value.auto_artifact_threshold,
        ).map(([artifactName]) => artifactName.replace('no_', '').replace('full', 'partial'));
      }
      return [];
    });
    // Displays the decision buttons based on user's roles
    const options = computed(() => {
      const myOptions = [
        {
          label: 'Usable',
          code: 'U',
          color: 'green darken-3 white--text',
        },
      ];
      if (myCurrentProjectRoles.value.includes('tier_1_reviewer') || myCurrentProjectRoles.value.includes('superuser')) {
        myOptions.push({
          label: 'Questionable',
          code: 'Q?',
          color: 'grey darken-3 white--text',
        });
      }
      if (myCurrentProjectRoles.value.includes('tier_2_reviewer')) {
        myOptions.push({
          label: 'Usable-Extra',
          code: 'UE',
          color: 'grey darken-3 white--text',
        });
        myOptions.push({
          label: 'Unusable',
          code: 'UN',
          color: 'red darken-3 white--text',
        });
      }
      return myOptions;
    });

    /** Resets currentViewData for present/absent whenever image changes */
    watch(currentViewData, () => {
      confirmedPresent.value = [];
      confirmedAbsent.value = [];
    });
    /** If a change is made to comment, present, absent, set warnDecision false */
    watch(newComment, () => {
      warnDecision.value = false;
    });
    watch(confirmedPresent, () => {
      warnDecision.value = false;
    });
    watch(confirmedAbsent, () => {
      warnDecision.value = false;
    });

    async function pollForEvaluation() {
      const frameData = await djangoRest.frame(currentViewData.value.currentFrame.id);
      if (frameData.frame_evaluation) {
        setFrameEvaluation(frameData.frame_evaluation);
        clearInterval(pollInterval.value);
      }
    }
    /**
     * Determines the styling of the four chip states
     *
     * Four possible states are: confirmed present, confirmed absent,
     * suggested unconfirmed, unsuggested unconfirmed (default)
     */
    function getCurrentChipState(artifact) {
      // this function determines the styling of the four chip states.
      // four states of a chip are:
      //  confirmed present, confirmed absent, suggested unconfirmed, unsuggested unconfirmed

      // default is unsuggested unconfirmed
      const chipState = {
        state: 0,
        label: artifact.labelText,
        outlined: true,
        color: 'default',
        textDecoration: 'none',
        textColor: 'default',
      };
      if (confirmedPresent.value.includes(artifact.value)) {
        // confirmed present
        chipState.state = 1;
        chipState.outlined = false;
        chipState.color = 'red';
        chipState.textColor = 'white';
      } else if (confirmedAbsent.value.includes(artifact.value)) {
        // confirmed absent
        chipState.state = 2;
        chipState.textDecoration = 'line-through';
      } else if (suggestedArtifacts.value.includes(artifact.value)) {
        // suggested unconfirmed
        chipState.state = 3;
        chipState.label += '?';
        chipState.color = 'red';
        chipState.textColor = 'red';
      }
      return chipState;
    }
    /** Changes the state of a chip when it has been clicked upon */
    function clickChip(artifact, chipState) {
      // this function determines state cycle of chips
      switch (chipState) {
        case 1:
          // currently confirmed present
          confirmedPresent.value = confirmedPresent.value.filter(
            (artifactName) => artifactName !== artifact.value,
          );
          confirmedAbsent.value.push(artifact.value);
          break;
        case 2:
          // currently confirmed absent
          confirmedAbsent.value = confirmedAbsent.value.filter(
            (artifactName) => artifactName !== artifact.value,
          );
          break;
        default:
          // currently unconfirmed
          confirmedPresent.value.push(artifact.value);
      }
    }
    async function refreshTaskOverview() {
      if (currentProject.value) {
        const taskOverview = await djangoRest.projectTaskOverview(currentProject.value.id);
        // If API has different data, update taskOverview
        if (JSON.stringify(store.state.currentTaskOverview) !== JSON.stringify(taskOverview)) {
          setTaskOverview(taskOverview);
        }
      }
    }
    function switchLock() {
      context.emit('switchLock', currentViewData.value.experimentId, null, true);
    }
    function handleCommentChange(value) {
      newComment.value = value;
    }
    async function handleCommentSave(decision) {
      // If feedback has been left on the scan
      if (
        newComment.value.trim().length > 0
        || decision === 'U'
        || confirmedPresent.value.length > 0
        || confirmedAbsent.value.length > 0
      ) {
        try {
          // Object with present/absent artifacts
          const userIdentifiedArtifacts = {
            present: confirmedPresent.value,
            absent: confirmedAbsent.value,
          };
          const zxyLocation = vtkViews.value.map(
            (view) => proxyManager.value.getRepresentation(null, view).getSlice(),
          );
          // Create new scan decision using API
          const savedObj = await djangoRest.setDecision(
            currentViewData.value.scanId,
            decision,
            newComment.value,
            userIdentifiedArtifacts,
            (storeCrosshairs.value ? {
              i: zxyLocation[1],
              j: zxyLocation[2],
              k: zxyLocation[0],
            } : {}),
          );
          addScanDecision({
            currentScanId: currentViewData.value.scanId,
            newScanDecision: savedObj,
          });
          await refreshTaskOverview();
          if (AUTO_ADVANCE) {
            context.emit('handleKeyPress', 'next');
          }
          setSnackbar('Saved decision successfully.');
          warnDecision.value = false;
          newComment.value = '';
        } catch (err) {
          setSnackbar(`Save failed: ${err || 'Server error'}`);
          // If error is due a lock contention, it is likely because someone claimed the lock
          //   after we got the experiment data
          //   (else we would already know about the lock owner and not attempt to lock).
          //   Thus, we need to update our experiment's info and check who the lock owner is
          if (err.toString().includes('lock')) {
            updateExperiment(await djangoRest.experiment(currentViewData.value.experimentId));
          }
        }
      } else {
        warnDecision.value = true;
      }
    }
    function keyPress(event) {
      if (['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName)) return;
      if (Object.values(decisionShortcuts).includes(event.key)) {
        const targetDecision = Object.keys(decisionShortcuts).find(
          (d) => decisionShortcuts[d] === event.key,
        );
        handleCommentSave(targetDecision);
      }
    }

    onMounted(() => {
      // Check every 10 secs for whether an auto evaluation has been completed
      if (!currentViewData.value.currentAutoEvaluation) {
        pollInterval.value = setInterval(pollForEvaluation, 1000 * 10);
      }
      window.addEventListener('keypress', keyPress);
    });
    onBeforeUnmount(() => {
      // Stop polling for auto evaluations
      clearInterval(pollInterval.value);
      window.removeEventListener('keypress', keyPress);
    });

    /** Returns an array containing the name of an artifact and it's current selection state */
    const chips = computed(
      () => artifacts.value.map(
        (artifact) => ({ artifact, chipState: getCurrentChipState(artifact) }),
      ),
    );
    return {
      user,
      currentProject,
      proxyManager,
      vtkViews,
      storeCrosshairs,
      currentViewData,
      myCurrentProjectRoles,
      artifacts,
      suggestedArtifacts,
      options,
      warnDecision,
      newComment,
      confirmedPresent,
      confirmedAbsent,
      decisionShortcuts,
      pollForEvaluation,
      getCurrentChipState,
      clickChip,
      refreshTaskOverview,
      switchLock,
      handleCommentChange,
      handleCommentSave,
      chips,
    };
  },
});
</script>

<template>
  <v-container
    fluid
    class="px-5"
  >
    <v-flex
      class="d-flex pb-3"
      style="justify-content: space-between; column-gap: 20px"
    >
      <v-subheader
        v-if="experimentIsEditable"
        class="pa-0 ma-0"
      >
        Indicate artifacts in this scan
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <v-icon
              v-bind="attrs"
              small
              class="pl-2"
              v-on="on"
            >
              info
            </v-icon>
          </template>
          <span>
            Toggle each tag below.
            Fill red to confirm an artifact is present.
            Crossthrough to confirm an artifact is absent.
          </span>
        </v-tooltip>
      </v-subheader>
      <v-flex
        v-if="currentViewData.currentAutoEvaluation"
        style="display: flex; align-items: flex-start; justify-content: flex-end"
      >
        <v-subheader
          class="pa-0 ma-0"
          style="text-align: right"
        >
          Auto evaluation
        </v-subheader>
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <v-icon
              v-bind="attrs"
              small
              style="height: 25px; padding: 5px"
              v-on="on"
            >
              info
            </v-icon>
          </template>
          <span>
            An evaluation performed by the MIQA server using artificial intelligence
          </span>
        </v-tooltip>
        <EvaluationResults
          :results="currentViewData.currentAutoEvaluation.results"
        />
      </v-flex>
      <v-flex
        v-else
        cols="5"
        class="d-flex justify-end align-center"
      >
        <v-subheader
          class="pa-0 ma-0"
          style="text-align: right"
        >
          No Auto evaluation available
        </v-subheader>
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <v-icon
              v-bind="attrs"
              small
              style="height: 25px; padding: 5px"
              v-on="on"
            >
              info
            </v-icon>
          </template>
          <span>
            An evaluation performed by the MIQA server using artificial intelligence
          </span>
        </v-tooltip>
      </v-flex>
    </v-flex>
    <v-row
      v-if="experimentIsEditable"
      no-gutters
    >
      <v-col
        cols="12"
        class="d-flex justify-space-around flex-wrap"
      >
        <v-chip
          v-for="({ artifact, chipState }) in chips"
          v-bind="artifact"
          :key="artifact.value"
          :outlined="chipState.outlined"
          :color="chipState.color"
          :text-color="chipState.textColor"
          :style="'text-decoration: ' + chipState.textDecoration + '; margin-bottom: 3px;'"
          small
          @click="clickChip(artifact, chipState.state)"
        >
          {{ chipState.label }}
        </v-chip>
      </v-col>
    </v-row>
    <v-row
      v-if="experimentIsEditable"
      dense
    >
      <v-col
        cols="12"
        class="pt-5"
      >
        <v-textarea
          v-model="newComment"
          :counter="!warnDecision"
          :hide-details="warnDecision"
          filled
          no-resize
          height="80px"
          name="input-comment"
          label="Evaluation Comment"
          placeholder="Write a comment about the scan"
          @input="handleCommentChange"
        />
      </v-col>
    </v-row>
    <v-row
      v-if="warnDecision"
      dense
    >
      <v-col
        cols="12"
        class="red--text"
        style="text-align: center"
      >
        Decisions other than "usable" must have a comment or artifact selection.
      </v-col>
    </v-row>
    <v-row
      v-if="experimentIsEditable"
      no-gutters
    >
      <v-col cols="12">
        <div class="button-container">
          <div
            v-for="option in options"
            :key="option.code"
            style="text-align: center"
          >
            <v-btn
              :color="option.color"
              @click="handleCommentSave(option.code)"
            >
              {{ option.label }}
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>
    <v-row v-if="!experimentIsEditable">
      <v-col cols="12">
        <div
          class="uneditable-notice pa-3"
        >
          <v-icon>mdi-lock</v-icon>
          You {{ editRights ? 'have not claimed' : 'do not have' }}
          edit access on this Experiment.
          <div
            v-if="lockOwner"
            class="my-3"
            style="text-align:center"
          >
            <UserAvatar
              :target-user="lockOwner"
              as-editor
            />
            <br>
            {{ lockOwner.username }}
            <br>
            currently has edit access.
          </div>
          <v-btn
            v-if="editRights && (user.is_superuser || !lockOwner)"
            :loading="loadingLock"
            :disabled="loadingLock"
            color="primary"
            @click="switchLock"
          >
            {{ lockOwner ? "Steal edit access" : "Claim edit access" }}
          </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.button-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-around;
}
.v-subheader {
  height: 30px;
}
.uneditable-notice {
  display: flex;
  flex-flow: column wrap;
  width: 100%;
  height: 100%;
  justify-content: center;
  align-content: center;
  border: 1px dashed gray;
}
</style>
