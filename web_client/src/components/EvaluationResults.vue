<script lang="ts">
export default {
  name: 'EvaluationResults',
  components: {},
  props: {
    results: {
      required: true,
      type: Object,
    },
  },
  computed: {
    orderedResults() {
      return Object.entries(this.results)
        .sort((first, second) => Number(first[1]) - Number(second[1]));
    },
  },
  methods: {
    convertValueToColor(value, text = true) {
      const colors = [
        'red darken-4',
        'red darken-2',
        'orange darken-4',
        'orange darken-2',
        'orange lighten-1',
        'amber darken-1',
        'lime lighten-1',
        'light-green lighten-1',
        'green lighten-1',
        'green darken-2',
        'green darken-4',
        'black '];
      const thisColor = colors[Math.floor(Math.abs(value) * (colors.length - 1)) % colors.length];
      if (text) {
        return `font-weight-bold ${thisColor.replace(' ', '--text text--')}`;
      }
      return thisColor;
    },
  },
};
</script>

<template>
  <v-tooltip
    left
    color="rgba(0,0,0,0)"
  >
    <template #activator="{ on, attrs }">
      <div
        v-bind="attrs"
        :class="convertValueToColor(results.overall_quality)"
        style="display: flex"
        v-on="on"
      >
        {{ Math.round(results.overall_quality * 100) }}%
        <v-img
          src="evaluation-details.png"
          style="display: inline-block"
          height="20"
          width="20"
        />
      </div>
    </template>
    <v-card class="pa-5">
      <v-container
        style="width: 450px"
        class="pa-0"
      >
        <v-row
          no-gutters
        >
          <v-col
            cols="5"
            align="right"
            class="pr-3 font-weight-bold"
            style="text-transform: capitalize"
          >
            Overall Quality
          </v-col>
          <v-col
            cols="6"
            class="pr-3"
          >
            <v-sheet
              :color="convertValueToColor(results.overall_quality, text = false)"
              :width="(results.overall_quality * 100) + '%'"
              height="5"
              class="mt-2"
            />
          </v-col>
          <v-col
            :class="convertValueToColor(results.overall_quality)"
            cols="1"
          >
            {{ Math.round(results.overall_quality * 100) }}%
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12" />
        </v-row>
      </v-container>
      <v-container
        v-for="[name, value] in orderedResults"
        :key="name"
        style="width: 450px"
        class="pa-0"
      >
        <v-row
          v-if="
            !['overall_quality',
              'signal_to_noise_ratio',
              'contrast_to_noise_ratio'].includes(name)"
          no-gutters
        >
          <v-col
            cols="5"
            align="right"
            class="pr-3"
            style="text-transform: capitalize"
          >
            {{ name.replace(/_/g, " ") }}
          </v-col>
          <v-col
            cols="6"
            class="pr-3"
          >
            <v-sheet
              :color="name === 'normal_variants' ? 'black' : convertValueToColor(value, text = false)"
              :width="(value * 100) + '%'"
              height="5"
              class="mt-2"
            />
          </v-col>
          <v-col
            :class="name === 'normal_variants'
              ? 'font-weight-bold black--text'
              : convertValueToColor(value)"
            cols="1"
          >
            {{ Math.round(value * 100) }}%
          </v-col>
        </v-row>
      </v-container>
    </v-card>
  </v-tooltip>
</template>

<style lang="scss" scoped>
.v-tooltip__content.menuable__content__active {
  opacity: 1!important;
}
</style>
