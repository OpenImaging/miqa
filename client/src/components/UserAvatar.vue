<script>
import { User } from '@/types';

export default {
  name: 'UserAvatar',
  props: {
    user: {
      type: User,
      required: true,
    },
    me: {
      type: User,
      required: true,
    },
  },
  methods: {
    hashCode(s) {
      return s.split('').reduce((a, b) => { a = ((a < 5) - a) + b.charCodeAt(0); return a && a; }, 0);
    },
    computeColor() {
      console.log(this.user.username);
      const colors = [
        'purple lighten-1',
        'purple darken-1',
        'indigo lighten-1',
        'indigo darken-1',
        'blue lighten-1',
        'blue darken-1',
        'cyan lighten-1',
        'cyan darken-1',
        'teal lighten-1',
        'teal darken-1',
      ];
      const colorIndex = Math.abs(this.hashCode(this.user.username) % colors.length);
      return colors[colorIndex];
    },
  },
};
</script>

<template>
  <v-tooltip
    v-if="user"
    bottom
  >
    <template v-slot:activator="{ on, attrs }">
      <v-avatar
        v-bind="attrs"
        v-on="on"
        :color="computeColor()"
        size="30"
      >
        <span
          v-if="user.first_name && user.last_name"
          class="white--text text--h5"
        >
          {{ user.first_name[0] }}{{ user.last_name[0] }}
        </span>
        <v-icon
          v-else
          dark
        >
          mdi-account-circle
        </v-icon>
      </v-avatar>
    </template>
    <span>
      {{ user.username === me.username ? 'You are' : user.username +' is' }}
      currently editing this Experiment.
    </span>
  </v-tooltip>
</template>

<style scoped>

</style>
