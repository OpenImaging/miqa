<script>
import _ from 'lodash';
import { mapState, mapGetters } from 'vuex';
import UserAvatar from '@/components/UserAvatar.vue';
import DataImportExport from '@/components/DataImportExport.vue';
import { API_URL } from '../constants';

export default {
  name: 'ExperimentsView',
  components: { UserAvatar, DataImportExport },
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
      'experiments',
      'experimentIds',
      'experimentScans',
      'loadingExperiment',
      'scans',
      'scanFrames',
      'frames',
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
    scansForExperiment(expId) {
      const expScanIds = this.experimentScans[expId];
      return expScanIds.map((scanId) => {
        const scan = this.scans[scanId];
        return {
          ...scan,
          ...this.decisionToRating(scan.decisions),
        };
      });
    },
    getIdOfFirstFrameInScan(scanId) {
      return `${this.scanFrames[scanId][0]}`;
    },
    decisionToRating(decisions) {
      if (decisions.length === 0) return {};
      const rating = _.last(_.sortBy(decisions, (dec) => dec.created)).decision.toLowerCase();
      switch (rating) {
        case 'good':
          return {
            decision: 'G',
            css: 'green--text',
          };
        case 'other':
          return {
            decision: 'O',
            css: 'blue--text',
          };
        case 'bad':
          return {
            decision: 'B',
            css: 'red--text',
          };
        default: // caught be malformed decisions
          return {
            decision: '?',
            css: 'black--text',
          };
      }
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
          class="body-2"
        >
          <v-card
            flat
            class="d-flex justify-space-between pr-2"
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
                :to="getIdOfFirstFrameInScan(scan.id)"
                class="ml-0 px-1 scan-name"
                href
                text
                small
                active-class=""
              >
                {{ scan.name }}
                <span
                  v-if="scan.decisions.length !== 0"
                  :class="scan.css"
                  small
                >&nbsp;&nbsp;({{ scan.decision }})</span>
              </v-btn>
            </li>
          </ul>
        </li>
      </ul>
      <DataImportExport />
    </div>
    <div
      v-else
      class="pa-5"
    >
      <span class="px-5">No imported data.</span>
      <DataImportExport import-only />
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
.scans-view .scan-name .v-btn__content {
  text-transform: none;
}
</style>
