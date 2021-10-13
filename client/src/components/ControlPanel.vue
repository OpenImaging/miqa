<script>
import {
  mapState, mapGetters,
} from 'vuex';

export default {
  name: 'Dataset',
  components: {

  },
  inject: ['mainProject', 'user'],
  data: () => ({
    window: 256,
    level: 150,
  }),
  computed: {
    ...mapState([
      'proxyManager',
      'projectCachedPercentage',
    ]),
    ...mapGetters([
      'currentViewData',
      'previousExperiment',
      'nextExperiment',
      'nextDataset',
      'getDataset',
      'previousDataset',
      'currentDataset',
    ]),
    representation() {
      return this.currentDataset && this.proxyManager.getRepresentations()[0];
    },
    winMin() {
      return this.representation.getPropertyDomainByName('windowWidth').min;
    },
    winMax() {
      return this.representation.getPropertyDomainByName('windowWidth').max;
    },
    levMin() {
      return this.representation.getPropertyDomainByName('windowLevel').min;
    },
    levMax() {
      return this.representation.getPropertyDomainByName('windowLevel').max;
    },
  },
  watch: {
    window(value) {
      if (Number.isInteger(value)) {
        this.representation.setWindowWidth(value);
      }
    },
    level(value) {
      if (Number.isInteger(value)) {
        this.representation.setWindowLevel(value);
      }
    },
    currentDataset() {
      this.representation.setWindowWidth(this.window);
      this.representation.setWindowLevel(this.level);
    },
  },
  mounted() {
    this.representation.setWindowWidth(this.window);
    this.representation.setWindowLevel(this.level);
    window.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowUp') {
        this.handleKeyPress('previous');
      } else if (event.key === 'ArrowDown') {
        this.handleKeyPress('next');
      } else if (event.key === 'ArrowLeft') {
        this.handleKeyPress('back');
      } else if (event.key === 'ArrowRight') {
        this.handleKeyPress('forward');
      }
    });
  },
  methods: {
    updateImage() {
      if (this.direction === 'back') {
        this.$router
          .push(this.previousDataset ? this.previousDataset : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'forward') {
        this.$router
          .push(this.nextDataset ? this.nextDataset : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'previous') {
        this.$router
          .push(this.previousExperiment ? this.previousExperiment : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'next') {
        this.$router
          .push(this.nextExperiment ? this.nextExperiment : '')
          .catch(this.handleNavigationError);
      }
    },
    handleKeyPress(direction) {
      this.direction = direction;
      this.updateImage();
    },
  },
};
</script>

<template>
  <v-flex
    shrink
    class="bottom"
  >
    <v-container
      fluid
      class="pa-0"
    >
      <v-row no-gutters>
        <v-col
          cols="4"
          class="pa-2 pr-1"
        >
          <v-card
            height="100%"
            elevation="3"
          >
            <v-container fluid>
              <v-row dense>
                <v-col cols="6">
                  Project
                </v-col>
                <v-col
                  cols="6"
                  class="grey--text"
                  style="text-align: right"
                >
                  {{ currentViewData.projectName }}
                </v-col>
              </v-row>
              <v-row dense>
                <v-col cols="6">
                  Experiment
                </v-col>
                <v-col
                  cols="6"
                  class="grey--text"
                  style="text-align: right"
                >
                  <!-- Inline user avatar of lock owner goes here -->
                  {{ currentViewData.experimentName }}
                </v-col>
              </v-row>
              <v-row
                class="ma-2"
                style="height: 99%"
              >
                <v-col
                  cols="12"
                  class="grey lighten-2"
                  style="height: 100px; overflow:auto"
                >
                  {{ currentViewData.experimentNote ?
                    currentViewData.experimentNote : "There are no notes on this experiment." }}
                </v-col>
              </v-row>
              <v-row no-gutters>
                <v-col
                  style="text-align: right"
                  class="grey--text"
                >
                  Save Note
                </v-col>
              </v-row>
            </v-container>
          </v-card>
        </v-col>
        <v-col
          cols="8"
          class="pa-2 pl-1"
        >
          <v-card
            height="100%"
            elevation="3"
          >
            <v-container
              fluid
              class="pa-0"
            >
              <v-row no-gutters>
                <v-col cols="6">
                  <v-container
                    fill-height
                    fluid
                  >
                    <v-row no-gutters>
                      <v-col cols="3">
                        Scan
                      </v-col>
                      <v-col
                        cols="6"
                        class="grey--text"
                        style="text-align: center"
                      >
                        <div
                          class="font-weight-bold"
                          style="display:inline"
                        >
                          {{ currentViewData.scanName }}
                        </div>
                        {{ currentViewData.scanPositionString }}
                      </v-col>
                      <v-col
                        cols="3"
                        style="text-align: right"
                      >
                        <v-btn
                          :disabled="!previousExperiment"
                          @mousedown="handleKeyPress('previous')"
                          small
                          depressed
                          color="white"
                        >
                          <v-icon>fa-caret-up</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!nextExperiment"
                          @mousedown="handleKeyPress('next')"
                          small
                          depressed
                          color="white"
                        >
                          <v-icon>fa-caret-down</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-col cols="3">
                        Frame
                      </v-col>
                      <v-col
                        cols="6"
                        class="grey--text"
                        style="text-align: center"
                      >
                        {{ currentViewData.framePositionString }}
                      </v-col>
                      <v-col
                        cols="3"
                        style="text-align: right"
                      >
                        <v-btn
                          :disabled="!previousDataset"
                          @mousedown="handleKeyPress('back')"
                          small
                          depressed
                        >
                          <v-icon>fa-caret-left</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!nextDataset"
                          @mousedown="handleKeyPress('forward')"
                          small
                          depressed
                        >
                          <v-icon>fa-caret-right</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>
                    <v-row
                      no-gutters
                      fill-height
                      align="center"
                    >
                      <v-col
                        cols="4"
                      >
                        Window width
                        <v-tooltip bottom>
                          <template v-slot:activator="{ on, attrs }">
                            <v-icon
                              v-bind="attrs"
                              v-on="on"
                              small
                            >
                              info
                            </v-icon>
                          </template>
                          <span>
                            The measure of the range of CT numbers that an image contains.
                            A significantly wide window displaying all the CT numbers will
                            obscure different attenuations between soft tissues.
                          </span>
                        </v-tooltip>
                      </v-col>
                      <v-col
                        cols="8"
                        style="text-align: center"
                      >
                        <v-slider
                          v-model="window"
                          :max="winMax"
                          :min="winMin"
                          class="align-center"
                          hide-details
                        >
                          <template v-slot:prepend>
                            {{ winMin }}
                          </template>
                          <template v-slot:append>
                            <div class="pr-5 pt-2">
                              {{ winMax }}
                            </div>
                            <v-text-field
                              v-model="window"
                              class="mt-0 pt-0"
                              hide-details
                              single-line
                              type="number"
                              style="width: 60px"
                            />
                          </template>
                        </v-slider>
                      </v-col>
                    </v-row>
                    <v-row
                      no-gutters
                      fill-height
                      align="center"
                    >
                      <v-col cols="4">
                        Window level
                        <v-tooltip bottom>
                          <template v-slot:activator="{ on, attrs }">
                            <v-icon
                              v-bind="attrs"
                              v-on="on"
                              small
                            >
                              info
                            </v-icon>
                          </template>
                          <span>
                            The midpoint of the range of the CT numbers displayed.
                            When the window level is decreased the CT image will be brighter.
                          </span>
                        </v-tooltip>
                      </v-col>
                      <v-col
                        cols="8"
                        style="text-align: center"
                      >
                        <v-slider
                          v-model="level"
                          :max="levMax"
                          :min="levMin"
                          class="align-center"
                          hide-details
                        >
                          <template v-slot:prepend>
                            {{ levMin }}
                          </template>
                          <template v-slot:append>
                            <div class="pr-5 pt-2">
                              {{ levMax }}
                            </div>
                            <v-text-field
                              v-model="level"
                              class="mt-0 pt-0"
                              hide-details
                              single-line
                              type="number"
                              style="width: 60px"
                            />
                          </template>
                        </v-slider>
                      </v-col>
                    </v-row>
                    <v-row class="py-3">
                      <v-col
                        cols="12"
                        style="text-align: center; height: 70px"
                      >
                        <transition name="bounce">
                          <div v-if="projectCachedPercentage < 1">
                            <v-progress-circular
                              :value="projectCachedPercentage * 100"
                              color="blue"
                            />
                            <div> Loading... </div>
                          </div>
                        </transition>
                      </v-col>
                    </v-row>
                  </v-container>
                </v-col>
                <v-col cols="6">
                  <v-container
                    fluid
                    class="px-5"
                  >
                    <v-row>
                      <v-col
                        cols="12"
                        class="grey lighten-4"
                        style="height: 80px; overflow:auto"
                      >
                        comments section
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col cols="6">
                        Automatic Evaluation
                        <v-tooltip bottom>
                          <template v-slot:activator="{ on, attrs }">
                            <v-icon
                              v-bind="attrs"
                              v-on="on"
                              small
                            >
                              info
                            </v-icon>
                          </template>
                          <span>
                            An evaluation performed by a computer, using artificial intelligence
                            or classic image processing algorithms
                          </span>
                        </v-tooltip>
                      </v-col>
                      <v-col
                        cols="6"
                        class="font-weight-bold orange--text"
                        style="text-align: right"
                      >
                        <v-tooltip
                          left
                          color="rgba(0,0,0,0)"
                        >
                          <template v-slot:activator="{ on, attrs }">
                            <div
                              v-bind="attrs"
                              v-on="on"
                            >
                              Percentage
                              <v-img
                                class="float-right ml-3"
                                src="evaluation-details.png"
                                height="20"
                                width="20"
                              />
                            </div>
                          </template>
                          <v-card class="pa-5">
                            Lots of text in here
                          </v-card>
                        </v-tooltip>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col
                        cols="12"
                        class="grey lighten-2"
                        style="height: 80px; overflow:auto"
                      >
                        evaluation section
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-col
                        cols="4"
                        style="text-align: center"
                      >
                        GOOD
                      </v-col>
                      <v-col
                        cols="4"
                        style="text-align: center"
                      >
                        BAD
                      </v-col>
                      <v-col
                        cols="4"
                        style="text-align: center"
                      >
                        OTHER
                      </v-col>
                    </v-row>
                  </v-container>
                </v-col>
              </v-row>
            </v-container>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-flex>
</template>

<style lang="scss" scoped>

.theme--light.v-btn.v-btn--disabled:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.theme--light.v-btn:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.v-btn::before {
  background-color: transparent !important;
}

.bounce-enter-active {
  animation: bounce-in .5s;
}
.bounce-leave-active {
  animation: bounce-in .5s reverse;
}
@keyframes bounce-in {
  0% {
    transform: scale(0);
  }
  50% {
    transform: scale(1.5);
  }
  100% {
    transform: scale(1);
  }
}

</style>
