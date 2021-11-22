<script>
import { mapGetters } from 'vuex';
import djangoRest from '@/django';
import store from '@/store';

export default {
  name: 'DecisionButtons',
  inject: ['user'],
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
    };
  },
  computed: {
    ...mapGetters([
      'currentViewData',
      'myCurrentProjectRoles',
    ]),
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
    newComment() {
      this.warnDecision = false;
    },
  },
  methods: {
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
</style>
