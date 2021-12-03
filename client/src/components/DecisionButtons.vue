<script>
import _ from 'lodash';
import { mapGetters, mapState } from 'vuex';
import djangoRest from '@/django';
import store from '@/store';
import EvaluationResults from '@/components/EvaluationResults.vue';

export default {
  name: 'DecisionButtons',
  inject: ['user', 'MIQAConfig'],
  components: {
    EvaluationResults,
  },
  props: {
    experimentIsEditable: {
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
    };
  },
  computed: {
    ...mapState([
      'currentViewData',
    ]),
    ...mapGetters([
      'currentViewData',
      'myCurrentProjectRoles',
    ]),
    artifacts() {
      return this.MIQAConfig.artifact_options.map((name) => ({
        value: name,
        labelText: this.convertValueToLabel(name),
      }));
    },
    chips() {
      return this.artifacts.map((artifact) => [artifact, this.getCurrentChipState(artifact)]);
    },
    suggestedArtifacts() {
      if (this.currentViewData.scanDecisions.length > 0) {
        const lastDecisionArtifacts = _.last(_.sortBy(
          this.currentViewData.scanDecisions, (dec) => dec.created,
        )).user_identified_artifacts;
        return Object.entries(lastDecisionArtifacts).filter(
          ([, present]) => present === 1,
        ).map(([artifactName]) => artifactName);
      } if (this.currentViewData.currentAutoEvaluation) {
        const predictedArtifacts = this.currentViewData.currentAutoEvaluation.results;
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
  },
  methods: {
    convertValueToLabel(artifactName) {
      return artifactName.replace('susceptibility_metal', 'metal_susceptibility').replace(/_/g, ' ').replace(
        /\w\S*/g,
        (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase(),
      );
    },
    getCurrentChipState(artifact) {
      // this function determines the styling of the four chip states.
      // four states of a chip are:
      //  confirmed present, confirmed absent, suggested unconfirmed, unsuggested unconfirmed

      // default is unsuggested unconfirmed
      let state = 0;
      let label = artifact.labelText;
      let outlined = true;
      let color = 'default';
      let textDecoration = 'none';
      let textColor = 'default';
      if (this.confirmedPresent.includes(artifact.value)) {
        // confirmed present
        state = 1;
        outlined = false;
        color = 'green';
        textColor = 'white';
      } else if (this.confirmedAbsent.includes(artifact.value)) {
        // confirmed absent
        state = 2;
        textDecoration = 'line-through';
      } else if (this.suggestedArtifacts.includes(artifact.value)) {
        state = 3;
        // suggested unconfirmed
        label += '?';
        color = 'green';
        textColor = 'green';
      }
      return [state, label, outlined, color, textColor, textDecoration];
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
    handleCommentChange(value) {
      this.newComment = value;
    },
    async handleCommentSave(decision) {
      if (this.newComment.trim().length > 0 || decision === 'U') {
        try {
          const userIdentifiedArtifacts = {
            present: this.confirmedPresent,
            absent: this.confirmedAbsent,
          };
          const { addScanDecision } = store.commit;
          const savedObj = await djangoRest.setDecision(
            this.currentViewData.scanId,
            decision,
            this.newComment,
            userIdentifiedArtifacts,
          );
          addScanDecision({
            currentScan: this.currentViewData.scanId,
            newDecision: savedObj,
          });
          this.$emit('handleKeyPress', 'next');
          this.$snackbar({
            text: 'Saved decision successfully.',
            timeout: 6000,
          });
          this.warnDecision = false;
          this.newComment = '';
        } catch (err) {
          console.log(err);
          this.$snackbar({
            text: `Save failed: ${err.response.data.detail || 'Server error'}`,
            timeout: 6000,
          });
        }
      } else {
        this.warnDecision = true;
      }
    },
  },
};
</script>

<template>
  <div style="pa-0 ma-0">
    <v-row no-gutters>
      <v-col cols="7">
        <v-subheader class="pl-0">
          Indicate presence/absence of artifacts in this scan
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                v-on="on"
                small
                class="pl-2"
              >
                info
              </v-icon>
            </template>
            <span>
              Toggle each tag below.
              Fill green to confirm an artifact is present.
              Crossthrough to confirm an artifact is absent.
            </span>
          </v-tooltip>
        </v-subheader>
      </v-col>
      <v-col
        v-if="currentViewData.currentAutoEvaluation"
        cols="5"
        class="d-flex justify-end align-center"
      >
        Auto Evaluation
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-icon
              v-bind="attrs"
              v-on="on"
              small
              style="height: 25px; padding: 5px"
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
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col
        cols="12"
        class="d-flex justify-space-around flex-wrap"
      >
        <v-chip
          v-for="([artifact, chipState]) in chips"
          v-bind="artifact"
          :key="artifact.value"
          @click="clickChip(artifact, chipState[0])"
          :outlined="chipState[2]"
          :color="chipState[3]"
          :text-color="chipState[4]"
          :style="'text-decoration: '+chipState[5] +'; margin-bottom: 3px;'"
        >
          {{ chipState[1] }}
        </v-chip>
      </v-col>
    </v-row>
    <v-row
      v-if="experimentIsEditable"
    >
      <v-col
        cols="12"
        class="pb-0 mb-0 pt-5"
      >
        <v-textarea
          @input="handleCommentChange"
          :counter="!warnDecision"
          :hide-details="warnDecision"
          v-model="newComment"
          filled
          no-resize
          height="60px"
          name="input-comment"
          label="Evaluation Comment"
          placeholder="Write a comment about the scan and submit a decision"
        />
      </v-col>
    </v-row>
    <v-row
      v-if="warnDecision"
      no-gutters
    >
      <v-col
        cols="12"
        class="red--text"
        style="text-align: center"
      >
        Decisions other than "usable" must have a comment.
      </v-col>
    </v-row>
    <div
      v-if="experimentIsEditable"
      no-gutters
      class="button-container"
    >
      <div
        v-for="option in options"
        :key="option.code"
        style="text-align: center"
      >
        <v-btn
          @click="handleCommentSave(option.code)"
          :color="option.color"
        >
          {{ option.label }}
        </v-btn>
      </div>
    </div>
  </div>
</template>

<style scoped>
.button-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-around;
}
</style>
