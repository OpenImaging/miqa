<script lang="ts">
import {
  defineComponent,
  computed,
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
} from 'vue';
import router from '@/router';
import store from '@/store';
import djangoRest from '@/django';
import UserAvatar from './UserAvatar.vue';
import ScanDecision from './ScanDecision.vue';
import DecisionButtons from './DecisionButtons.vue';
import WindowWidget from './WindowWidget.vue';

export default defineComponent({
  name: 'ControlPanel',
  components: {
    UserAvatar,
    ScanDecision,
    DecisionButtons,
    WindowWidget,
  },
  setup() {
    const newExperimentNote = ref('');
    const loadingLock = ref();
    const lockCycle = ref();
    const direction = ref();

    const user = computed(() => store.state.me);
    const proxyManager = computed(() => store.state.proxyManager);
    const scanCachedPercentage = computed(() => store.state.scanCachedPercentage);
    const showCrosshairs = computed(() => store.state.showCrosshairs);
    const storeCrosshairs = computed(() => store.state.storeCrosshairs);

    const currentViewData = computed(() => store.getters.currentViewData);
    const nextFrame = computed(() => store.getters.nextFrame);
    const previousFrame = computed(() => store.getters.previousFrame);
    const currentFrame = computed(() => store.getters.currentFrame);
    const myCurrentProjectRoles = computed(() => store.getters.myCurrentProjectRoles);

    const setLock = (lockParameters) => store.dispatch('setLock', lockParameters);
    const setCurrentFrameId = (frameId) => store.commit('SET_CURRENT_FRAME_ID', frameId);
    const setShowCrosshairs = (show) => store.commit('SET_SHOW_CROSSHAIRS', show);
    const setStoreCrosshairs = (persist) => store.commit('SET_STORE_CROSSHAIRS', persist);
    const updateExperiment = (experiment) => store.commit('UPDATE_EXPERIMENT', experiment);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);

    const experimentId = computed(() => currentViewData.value.experimentId);
    const editRights = computed(() => myCurrentProjectRoles.value.includes('tier_1_reviewer')
      || myCurrentProjectRoles.value.includes('tier_2_reviewer')
      || myCurrentProjectRoles.value.includes('superuser'));
    const lockOwner = computed(() => currentViewData.value.lockOwner);
    const experimentIsEditable = computed(
      () => lockOwner.value && lockOwner.value.id === user.value.id,
    );
    const representation = computed(
      () => currentFrame.value && proxyManager.value.getRepresentations()[0],
    );

    function openScanLink() {
      window.open(currentViewData.value.scanLink, '_blank');
    }
    function navigateToScan(location) {
      if (!location) location = 'complete';
      if (location && location !== router.app.$route.params.scanId) {
        router.push(`/${currentViewData.value.projectId}/${location}` || '');
      }
    }
    function updateImage() {
      if (direction.value === 'back') {
        setCurrentFrameId(previousFrame.value);
      } else if (direction.value === 'forward') {
        setCurrentFrameId(nextFrame.value);
      } else if (direction.value === 'previous') {
        navigateToScan(currentViewData.value.upTo);
      } else if (direction.value === 'next') {
        navigateToScan(currentViewData.value.downTo);
      }
    }
    function handleKeyPress(dir) {
      direction.value = dir;
      updateImage();
    }
    // If there aren't at least two keys in `currentView` we know
    // that we aren't looking at a valid scan, so advance to next.
    function navigateToNextIfCurrentScanNull() {
      if (Object.keys(currentViewData.value).length < 2) {
        handleKeyPress('next');
        return true;
      }
      return false;
    }
    /** Release lock on old experiment, set lock on new experiment */
    async function switchLock(newExperimentId, oldExperimentId = null, force = false) {
      if (!navigateToNextIfCurrentScanNull()) {
        if (editRights.value) {
          loadingLock.value = true;
          if (oldExperimentId) {
            try {
              await setLock({ experimentId: oldExperimentId, lock: false, force });
            } catch (err) {
              setSnackbar('Failed to release edit access on Experiment.');
            }
          }
          // Set the new lock
          try {
            await setLock({ experimentId: newExperimentId, lock: true, force });
            lockCycle.value = setInterval(async () => {
              await setLock({ experimentId: newExperimentId, lock: true });
            }, 1000 * 60 * 5, currentViewData.value.experimentId);
          } catch (err) {
            setSnackbar('Failed to claim edit access on Experiment.');
            loadingLock.value = false;
          }
        }
      }
    }
    function slideToFrame(framePosition) {
      setCurrentFrameId(currentViewData.value.scanFramesList[framePosition - 1]);
    }
    function handleExperimentNoteChange(value) {
      newExperimentNote.value = value;
    }
    async function handleExperimentNoteSave() {
      if (newExperimentNote.value.length > 0) {
        try {
          const newExpData = await djangoRest.setExperimentNote(
            currentViewData.value.experimentId,
            newExperimentNote.value,
          );
          setSnackbar('Saved note successfully.');
          newExperimentNote.value = '';
          updateExperiment(newExpData);
        } catch (err) {
          setSnackbar(`Save failed: ${err.response.data.detail || 'Server error'}`);
        }
      }
    }

    watch(experimentId, (newValue, oldValue) => {
      // Update locked experiment when experiment changes
      switchLock(newValue, oldValue);
      clearInterval(lockCycle.value);
    });
    watch(currentViewData, navigateToNextIfCurrentScanNull);

    onMounted(() => {
      if (!navigateToNextIfCurrentScanNull()) {
        // Switch the lock to the current experiment
        switchLock(experimentId.value);

        // Handles key presses
        window.addEventListener('keydown', (event) => {
          const activeElement = document.activeElement as HTMLElement;
          if (['textarea', 'input'].includes(activeElement.tagName.toLowerCase())) return;
          if (event.key === 'ArrowUp') {
            handleKeyPress('previous');
          } else if (event.key === 'ArrowDown') {
            handleKeyPress('next');
          } else if (event.key === 'ArrowLeft') {
            handleKeyPress('back');
          } else if (event.key === 'ArrowRight') {
            handleKeyPress('forward');
          }
        });
      }
    });
    onBeforeUnmount(() => {
      // Remove lock
      setLock({ experimentId: experimentId.value, lock: false });
      clearInterval(lockCycle.value);
    });

    return {
      user,
      newExperimentNote,
      loadingLock,
      lockCycle,
      proxyManager,
      representation,
      scanCachedPercentage,
      showCrosshairs,
      storeCrosshairs,
      currentViewData,
      lockOwner,
      experimentIsEditable,
      nextFrame,
      previousFrame,
      currentFrame,
      myCurrentProjectRoles,
      setLock,
      setCurrentFrameId,
      setShowCrosshairs,
      setStoreCrosshairs,
      updateExperiment,
      handleExperimentNoteChange,
      handleExperimentNoteSave,
      openScanLink,
      handleKeyPress,
      experimentId,
      editRights,
      switchLock,
      slideToFrame,
    };
  },
});
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
                class="d-flex px-5 py-3 flex-grow-1 flex-column"
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
                class="px-6 py-8 align-center"
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
              height="95px"
              hide-details
              name="input-experiment-notes"
              label="Experiment Notes"
              placeholder="There are no notes on this experiment."
              class="mx-3"
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
                    <div
                      class="d-flex flex-column"
                      style="width: 100%"
                    >
                      <div class="d-flex justify-space-between">
                        <div>
                          Scan:
                          <p
                            :class="currentViewData.scanLink ? 'link' : 'grey--text'"
                            style="display:inline"
                            @click="openScanLink"
                            @keydown="openScanLink"
                          >
                            <b>{{ currentViewData.scanName }}</b>
                          </p>
                          <p
                            class="grey--text"
                            style="display:inline"
                          >
                            ({{ currentViewData.scanPosition }} /
                            {{ currentViewData.experimentScansList.length }})
                          </p>
                        </div>
                        <div>
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
                            small
                            depressed
                            class="transparent-btn"
                            @mousedown="handleKeyPress('next')"
                          >
                            <v-icon>fa-caret-down</v-icon>
                          </v-btn>
                        </div>
                      </div>
                      <div class="d-flex justify-space-between">
                        <div>
                          Frame:
                          <p
                            class="grey--text"
                            style="display:inline"
                          >
                            ({{ currentViewData.framePosition }} /
                            {{ currentViewData.scanFramesList.length }})
                          </p>
                        </div>
                        <v-slider
                          :value="currentViewData.framePosition"
                          :min="1"
                          :max="currentViewData.scanFramesList.length"
                          @input="slideToFrame"
                        />
                        <div>
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
                        </div>
                      </div>
                    </div>

                    <window-widget
                      :representation="representation"
                      :experiment-id="experimentId"
                    />

                    <v-row class="mx-0">
                      <v-col
                        cols="12"
                        class="grey lighten-4"
                        style="height: 100px; overflow:auto; margin: 15px 0"
                      >
                        <ScanDecision
                          v-for="decision in currentViewData.scanDecisions"
                          :key="decision.id"
                          class="scan-decision"
                          :decision="decision"
                        />
                        <div
                          v-if="!currentViewData.scanDecisions
                            || currentViewData.scanDecisions.length === 0"
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
