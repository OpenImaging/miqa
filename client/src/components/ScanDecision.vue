<script>
import { ScanDecision } from '@/types';
import UserAvatar from './UserAvatar.vue';

export default {
  name: 'ScanDecision',
  components: {
    UserAvatar,
  },
  props: {
    decision: {
      type: ScanDecision,
      required: true,
    },
  },
  methods: {
    convertDecisionToColor(decision) {
      if (decision.toLowerCase() === 'bad') return 'red--text text--darken-2';
      if (decision.toLowerCase() === 'good') return 'green--text text--darken-2';
      return 'grey--text text--darken-2';
    },
  },
};
</script>

<template>
  <v-row dense>
    <v-col cols="1">
      <UserAvatar
        :target-user="decision.creator"
      />
    </v-col>
    <v-col
      :class="convertDecisionToColor(decision.decision)"
      cols="1"
      style="text-align: center"
    >
      ({{ decision.decision[0] }})
    </v-col>
    <v-col
      :class="decision.note ? 'black--text' : 'grey--text'"
      cols="7"
    >
      {{ decision.note ? decision.note : "No comment" }}
    </v-col>
    <v-col
      cols="3"
      class="grey--text"
      style="text-align: right"
    >
      {{ decision.created }}
    </v-col>
  </v-row>
</template>

<style scoped>

</style>
