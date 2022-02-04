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
      'currentTaskOverview',
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
      return `/${this.currentProject.id}/${this.scanFrames[scanId][0]}`;
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
    scanIsCurrent(scan) {
      if (scan === this.currentScan) {
        return ' current';
      }
      return '';
    },
    scanState(scan) {
      let state;
      if (this.currentTaskOverview) {
        state = this.currentTaskOverview.scan_states[scan.id];
      }
      return state || 'unreviewed';
    },
    scanStateClass(scan) {
      let classes = `body-1 state-${this.scanState(scan).replace(/ /g, '-')}`;
      if (scan === this.currentScan) {
        classes = `${classes} current`;
      }
      return classes;
    },
  },
};
</script>

<template>
  <v-card class="flex-card">
    <v-subheader
      class="d-flex"
      style="justify-content: space-between"
    >
      Experiments
      <div
        class="d-flex mode-toggle"
      >
        <span>All scans</span>
        <v-switch
          @change="switchReviewMode"
          :value="reviewMode"
          inset
          dense
          style="display: inline-block; max-height: 40px; max-width: 60px;"
          class="px-3 ma-0"
        />
        <span>Scans for my review</span>
      </div>
    </v-subheader>
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
                :class="scanStateClass(scan)"
              >
                <v-tooltip right>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn
                      v-bind="attrs"
                      v-on="on"
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
                  </template>
                  <span>
                    {{ scanState(scan) }}
                  </span>
                </v-tooltip>
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
  align-items: baseline;
}
</style>
