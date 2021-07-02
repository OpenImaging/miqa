<script>
import _ from 'lodash';
import { mapState, mapGetters } from 'vuex';
import { API_URL } from '../constants';

export default {
  name: 'SessionsView',
  components: {},
  props: {
    minimal: {
      type: Boolean,
      default: false,
    },
  },
  data: () => ({
    API_URL,
  }),
  computed: {
    ...mapState([
      'experiments',
      'experimentIds',
      'experimentSessions',
      'loadingExperiment',
      'sessions',
      'sessionDatasets',
      'datasets',
    ]),
    ...mapGetters(['currentSession', 'currentExperiment']),
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
    sessionsForExperiment(expId) {
      const expSessionIds = this.experimentSessions[expId];
      return expSessionIds.map((sessionId) => {
        const scan = this.sessions[sessionId];
        return {
          ...scan,
          ...this.decisionToRating(scan.decisions),
        };
      });
    },
    getIdOfFirstDatasetInSession(sessionId) {
      return `${this.sessionDatasets[sessionId][0]}`;
    },
    decisionToRating(decisions) {
      if (decisions.length === 0) return {};
      const rating = _.last(decisions).decision.toLowerCase();
      switch (rating) {
        case 'good':
          return {
            decision: 'G',
            css: 'green--text',
          };
        case 'usable_extra':
          return {
            decision: 'E',
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
  <div class="sessions-view">
    <ul
      v-if="orderedExperiments && orderedExperiments.length"
      class="experiment"
    >
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
            v-for="session of sessionsForExperiment(experiment.id)"
            :key="`s.${session.id}`"
            class="body-1"
            :class="{
              current: session === currentSession
            }"
          >
            <v-btn
              class="ml-0 px-1 scan-name"
              href
              text
              small
              :to="getIdOfFirstDatasetInSession(session.id)"
              active-class=""
            >
              {{ session.name }}
              <span
                v-if="session.decisions.length !== 0"
                :class="session.css"
                small
              >&nbsp;&nbsp;({{ session.decision }})</span>
            </v-btn>
          </li>
        </ul>
      </li>
    </ul>
    <div
      v-else
      class="text-xs-center body-2"
    >
      No imported sessions
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
.sessions-view .scan-name .v-btn__content {
  text-transform: none;
}
</style>
