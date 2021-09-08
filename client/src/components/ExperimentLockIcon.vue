<script>
import { mapActions } from 'vuex';

export default {
  name: 'ExperimentLockIcon',
  components: {},
  props: {
    experiment: {
      type: Object,
      required: true,
    },
    small: {
      type: Boolean,
      default: false,
    },
  },
  inject: ['user'],
  methods: {
    ...mapActions(['lockExperiment', 'unlockExperiment']),
  },
};
</script>

<template>
  <v-tooltip
    v-if="experiment.lockOwner === null"
    right
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        icon
        v-bind="attrs"
        v-on="on"
        @click="unlockExperiment(experiment)"
      >
        <v-icon
          :small="small"
          color="grey"
        >
          mdi-lock
        </v-icon>
      </v-btn>
    </template>
    <span>Click to unlock the experiment</span>
  </v-tooltip>
  <v-tooltip
    v-else-if="experiment.lockOwner.username === user.username"
    right
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        icon
        v-bind="attrs"
        v-on="on"
        @click="lockExperiment(experiment)"
      >
        <v-icon
          :small="small"
          color="green"
        >
          mdi-lock-open
        </v-icon>
      </v-btn>
    </template>
    <span>Click to lock the experiment</span>
  </v-tooltip>
  <v-tooltip
    v-else
    right
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        icon
        v-bind="attrs"
        v-on="on"
      >
        <v-icon
          :small="small"
          color="orange"
        >
          mdi-lock-open
        </v-icon>
      </v-btn>
    </template>
    <span>Currently unlocked by {{ experiment.lockOwner.username }}</span>
  </v-tooltip>
</template>
