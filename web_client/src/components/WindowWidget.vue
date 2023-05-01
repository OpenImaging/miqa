<script lang="ts">
import {
  defineComponent, computed, watch, ref, onMounted,
} from 'vue';
import debounce from 'lodash/debounce';
import store from '@/store';
import { windowPresets } from '@/vtk/constants';
import CustomRangeSlider from './CustomRangeSlider.vue';

export default defineComponent({
  name: 'WindowWidget',
  components: {
    CustomRangeSlider,
  },
  props: {
    representation: {
      required: true,
      type: Object,
    },
    experimentId: {
      required: true,
      type: String,
    },
  },
  setup(props) {
    const currentRange = ref();
    const showLockOptions = ref(false);
    const imageLoadError = ref(false);
    const selectedPreset = ref();
    const currentViewData = computed(() => store.getters.currentViewData);
    const currentFrame = computed(() => store.state.currentFrameId);
    const currentWindowWidth = computed(() => store.state.currentWindowWidth);
    const currentWindowLevel = computed(() => store.state.currentWindowLevel);
    const currentWindowState = computed(() => ({
      width: currentWindowWidth.value,
      level: currentWindowLevel.value,
    }));
    const data = computed(() => props.representation.getInputDataSet());
    const distribution = computed(() => data.value.computeHistogram(data.value.getBounds()));
    const widthMin = computed(() => distribution.value.minimum || 0);
    const widthMax = computed(() => distribution.value.maximum || 0);
    const windowLocked = computed(() => store.state.windowLocked.lock);
    const windowLockImage = computed(() => store.state.windowLocked.associatedImage);

    function updateRender(ww, wl, updateRange = false) {
      if (windowLocked.value) return;
      if (currentWindowWidth.value !== ww) props.representation.setWindowWidth(ww);
      if (currentWindowLevel.value !== wl) props.representation.setWindowLevel(wl);
      if (updateRange) {
        currentRange.value = [
          wl - ww / 2,
          wl + ww / 2,
        ];
      }
    }
    function updateFromRange([v0, v1]) {
      if (windowLocked.value) return;
      if (currentRange.value
        && v0 === currentRange.value[0]
        && v1 === currentRange.value[1]) return;
      currentRange.value = [v0, v1];
      const ww = v1 - v0;
      const wl = v0 + Math.floor(ww / 2);
      updateRender(ww, wl);
    }
    watch(currentWindowState, debounce(
      (state) => updateRender(state.width, state.level, true),
      600,
    ));

    function autoRange() {
      if (windowLocked.value) return;
      currentRange.value = [
        Math.floor(distribution.value.minimum + distribution.value.sigma),
        Math.floor(distribution.value.maximum - distribution.value.sigma),
      ];
      const ww = currentRange.value[1] - currentRange.value[0];
      const wl = currentRange.value[0] + Math.floor(ww / 2);
      updateRender(ww, wl);
    }
    watch(currentFrame, autoRange);

    function applyPreset(presetId) {
      if (windowLocked.value) return;
      currentRange.value = windowPresets.find(
        (preset) => preset.value === presetId,
      ).apply(widthMin.value, widthMax.value);
      const [v0, v1] = currentRange.value;
      const ww = v1 - v0;
      const wl = v0 + Math.floor(ww / 2);
      updateRender(ww, wl);
    }

    onMounted(() => {
      if (windowLocked.value) {
        currentRange.value = [
          currentWindowLevel.value - currentWindowLevel.value / 2,
          currentWindowLevel.value + currentWindowLevel.value / 2,
        ];
        return;
      }
      autoRange();
      window.addEventListener('click', (event: Event) => {
        const protectedDiv = document.getElementById('windowLockWidget');
        const target = event.target as HTMLElement;
        if (!protectedDiv || !protectedDiv.contains(target)) {
          showLockOptions.value = false;
        }
      });
    });

    function setWindowLock(
      lock: boolean,
      duration: string | undefined = undefined,
      target: string | undefined = undefined,
    ) {
      let associatedImage;
      if (duration) associatedImage = `${duration.charAt(0).toUpperCase()}.png`;
      store.commit('SET_WINDOW_LOCKED', {
        lock,
        duration,
        target,
        associatedImage,
      });
      showLockOptions.value = false;
    }

    return {
      currentRange,
      currentViewData,
      currentWindowWidth,
      currentWindowLevel,
      updateFromRange,
      selectedPreset,
      windowLocked,
      setWindowLock,
      showLockOptions,
      imageLoadError,
      windowLockImage,
      widthMin,
      widthMax,
      windowPresets,
      applyPreset,
    };
  },
});
</script>

<template>
  <div
    class="d-flex flex-column"
    style="width: 100%;"
  >
    <div class="d-flex justify-space-between gapped align-center flex-wrap">
      Window
      <v-tooltip bottom>
        <template #activator="{ on, attrs }">
          <v-icon
            v-bind="attrs"
            small
            v-on="on"
          >
            info
          </v-icon>
        </template>
        <span>
          Adjust window and level by moving the slider endpoints or sliding the range bar
        </span>
      </v-tooltip>
      <custom-range-slider
        v-if="currentRange && currentRange.length === 2"
        :value="currentRange"
        :disabled="windowLocked"
        :max="widthMax"
        :min="widthMin"
        class="align-center"
        height="5"
        style="min-width: 300px"
        @input="updateFromRange"
      >
        <template #prepend>
          <v-text-field
            :value="currentRange[0]"
            class="mt-0 pt-0"
            hide-details
            single-line
            type="number"
            style="width: 60px"
            @input="(value) => currentRange = [value, currentRange[1]]"
          />
        </template>
        <template #append>
          <v-text-field
            :value="currentRange[1]"
            class="mt-0 pt-0"
            hide-details
            single-line
            type="number"
            style="width: 60px"
            @input="(value) => currentRange = [currentRange[0], value]"
          />
        </template>
      </custom-range-slider>
      <div
        id="windowLockWidget"
        cols="1"
        style="text-align: right"
      >
        <v-icon
          v-if="!windowLocked"
          @click="() => showLockOptions = true"
        >
          mdi-lock-open
        </v-icon>
        <v-img
          v-else
          :src="windowLockImage"
          height="24px"
          width="18px"
          class="float-right mx-1"
          @click="() => setWindowLock(false)"
          @error="imageLoadError = true"
        />
        <v-icon
          v-if="imageLoadError && windowLocked"
          @click="() => setWindowLock(false)"
        >
          mdi-lock
        </v-icon>
        <v-card
          v-if="showLockOptions"
          attach="#windowLockWidget"
          class="py-3 px-5"
          style="width: 300px; position: absolute; z-index: 2;"
        >
          <div
            class="d-flex"
            style="flex-direction: column; align-items: flex-start; gap: 5px;"
          >
            <v-btn
              small
              @click="() => setWindowLock(true, 'scan', currentViewData.scanId)"
            >
              <v-img
                src="S.png"
                height="18px"
                width="12px"
                class="mr-2"
                @error="imageLoadError = true"
              />
              Maintain lock for Scan
            </v-btn>
            <v-btn
              small
              @click="() => setWindowLock(true, 'experiment', currentViewData.experimentId)"
            >
              <v-img
                src="E.png"
                height="18px"
                width="12px"
                class="mr-2"
                @error="imageLoadError = true"
              />
              Maintain lock for Experiment
            </v-btn>
            <v-btn
              small
              @click="() => setWindowLock(true, 'project', currentViewData.projectId)"
            >
              <v-img
                src="P.png"
                height="18px"
                width="12px"
                class="mr-2"
                @error="imageLoadError = true"
              />
              Maintain lock for Project
            </v-btn>
          </div>
        </v-card>
      </div>
    </div>
    <div class="d-flex justify-space-between gapped align-center">
      Presets
      <v-select
        v-model="selectedPreset"
        :items="windowPresets"
        :disabled="windowLocked"
        placeholder="Select a preset"
        hide-details
        class="pa-0"
        @change="applyPreset"
      />
    </div>
  </div>
</template>

<style scoped>
.gapped {
  column-gap: 10px;
}
</style>
