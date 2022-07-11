<script lang="ts">
import store from '@/store';
import {
  defineComponent, computed, watch,
} from '@vue/composition-api';

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
    const { currentViewData } = store.getters;
    const windowLocked = computed(() => store.state.windowLocked);
    const currentWindowWidth = computed(() => store.state.currentWindowWidth);
    const currentWindowLevel = computed(() => store.state.currentWindowLevel);
    const widthMin = computed(() => (props.representation && props.representation.getPropertyDomainByName('windowWidth').min) || 0);
    const widthMax = computed(() => (props.representation && Math.ceil(props.representation.getPropertyDomainByName('windowWidth').max)) || 0);
    const levelMin = computed(() => (props.representation && props.representation.getPropertyDomainByName('windowLevel').min) || 0);
    const levelMax = computed(() => (props.representation && Math.ceil(props.representation.getPropertyDomainByName('windowLevel').max)) || 0);
    const autoWidth = computed(() => currentViewData.autoWindow || widthMax.value);
    const autoLevel = computed(() => currentViewData.autoLevel
        || Math.ceil((levelMax.value * 0.4) / 10) * 10);
    const setWindowLocked = (lock) => store.commit.setWindowLocked(lock);
    const setExperimentAutoWidth = (width) => store.commit.setExperimentAutoWindow(width);
    const setExperimentAutoLevel = (level) => store.commit.setExperimentAutoLevel(level);

    function updateWindow(width: number, level: number) {
      props.representation.setWindowWidth(width);
      props.representation.setWindowLevel(level);
    }

    watch(currentWindowWidth, (value) => {
      if (Number.isInteger(value) && value !== autoWidth.value) {
        setExperimentAutoWidth({ experimentId: props.experimentId, autoWindow: value });
        props.representation.setWindowWidth(value);
      }
    });

    watch(currentWindowLevel, (value) => {
      if (Number.isInteger(value) && value !== autoLevel.value) {
        setExperimentAutoLevel({ experimentId: props.experimentId, autoLevel: value });
        props.representation.setWindowLevel(value);
      }
    });

    updateWindow(autoWidth.value, autoLevel.value);
    return {
      windowLocked,
      currentWindowWidth,
      currentWindowLevel,
      setWindowLocked,
      setExperimentAutoWidth,
      setExperimentAutoLevel,
      widthMin,
      widthMax,
      levelMin,
      levelMax,
      autoWidth,
      autoLevel,
      updateWindow,
    };
  },
});
</script>

<template>
  <v-row
    no-gutters
    fill-height
    align="center"
  >
    <v-col
      cols="1"
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
    <v-col
      cols="3"
    >
      Window width
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
      cols="6"
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
    <v-col cols="3">
      Window level
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
    <v-col cols="6">
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
  </v-row>
</template>
