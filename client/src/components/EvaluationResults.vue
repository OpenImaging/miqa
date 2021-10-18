<script>
export default {
  name: 'EvaluationResults',
  components: {},
  props: {
    results: {
      required: true,
      type: Object,
    },
  },
  methods: {
    convertValueToColor(value, text = true) {
      const colors = [
        'green darken-4',
        'green darken-2',
        'green lighten-1',
        'light-green lighten-1',
        'lime lighten-1',
        'amber lighten-3',
        'orange lighten-1',
        'orange darken-2',
        'orange darken-4',
        'red darken-2',
        'red darken-4',
        'black'];
      const thisColor = colors[Math.floor(value * (colors.length - 1))];
      if (text) return thisColor.replace(' ', '--text text--');
      return thisColor;
    },
  },
};
</script>

<template>
  <v-col
    :class="'font-weight-bold ' + convertValueToColor(1 - results.overall_quality)"
    cols="6"
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
          {{ results.overall_quality * 100 }}%
          <v-img
            class="float-right ml-3"
            src="evaluation-details.png"
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
              cols="4"
              align="right"
              class="pr-3 font-weight-bold"
              style="text-transform: capitalize"
            >
              Overall Quality
            </v-col>
            <v-col
              cols="7"
              class="pr-3"
            >
              <v-sheet
                :color="convertValueToColor(1 - results.overall_quality, text=false)"
                :width="(results.overall_quality *100)+'%'"
                height="5"
                class="mt-2"
              />
            </v-col>
            <v-col
              :class="'font-weight-bold ' + convertValueToColor(1 - results.overall_quality)"
              cols="1"
            >
              {{ results.overall_quality }}
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" />
          </v-row>
        </v-container>
        <v-container
          v-for="(value, name) of results"
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
              cols="4"
              align="right"
              class="pr-3"
              style="text-transform: capitalize"
            >
              {{ name.replace(/_/g, " ") }}
            </v-col>
            <v-col
              cols="7"
              class="pr-3"
            >
              <v-sheet
                :color="convertValueToColor(value, text=false)"
                :width="(value * 100)+'%'"
                height="5"
                class="mt-2"
              />
            </v-col>
            <v-col
              :class="'font-weight-bold ' + convertValueToColor(value)"
              cols="1"
            >
              {{ value }}
            </v-col>
          </v-row>
        </v-container>
      </v-card>
    </v-tooltip>
  </v-col>
</template>

<style lang="scss" scoped>
.v-tooltip__content.menuable__content__active {
  opacity: 1!important;
}
</style>
