<script lang="ts">
import store from '@/store';
import {
  defineComponent, computed, watch, ref,
} from '@vue/composition-api';
import { windowPresets } from '@/vtk/constants';

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
    const selectedPreset = ref();
    const windowLocked = computed(() => store.state.windowLocked);
    const currentWindowWidth = computed(() => store.state.currentWindowWidth);
    const currentWindowLevel = computed(() => store.state.currentWindowLevel);
    const widthMin = computed(() => (props.representation && props.representation.getPropertyDomainByName('windowWidth').min) || 0);
    const widthMax = computed(() => (props.representation && Math.ceil(props.representation.getPropertyDomainByName('windowWidth').max)) || 0);
    const levelMin = computed(() => (props.representation && props.representation.getPropertyDomainByName('windowLevel').min) || 0);
    const levelMax = computed(() => (props.representation && Math.ceil(props.representation.getPropertyDomainByName('windowLevel').max)) || 0);
    const setWindowLocked = (lock) => store.commit.setWindowLocked(lock);

    function updateWindow(width: number, level: number) {
      props.representation.setWindowWidth(width);
      props.representation.setWindowLevel(level);
    }
    function applyPreset(preset) {
      updateWindow(preset.width, preset.level);
      setWindowLocked(true);
    }

    watch(currentWindowWidth, (value) => {
      if (Number.isInteger(value)) {
        props.representation.setWindowWidth(value);
      }
    });

    watch(currentWindowLevel, (value) => {
      if (Number.isInteger(value)) {
        props.representation.setWindowLevel(value);
      }
    });

    return {
      selectedPreset,
      windowLocked,
      currentWindowWidth,
      currentWindowLevel,
      setWindowLocked,
      widthMin,
      widthMax,
      levelMin,
      levelMax,
      updateWindow,
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
          The measure of the range of CT numbers that an image contains.
          A significantly wide window displaying all the CT numbers will
          obscure different attenuations between soft tissues.
        </span>
      </v-tooltip>
    </v-col>
    <v-col
      cols="7"
      style="text-align: center"
    >
      <v-slider
        v-mousetrap="[
          {
            bind: '-',
            handler: () => updateWindow(currentWindowWidth - 5, currentWindowLevel)
          },
          {
            bind: '=',
            handler: () => updateWindow(currentWindowWidth + 5, currentWindowLevel)
          }
        ]"
        :value="currentWindowWidth"
        :max="widthMax"
        :min="widthMin"
        class="align-center"
        hide-details
        :disabled="windowLocked"
        @input="(width) => updateWindow(width, currentWindowLevel)"
      >
        <template #prepend>
          {{ widthMin }}
        </template>
        <template #append>
          <div class="pr-5 pt-2">
            {{ widthMax }}
          </div>
        </template>
      </v-slider>
    </v-col>
    <v-col cols="2">
      <v-text-field
        :value="currentWindowWidth"
        class="mt-0 pt-0"
        hide-details
        single-line
        type="number"
        style="width: 80px; float: right"
        :disabled="windowLocked"
        @input="(width) => updateWindow(width, currentWindowLevel)"
      />
    </v-col>
    <v-col
      cols="1"
      style="text-align: right"
    >
      <v-icon
        v-if="!windowLocked"
        @click="() => setWindowLocked(true)"
      >
        mdi-lock-open
      </v-icon>
      <v-icon
        v-else
        @click="() => setWindowLocked(false)"
      >
        mdi-lock
      </v-icon>
    </v-col>

    <v-col cols="2">
      Level
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
          The midpoint of the range of the CT numbers displayed.
          When the window level is decreased the CT image will be brighter.
        </span>
      </v-tooltip>
    </v-col>
    <v-col cols="7">
      <v-slider
        v-mousetrap="[
          {
            bind: '[',
            handler: () => updateWindow(currentWindowWidth, currentWindowLevel - 5)
          },
          {
            bind: ']',
            handler: () => updateWindow(currentWindowWidth, currentWindowLevel + 5)
          }
        ]"
        :value="currentWindowLevel"
        :max="levelMax"
        :min="levelMin"
        class="align-center"
        hide-details
        :disabled="windowLocked"
        @input="(level) => updateWindow(currentWindowWidth, level)"
      >
        <template #prepend>
          {{ levelMin }}
        </template>
        <template #append>
          <div class="pr-5 pt-2">
            {{ levelMax }}
          </div>
        </template>
      </v-slider>
    </v-col>
    <v-col cols="2">
      <v-text-field
        :value="currentWindowLevel"
        class="mt-0 pt-0"
        hide-details
        single-line
        type="number"
        style="width: 80px; float: right"
        :disabled="windowLocked"
        @input="(level) => updateWindow(currentWindowWidth, level)"
      />
    </v-col>
    <v-col
      cols="1"
      style="text-align: right"
    >
      <v-icon
        v-if="!windowLocked"
        @click="() => setWindowLocked(true)"
      >
        mdi-lock-open
      </v-icon>
      <v-icon
        v-else
        @click="() => setWindowLocked(false)"
      >
        mdi-lock
      </v-icon>
    </v-col>

    <v-col cols="2">
      Presets
    </v-col>
    <v-col cols="8">
      <v-select
        v-model="selectedPreset"
        :items="windowPresets"
        placeholder="Select a preset"
        item-text="label"
        item-value="window"
        hide-details
        class="pa-0"
      />
    </v-col>
    <v-col col="2">
      <v-btn
        small
        :disabled="!selectedPreset"
        style="float: right; margin-top: 10px"
        @click="() => applyPreset(selectedPreset)"
      >
        Apply
      </v-btn>
    </v-col>
  </v-row>
</template>
