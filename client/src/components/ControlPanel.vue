<script>
import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import djangoRest from '@/django';
import store from '@/store';

import EvaluationResults from './EvaluationResults.vue';
import UserAvatar from './UserAvatar.vue';
import ScanDecision from './ScanDecision.vue';
import DecisionButtons from './DecisionButtons.vue';

export default {
  name: 'Frame',
  components: {
    EvaluationResults,
    UserAvatar,
    ScanDecision,
    DecisionButtons,
  },
  inject: ['user'],
  data: () => ({
    window: 256,
    level: 150,
    newExperimentNote: '',
  }),
  computed: {
    ...mapState([
      'proxyManager',
      'scanCachedPercentage',
      'showCrosshairs',
      'myCurrentProjectRoles',
    ]),
    ...mapGetters([
      'currentViewData',
      'nextFrame',
      'getFrame',
      'previousFrame',
      'currentFrame',
      'myCurrentProjectRoles',
    ]),
    ...mapMutations([
      'updateExperiment',
      'addScanDecision',
      'setExperimentAutoWindow',
      'setExperimentAutoLevel',
    ]),
    experimentId() {
      return this.currentViewData.experimentId;
    },
    experimentIsEditable() {
      return this.lockOwner && this.lockOwner.id === this.user.id;
    },
    lockOwner() {
      return this.currentViewData.lockOwner;
    },
    representation() {
      return this.currentFrame && this.proxyManager.getRepresentations()[0];
    },
    winMin() {
      return (this.representation && this.representation.getPropertyDomainByName('windowWidth').min) || 0;
    },
    winMax() {
      return (this.representation && Math.ceil(this.representation.getPropertyDomainByName('windowWidth').max)) || 0;
    },
    autoWindow() {
      return this.currentViewData.autoWindow
        || Math.ceil((this.winMax * 0.3) / 10) * 10;
    },
    levMin() {
      return (this.representation && this.representation.getPropertyDomainByName('windowLevel').min) || 0;
    },
    levMax() {
      return (this.representation && Math.ceil(this.representation.getPropertyDomainByName('windowLevel').max)) || 0;
    },
    autoLevel() {
      return this.currentViewData.autoLevel
        || Math.ceil((this.levMax * 0.2) / 10) * 10;
    },
  },
  watch: {
    window(value) {
      if (Number.isInteger(value) && value !== this.autoWindow) {
        const { setExperimentAutoWindow } = store.commit;
        setExperimentAutoWindow({ experimentId: this.experimentId, autoWindow: value });
        this.representation.setWindowWidth(value);
      }
    },
    level(value) {
      if (Number.isInteger(value) && value !== this.autoLevel) {
        const { setExperimentAutoLevel } = store.commit;
        setExperimentAutoLevel({ experimentId: this.experimentId, autoLevel: value });
        this.representation.setWindowLevel(value);
      }
    },
    currentFrame() {
      this.updateWinLev();
    },
    experimentId(newValue, oldValue) {
      this.switchLock(newValue, oldValue);
    },
  },
  mounted() {
    this.switchLock(this.experimentId);
    this.updateWinLev();
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
  beforeDestroy() {
    this.setLock({ experimentId: this.experimentId, lock: false });
  },
  methods: {
    ...mapActions([
      'setLock',
    ]),
    ...mapMutations([
      'setShowCrosshairs',
    ]),
    async switchLock(newExp, oldExp = null) {
      if (this.myCurrentProjectRoles.includes('tier_1_reviewer')
      || this.myCurrentProjectRoles.includes('tier_2_reviewer')
      || this.myCurrentProjectRoles.includes('superuser')) {
        if (oldExp) {
          try {
            await this.setLock({ experimentId: oldExp, lock: false });
          } catch (err) {
            console.log(err);
            this.$snackbar({
              text: 'Failed to release edit access on Experiment.',
              timeout: 6000,
            });
          }
        }
        try {
          await this.setLock({ experimentId: newExp, lock: true });
        } catch (err) {
          console.log(err);
          this.$snackbar({
            text: 'Failed to claim edit access on Experiment.',
            timeout: 6000,
          });
        }
      }
    },
    updateWinLev() {
      this.window = this.autoWindow;
      this.level = this.autoLevel;
    },
    updateImage() {
      if (this.direction === 'back') {
        this.$router
          .push(this.previousFrame ? this.previousFrame : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'forward') {
        this.$router
          .push(this.nextFrame ? this.nextFrame : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'previous') {
        this.$router
          .push(this.currentViewData.upTo ? this.currentViewData.upTo : '')
          .catch(this.handleNavigationError);
      } else if (this.direction === 'next') {
        this.$router
          .push(this.currentViewData.downTo ? this.currentViewData.downTo : '')
          .catch(this.handleNavigationError);
      }
    },
    handleKeyPress(direction) {
      this.direction = direction;
      this.updateImage();
    },
    handleExperimentNoteChange(value) {
      this.newExperimentNote = value;
    },
    async handleExperimentNoteSave() {
      if (this.newExperimentNote.length > 0) {
        try {
          const { updateExperiment } = store.commit;
          const newExpData = await djangoRest.setExperimentNote(
            this.currentViewData.experimentId, this.newExperimentNote,
          );
          this.$snackbar({
            text: 'Saved note successfully.',
            timeout: 6000,
          });
          this.newExperimentNote = '';
          updateExperiment(newExpData);
        } catch (err) {
          this.$snackbar({
            text: `Save failed: ${err.response.data.detail || 'Server error'}`,
            timeout: 6000,
          });
        }
      }
    },
  },
};
</script>

<template>
  <v-flex
    v-if="representation"
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
                  <UserAvatar
                    :target-user="lockOwner"
                    as-editor
                  />
                  {{ currentViewData.experimentName }}
                </v-col>
              </v-row>

              <v-textarea
                v-model="currentViewData.experimentNote"
                @input="handleExperimentNoteChange"
                :disabled="!experimentIsEditable"
                filled
                no-resize
                height="120px"
                hide-details
                class="mt-3"
                name="input-experiment-notes"
                label="Experiment Notes"
                placeholder="There are no notes on this experiment."
              />

              <v-row no-gutters>
                <v-col
                  v-on:click="handleExperimentNoteSave()"
                  :class="newExperimentNote.length > 0 ? 'blue--text' : 'grey--text'"
                  style="text-align: right"
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
                <v-col cols="5">
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
                          :disabled="!currentViewData.upTo"
                          @mousedown="handleKeyPress('previous')"
                          small
                          depressed
                          class="transparent-btn"
                        >
                          <v-icon>fa-caret-up</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!currentViewData.downTo"
                          @mousedown="handleKeyPress('next')"
                          small
                          depressed
                          class="transparent-btn"
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
                          :disabled="!previousFrame"
                          @mousedown="handleKeyPress('back')"
                          small
                          depressed
                          class="transparent-btn"
                        >
                          <v-icon>fa-caret-left</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!nextFrame"
                          @mousedown="handleKeyPress('forward')"
                          small
                          depressed
                          class="transparent-btn"
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
                    <v-row>
                      <v-col cols="4">
                        Display crosshairs
                      </v-col>
                      <v-col cols="8">
                        <v-switch
                          :input-value="showCrosshairs"
                          @change="setShowCrosshairs"
                          hide-details
                          class="shrink ma-0 pa-0 ml-n2"
                        />
                      </v-col>
                    </v-row>
                    <v-row class="py-3">
                      <v-col
                        cols="12"
                        style="text-align: center; height: 70px"
                      >
                        <transition name="bounce">
                          <div v-if="scanCachedPercentage < 1">
                            <v-progress-circular
                              :value="scanCachedPercentage * 100"
                              color="blue"
                            />
                            <div> Loading... </div>
                          </div>
                        </transition>
                      </v-col>
                    </v-row>
                  </v-container>
                </v-col>
                <v-col cols="7">
                  <v-container
                    fluid
                    class="px-5"
                  >
                    <v-row>
                      <v-col cols="12">
                        <v-container
                          class="grey lighten-4"
                          style="height: 100px; overflow:auto;"
                        >
                          <ScanDecision
                            v-for="decision in currentViewData.scanDecisions"
                            :key="decision.id"
                            :decision="decision"
                          />
                          <div
                            v-if="currentViewData.scanDecisions.length === 0"
                            class="grey--text"
                          >
                            This scan has no prior comments.
                          </div>
                        </v-container>
                      </v-col>
                    </v-row>
                    <v-row v-if="currentViewData.currentAutoEvaluation">
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
                            An evaluation performed by the MIQA server using artificial intelligence
                          </span>
                        </v-tooltip>
                      </v-col>
                      <EvaluationResults
                        :results="currentViewData.currentAutoEvaluation.results"
                      />
                    </v-row>
                    <DecisionButtons
                      :experimentIsEditable="experimentIsEditable"
                      @handleKeyPress="handleKeyPress"
                    />
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
.transparent-btn.v-btn--disabled, .transparent-btn.v-btn--disabled::before,
.transparent-btn, .transparent-btn::before,
.theme--light.v-btn.v-btn--disabled:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined) {
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
