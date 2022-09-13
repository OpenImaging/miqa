<script>
import _ from 'lodash';
import { mapGetters, mapMutations, mapState } from 'vuex';
import djangoRest from '@/django';
import store from '@/store';
import EvaluationResults from '@/components/EvaluationResults.vue';
import UserAvatar from './UserAvatar.vue';

export default {
  name: 'DecisionButtons',
  components: {
    EvaluationResults,
    UserAvatar,
  },
  inject: ['user', 'MIQAConfig'],
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
  data() {
    return {
      warnDecision: false,
      newComment: '',
      confirmedPresent: [],
      confirmedAbsent: [],
      decisionShortcuts: {
        U: 'u',
        UE: 'i',
        'Q?': 'o',
        UN: 'p',
      },
    };
  },
  computed: {
    ...mapState([
      'currentViewData',
      'currentProject',
      'proxyManager',
      'vtkViews',
      'storeCrosshairs',
    ]),
    ...mapGetters([
      'currentViewData',
      'myCurrentProjectRoles',
    ]),
    artifacts() {
      if (this.currentProject.settings.artifacts !== 'undefined') {
        const currentArtifacts = this.currentProject.settings.artifacts;
        return currentArtifacts.map((name) => ({
          value: name,
          labelText: this.convertValueToLabel(name),
        }));
      } else {
        return this.MIQAConfig.artifact_options.map((name) => ({
          value: name,
          labelText: this.convertValueToLabel(name),
        }));
      }
    },
    chips() {
      return this.artifacts.map((artifact) => [artifact, this.getCurrentChipState(artifact)]);
    },
    suggestedArtifacts() {
      if (this.currentViewData.scanDecisions && this.currentViewData.scanDecisions.length > 0) {
        const lastDecision = _.sortBy(
          this.currentViewData.scanDecisions, (dec) => dec.created,
        )[0];
        const lastDecisionArtifacts = lastDecision.user_identified_artifacts;
        // Of the artifacts chosen in the last scandecision,
        // include only those marked as present.
        return Object.entries(lastDecisionArtifacts).filter(
          ([, present]) => present === this.MIQAConfig.artifact_states.PRESENT,
        ).map(([artifactName]) => artifactName);
      } if (this.currentViewData.currentAutoEvaluation) {
        const predictedArtifacts = this.currentViewData.currentAutoEvaluation.results;
        // Of the results from the NN, filter these to
        // exclude overall_quality and normal_variants (not real artifacts)
        // and exclude anything under the suggestion threshold set by the server.
        // Then map these to display the negative connotation version of the artifact.
        return Object.entries(predictedArtifacts).filter(
          ([artifactName, percentCertainty]) => artifactName !== 'overall_quality'
            && artifactName !== 'normal_variants'
            && percentCertainty < this.MIQAConfig.auto_artifact_threshold,
        ).map(([artifactName]) => artifactName.replace('no_', '').replace('full', 'partial'));
      }
      return [];
    },
    options() {
      const myOptions = [
        {
          label: 'Usable',
          code: 'U',
          color: 'green darken-3 white--text',
        },
      ];
      if (this.myCurrentProjectRoles.includes('tier_2_reviewer')) {
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
      } else if (this.myCurrentProjectRoles.includes('tier_1_reviewer') || this.myCurrentProjectRoles.includes('superuser')) {
        myOptions.push({
          label: 'Questionable',
          code: 'Q?',
          color: 'grey darken-3 white--text',
        });
      }
      return myOptions;
    },
  },
  watch: {
    currentViewData() {
      this.confirmedPresent = [];
      this.confirmedAbsent = [];
    },
    newComment() {
      this.warnDecision = false;
    },
    confirmedPresent() {
      this.warnDecision = false;
    },
    confirmedAbsent() {
      this.warnDecision = false;
    },
  },
  mounted() {
    if (!this.currentViewData.currentAutoEvaluation) {
      this.pollInterval = setInterval(this.pollForEvaluation, 1000 * 10);
    }
  },
  beforeUnmount() {
    clearInterval(this.pollInterval);
  },
  methods: {
    ...mapMutations([
      'updateExperiment',
      'setFrameEvaluation',
    ]),
    async pollForEvaluation() {
      const frameData = await djangoRest.frame(this.currentViewData.currentFrame.id);
      if (frameData.frame_evaluation) {
        this.setFrameEvaluation(frameData.frame_evaluation);
        clearInterval(this.pollInterval);
      }
    },
    convertValueToLabel(artifactName) {
      return artifactName
        .replace('susceptibility_metal', 'metal_susceptibility')
        .replace('partial_brain_coverage', 'partial_coverage')
        .replace(/_/g, ' ')
        .replace(
          /\w\S*/g,
          (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase(),
        );
    },
    switchLock() {
      this.$emit('switchLock', this.currentViewData.experimentId, null, true);
    },
    getCurrentChipState(artifact) {
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
      if (this.confirmedPresent.includes(artifact.value)) {
        // confirmed present
        chipState.state = 1;
        chipState.outlined = false;
        chipState.color = 'red';
        chipState.textColor = 'white';
      } else if (this.confirmedAbsent.includes(artifact.value)) {
        // confirmed absent
        chipState.state = 2;
        chipState.textDecoration = 'line-through';
      } else if (this.suggestedArtifacts.includes(artifact.value)) {
        // suggested unconfirmed
        chipState.state = 3;
        chipState.label += '?';
        chipState.color = 'red';
        chipState.textColor = 'red';
      }
      return chipState;
    },
    clickChip(artifact, chipState) {
      // this function determines state cycle of chips
      switch (chipState) {
        case 1:
          // currently confirmed present
          this.confirmedPresent = this.confirmedPresent.filter(
            (artifactName) => artifactName !== artifact.value,
          );
          this.confirmedAbsent.push(artifact.value);
          break;
        case 2:
          // currently confirmed absent
          this.confirmedAbsent = this.confirmedAbsent.filter(
            (artifactName) => artifactName !== artifact.value,
          );
          break;
        default:
          // currently unconfirmed
          this.confirmedPresent.push(artifact.value);
      }
    },
    async refreshTaskOverview() {
      if (this.currentProject) {
        const taskOverview = await djangoRest.projectTaskOverview(this.currentProject.id);
        if (JSON.stringify(store.state.currentTaskOverview) !== JSON.stringify(taskOverview)) {
          store.commit.setTaskOverview(taskOverview);
        }
      }
    },
    handleCommentChange(value) {
      this.newComment = value;
    },
    async handleCommentSave(decision) {
      if (
        this.newComment.trim().length > 0
        || decision === 'U'
        || this.confirmedPresent.length > 0
        || this.confirmedAbsent.length > 0
      ) {
        try {
          const userIdentifiedArtifacts = {
            present: this.confirmedPresent,
            absent: this.confirmedAbsent,
          };
          const { addScanDecision } = store.commit;
          const zxyLocation = this.vtkViews.map(
            (view) => this.proxyManager.getRepresentation(null, view).getSlice(),
          );
          const savedObj = await djangoRest.setDecision(
            this.currentViewData.scanId,
            decision,
            this.newComment,
            userIdentifiedArtifacts,
            (this.storeCrosshairs ? {
              i: zxyLocation[1],
              j: zxyLocation[2],
              k: zxyLocation[0],
            } : {}),
          );
          addScanDecision({
            currentScan: this.currentViewData.scanId,
            newDecision: savedObj,
          });
          this.refreshTaskOverview();
          this.$emit('handleKeyPress', 'next');
          this.$snackbar({
            text: 'Saved decision successfully.',
            timeout: 6000,
          });
          this.warnDecision = false;
          this.newComment = '';
        } catch (err) {
          this.$snackbar({
            text: `Save failed: ${err || 'Server error'}`,
            timeout: 6000,
          });
          // If error is due a lock contention, it is likely because someone claimed the lock
          //   after we got the experiment data
          //   (else we would already know about the lock owner and not attempt to lock).
          //   Thus, we need to update our experiment's info and check who the lock owner is
          if (err.toString().includes('lock')) {
            this.updateExperiment(await djangoRest.experiment(this.currentViewData.experimentId));
          }
        }
      } else {
        this.warnDecision = true;
      }
    },
  },
};
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
          v-for="([artifact, chipState]) in chips"
          v-bind="artifact"
          :key="artifact.value"
          :outlined="chipState.outlined"
          :color="chipState.color"
          :text-color="chipState.textColor"
          :style="'text-decoration: '+chipState.textDecoration +'; margin-bottom: 3px;'"
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
          ref="commentInput"
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
              v-mousetrap="[
                { bind: decisionShortcuts[option.code],
                  handler: () => handleCommentSave(option.code) },
              ]"
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
          You {{ editRights ?'have not claimed' :'do not have' }}
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
            {{ lockOwner ?"Steal edit access" :"Claim edit access" }}
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
