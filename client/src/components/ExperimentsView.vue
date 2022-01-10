<script>
import _ from 'lodash';
import { mapState, mapGetters, mapMutations } from 'vuex';
import UserAvatar from '@/components/UserAvatar.vue';
import { API_URL } from '../constants';

export default {
  name: 'ExperimentsView',
  components: { UserAvatar },
  props: {
    minimal: {
      type: Boolean,
      default: false,
    },
  },
  inject: ['user'],
  data: () => ({
    API_URL,
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
      'currentProject',
    ]),
    ...mapGetters(['currentScan', 'currentExperiment']),
    orderedExperiments() {
      const allExperiments = this.experiments;
      return this.experimentIds.map((expId) => allExperiments[expId]);
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
  methods: {
    ...mapMutations([
      'switchReviewMode',
    ]),
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
    getURLForFirstFrameInScan(scanId) {
      return `${this.currentProject.id}/${this.scanFrames[scanId][0]}`;
    },
    decisionToRating(decisions) {
      if (decisions.length === 0) return {};
      const rating = _.last(_.sortBy(decisions, (dec) => dec.created)).decision;
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
  },
};
</script>

<template>
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
              {{ experiment.name }}
              <UserAvatar
                :target-user="experiment.lock_owner"
                as-editor
              />
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
              :class="{
                current: scan === currentScan
              }"
              class="body-1"
            >
              <v-btn
                :to="getURLForFirstFrameInScan(scan.id)"
                class="ml-0 px-1 scan-name"
                href
                text
                small
                active-class=""
              >
                {{ scan.name }}
                <span
                  v-if="scan.decisions.length !== 0"
                  :class="scan.color + ' pl-3'"
                  small
                >({{ scan.decision }})</span>
              </v-btn>
            </li>
          </ul>
        </li>
      </ul>
    </div>
    <div
      v-else
      class="pa-5"
      style="width: max-content"
    >
      <span class="px-5">No imported data.</span>
    </div>
    <div
      class="mode-toggle"
    >
      All scans
      <v-switch
        @change="switchReviewMode"
        :value="reviewMode"
        inset
        dense
        style="display: inline-block; max-height: 40px; max-width: 60px"
        class="px-3 ma-0"
      />
      Scans for my review
    </div>
  </div>
</template>

<style lang="scss" scoped>
.current {
  background: rgb(206, 206, 206);
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
</style>

<style lang="scss">
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
  padding: 0px 20px;
  display: block;
  min-width: 350px;
  height: min-content;
}
</style>
