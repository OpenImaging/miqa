<script>
import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import djangoRest from '@/django';
import store from '@/store';

import UserAvatar from './UserAvatar.vue';
import ScanDecision from './ScanDecision.vue';
import DecisionButtons from './DecisionButtons.vue';
import WindowWidget from './WindowWidget.vue';

export default {
  name: 'Frame',
  components: {
    UserAvatar,
    ScanDecision,
    DecisionButtons,
    WindowWidget,
  },
  inject: ['user'],
  data: () => ({
    newExperimentNote: '',
    loadingLock: undefined,
  }),
  computed: {
    ...mapState([
      'proxyManager',
      'scanCachedPercentage',
      'showCrosshairs',
      'storeCrosshairs',
    ]),
    ...mapGetters([
      'currentViewData',
      'nextFrame',
      'previousFrame',
      'currentFrame',
      'myCurrentProjectRoles',
    ]),
    ...mapMutations([
      'updateExperiment',
      'addScanDecision',
    ]),
    experimentId() {
      return this.currentViewData.experimentId;
    },
    editRights() {
      return this.myCurrentProjectRoles.includes('tier_1_reviewer')
      || this.myCurrentProjectRoles.includes('tier_2_reviewer')
      || this.myCurrentProjectRoles.includes('superuser');
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
  },
  watch: {
    experimentId(newValue, oldValue) {
      this.switchLock(newValue, oldValue);
      clearInterval(this.lockCycle);
    },
    currentViewData() {
      this.navigateToNextIfCurrentScanNull();
    },
  },
  mounted() {
    if (!this.navigateToNextIfCurrentScanNull()) {
      this.switchLock(this.experimentId);
      window.addEventListener('keydown', (event) => {
        if (['textarea', 'input'].includes(document.activeElement.type)) return;
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
    }
  },
  beforeDestroy() {
    this.setLock({ experimentId: this.experimentId, lock: false });
    clearInterval(this.lockCycle);
  },
  methods: {
    ...mapActions([
      'setLock',
    ]),
    ...mapMutations([
      'setShowCrosshairs',
      'setStoreCrosshairs',
    ]),
    openScanLink() {
      window.open(this.currentViewData.scanLink, '_blank');
    },
    async switchLock(newExp, oldExp = null, force = false) {
      if (!this.navigateToNextIfCurrentScanNull()) {
        if (this.editRights) {
          this.loadingLock = true;
          if (oldExp) {
            try {
              await this.setLock({ experimentId: oldExp, lock: false, force });
            } catch (err) {
              this.$snackbar({
                text: 'Failed to release edit access on Experiment.',
                timeout: 6000,
              });
            }
          }
          try {
            await this.setLock({ experimentId: newExp, lock: true, force });
            this.lockCycle = setInterval(async (experimentId) => {
              await this.setLock({ experimentId, lock: true });
            }, 1000 * 60 * 5, this.currentViewData.experimentId);
          } catch (err) {
            this.$snackbar({
              text: 'Failed to claim edit access on Experiment.',
              timeout: 6000,
            });
            this.loadingLock = false;
          }
        }
      }
    },
    navigateToFrame(frameId) {
      if (frameId && frameId !== this.$route.params.frameId) {
        this.$router
          .push(`/${this.currentViewData.projectId}/${frameId}` || '')
          .catch(this.handleNavigationError);
      }
    },
    updateImage() {
      if (this.direction === 'back') {
        this.navigateToFrame(this.previousFrame);
      } else if (this.direction === 'forward') {
        this.navigateToFrame(this.nextFrame);
      } else if (this.direction === 'previous') {
        this.navigateToFrame(this.currentViewData.upTo);
      } else if (this.direction === 'next') {
        this.navigateToFrame(this.currentViewData.downTo);
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
    navigateToNextIfCurrentScanNull() {
      if (Object.keys(this.currentViewData).length < 2) {
        this.handleKeyPress('next');
        return true;
      }
      return false;
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
            <div class="d-flex">
              <div
                class="d-flex px-5 py-3"
                style="flex-direction: column; flex-grow: 3"
              >
                <div class="current-info-container">
                  <div>
                    Project:
                  </div>
                  <div>
                    {{ currentViewData.projectName }}
                  </div>
                </div>
                <div class="current-info-container">
                  <div>
                    Experiment:
                  </div>
                  <div>
                    {{ currentViewData.experimentName }}
                    <UserAvatar
                      v-if="lockOwner"
                      :target-user="lockOwner"
                      as-editor
                    />
                  </div>
                </div>
                <div class="current-info-container">
                  <div>
                    Subject:
                  </div>
                  <div>
                    <b>{{ currentViewData.scanSubject || 'None' }}</b>
                  </div>
                </div>
                <div class="current-info-container">
                  <div>
                    Session:
                  </div>
                  <div>
                    <b>{{ currentViewData.scanSession || 'None' }}</b>
                  </div>
                </div>
              </div>
              <div
                v-if="scanCachedPercentage < 1 && scanCachedPercentage > 0"
                class="px-6 py-8"
                style="text-align: center"
              >
                <v-progress-circular
                  :value="scanCachedPercentage * 100"
                  color="blue"
                />
                <div> Loading... </div>
              </div>
            </div>
            <v-textarea
              v-model="currentViewData.experimentNote"
              filled
              :disabled="!experimentIsEditable"
              no-resize
              height="60px"
              hide-details
              name="input-experiment-notes"
              label="Experiment Notes"
              placeholder="There are no notes on this experiment."
              class="ma-3"
              @input="handleExperimentNoteChange"
            />
            <v-row no-gutters>
              <v-col
                :class="newExperimentNote.length > 0 ? 'blue--text' : 'grey--text'"
                class="px-3 text-right"
                @click="handleExperimentNoteSave()"
              >
                Save Note
              </v-col>
            </v-row>
            <v-flex
              class="d-flex ml-5"
              style="flex-direction:row"
            >
              <div style="flex-grow: 1">
                <v-switch
                  :input-value="showCrosshairs"
                  label="Display crosshairs"
                  hide-details
                  class="shrink pa-0 ml-n2"
                  @change="setShowCrosshairs"
                />
              </div>
              <div style="flex-grow: 1">
                <v-switch
                  :input-value="storeCrosshairs"
                  label="Store crosshairs with decision"
                  hide-details
                  class="shrink pa-0 ml-n2"
                  @change="setStoreCrosshairs"
                />
              </div>
            </v-flex>
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
                      <v-col cols="2">
                        Scan:
                      </v-col>
                      <v-col
                        cols="6"
                        class="grey--text"
                      >
                        <div
                          :class="currentViewData.scanLink ? 'link' : ''"
                          style="display:inline"
                          @click="openScanLink"
                        >
                          <b>{{ currentViewData.scanName }}</b>
                        </div>
                        {{ currentViewData.scanPositionString }}
                      </v-col>
                      <v-col
                        cols="4"
                        class="text-right"
                      >
                        <v-btn
                          :disabled="!currentViewData.upTo"
                          small
                          depressed
                          class="transparent-btn"
                          @mousedown="handleKeyPress('previous')"
                        >
                          <v-icon>fa-caret-up</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!currentViewData.downTo"
                          small
                          depressed
                          class="transparent-btn"
                          @mousedown="handleKeyPress('next')"
                        >
                          <v-icon>fa-caret-down</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>
                    <v-row no-gutters>
                      <v-col cols="2">
                        Frame:
                      </v-col>
                      <v-col
                        cols="6"
                        class="grey--text"
                      >
                        {{ currentViewData.framePositionString }}
                      </v-col>
                      <v-col
                        cols="4"
                        class="text-right"
                      >
                        <v-btn
                          :disabled="!previousFrame"
                          small
                          depressed
                          class="transparent-btn"
                          @mousedown="handleKeyPress('back')"
                        >
                          <v-icon>fa-caret-left</v-icon>
                        </v-btn>
                        <v-btn
                          :disabled="!nextFrame"
                          small
                          depressed
                          class="transparent-btn"
                          @mousedown="handleKeyPress('forward')"
                        >
                          <v-icon>fa-caret-right</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>

                    <window-widget
                      :representation="representation"
                      :experiment-id="experimentId"
                    />

                    <v-row class="mx-0">
                      <v-col
                        cols="12"
                        class="grey lighten-4"
                        style="height: 100px; overflow:auto; margin-bottom: 10px"
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
                      </v-col>
                    </v-row>
                  </v-container>
                </v-col>
                <v-col cols="6">
                  <DecisionButtons
                    :experiment-is-editable="experimentIsEditable"
                    :edit-rights="editRights"
                    :lock-owner="lockOwner"
                    :loading-lock="loadingLock"
                    @handleKeyPress="handleKeyPress"
                    @switchLock="switchLock"
                  />
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

.link {
  color: #1976d2;
  text-decoration: underline;
  cursor: pointer;
}

.current-info-container {
  display: flex;
  column-gap: 10px;
}
</style>
