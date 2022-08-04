<script lang="ts">
import store from '@/store';
import {
  defineComponent, computed, watch, ref, onMounted,
} from '@vue/composition-api';
import { windowPresets } from '@/vtk/constants';
import debounce from 'lodash/debounce';

export default defineComponent({
  name: 'WindowWidget',
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
    const currentViewData = computed(() => store.getters.currentViewData);
    const currentFrame = computed(() => store.state.currentFrameId);
    const currentWindowWidth = computed(() => store.state.currentWindowWidth);
    const currentWindowLevel = computed(() => store.state.currentWindowLevel);
    const currentWindowState = computed(() => ({
      width: currentWindowWidth.value,
      level: currentWindowLevel.value,
    }));
    const widthMin = computed(() => (props.representation && props.representation.getPropertyDomainByName('windowWidth').min) || 0);
    const widthMax = computed(() => (props.representation && Math.ceil(props.representation.getPropertyDomainByName('windowWidth').max)) || 0);
    const selectedPreset = ref();
    const windowLocked = computed(() => store.state.windowLocked.lock);
    const showLockOptions = ref(false);

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
      const ww = v1 - v0;
      const wl = v0 + Math.ceil(ww / 2);
      updateRender(ww, wl);
    }
    watch(currentWindowState, debounce(
      (state) => updateRender(state.width, state.level, true),
      600,
    ));

    function autoRange() {
      if (windowLocked.value) return;
      // start with a default range of the middle 60%
      const wholeRange = widthMax.value - widthMin.value;
      currentRange.value = [
        widthMin.value + wholeRange * 0.2,
        widthMax.value - wholeRange * 0.2,
      ];
      updateFromRange(currentRange.value);
    }
    watch(currentFrame, autoRange);

    function applyPreset(presetId) {
      if (windowLocked.value) return;
      currentRange.value = windowPresets.find(
        (preset) => preset.value === presetId,
      ).apply(widthMin.value, widthMax.value);
      updateFromRange(currentRange.value);
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
        if (!protectedDiv.contains(target)) {
          showLockOptions.value = false;
        }
      });
    });

    function setWindowLock(
      lock: boolean,
      duration: string | undefined = undefined,
      target: string | undefined = undefined,
    ) {
      store.commit.setWindowLocked({
        lock,
        duration,
        target,
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
      widthMin,
      widthMax,
      windowPresets,
      applyPreset,
    };
  },
});
</script>

<template>
  <v-row
    no-gutters
    fill-height
    align="center"
    style="border: 1px solid gray; padding: 10px"
  >
    <v-col
      cols="2"
    >
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
          TODO: explain this new widget
        </span>
      </v-tooltip>
    </v-col>
    <v-col
      cols="9"
      style="text-align: center"
    >
      <v-range-slider
        v-model="currentRange"
        :disabled="windowLocked"
        :max="widthMax"
        :min="widthMin"
        class="align-center"
        height="5"
        @change="updateFromRange"
      >
        <template #prepend>
          <v-text-field
            :value="currentRange[0]"
            class="mt-0 pt-0"
            hide-details
            single-line
            type="number"
            style="width: 60px"
            @change="$set(currentRange, 0, $event)"
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
            @change="$set(currentRange, 1, $event)"
          />
        </template>
      </v-range-slider>
    </v-col>
    <v-col
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
      <v-icon
        v-else
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
            />
            Maintain lock for Project
          </v-btn>
        </div>
      </v-card>
    </v-col>

    <v-col cols="2">
      Presets
    </v-col>
    <v-col cols="10">
      <v-select
        v-model="selectedPreset"
        :items="windowPresets"
        :disabled="windowLocked"
        placeholder="Select a preset"
        hide-details
        class="pa-0"
        @change="applyPreset"
      />
    </v-col>
  </v-row>
</template>
