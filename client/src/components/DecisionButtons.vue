<script>
import _ from 'lodash';
import { mapGetters, mapState } from 'vuex';
import djangoRest from '@/django';
import store from '@/store';

export default {
  name: 'DecisionButtons',
  inject: ['user', 'MIQAConfig'],
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
      selectedArtifacts: [],
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
    artifactOptions() {
      return this.MIQAConfig.artifact_options.map((name) => ({
        value: name,
        text: name.replace(/_/g, ' ').replace(
          /\w\S*/g,
          (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase(),
        ),
      }));
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
      this.selectedArtifacts = [];
      this.initializeSelectedArtifacts();
    },
    newComment() {
      this.warnDecision = false;
    },
  },
  mounted() {
    this.initializeSelectedArtifacts();
  },
  methods: {
    initializeSelectedArtifacts() {
      if (this.currentViewData.scanDecisions.length > 0) {
        const lastDecisionArtifacts = _.last(_.sortBy(
          this.currentViewData.scanDecisions, (dec) => dec.created,
        )).user_identified_artifacts;
        this.selectedArtifacts = Object.entries(lastDecisionArtifacts).filter(
          ([, selected]) => selected === 1,
        ).map(([artifactName]) => artifactName);
      } else if (this.currentViewData.currentAutoEvaluation) {
        this.selectedArtifacts = Object.entries(
          this.currentViewData.currentAutoEvaluation.results,
        ).map(
          ([artifactName, percentCertainty]) => {
            if (artifactName === 'full_brain_coverage') {
              return ['partial_brain_coverage', 1 - percentCertainty];
            } if (artifactName.includes('no_')) {
              return [artifactName.replace('no_', ''), 1 - percentCertainty];
            } return [artifactName, percentCertainty];
          },
        ).filter(
          ([artifactName, percentCertainty]) => percentCertainty > this.MIQAConfig.auto_artifact_threshold && artifactName !== 'overall_quality',
        ).map(([artifactName]) => artifactName);
      }
    },
    handleCommentChange(value) {
      this.newComment = value;
    },
    async handleCommentSave(decision) {
      if (this.newComment.trim().length > 0 || decision === 'U') {
        try {
          const { addScanDecision } = store.commit;
          const savedObj = await djangoRest.setDecision(
            this.currentViewData.scanId,
            decision,
            this.newComment,
            this.selectedArtifacts,
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
    <v-row>
      <v-col cols="12">
        <v-select
          v-model="selectedArtifacts"
          :items="artifactOptions"
          label="Select present artifacts"
          multiple
          clearable
          chips
          deletable-chips
          hint="Select artifacts present in this scan"
          persistent-hint
        />
      </v-col>
    </v-row>
    <v-row
      v-if="experimentIsEditable"
    >
      <v-col
        cols="12"
        class="pb-0 mb-0"
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
.v-list-item * {
  text-transform: capitalize!important;
}
</style>
