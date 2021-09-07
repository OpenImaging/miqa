<script lang="ts">
import { mapActions } from 'vuex';
import { defineComponent, inject } from '@vue/composition-api';
import { User } from '@/types';

export default defineComponent({
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
  setup() {
    const user = inject('user') as User;
    return { user };
  },
  methods: {
    ...mapActions(['lockExperiment', 'unlockExperiment']),
  },
});
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
        @click="lockExperiment(experiment)"
      >
        <v-icon
          :small="small"
          color="grey"
        >
          mdi-lock-open
        </v-icon>
      </v-btn>
    </template>
    <span>Click to lock the experiment</span>
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
        @click="unlockExperiment(experiment)"
      >
        <v-icon
          :small="small"
          color="green"
        >
          mdi-lock
        </v-icon>
      </v-btn>
    </template>
    <span>Click to unlock the experiment</span>
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
          mdi-lock
        </v-icon>
      </v-btn>
    </template>
    <span>Currently locked by {{ experiment.lockOwner.username }}</span>
  </v-tooltip>
</template>
