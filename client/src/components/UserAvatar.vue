<script>

export default {
  name: 'UserAvatar',
  inject: ['user'],
  props: {
    targetUser: {
      type: Object,
      required: true,
    },
    asEditor: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  computed: {
    tooltipText() {
      let name = this.targetUser.username;
      if (this.targetUser.first_name && this.targetUser.last_name) {
        name = `${this.targetUser.first_name} ${this.targetUser.last_name}`;
      }
      if (this.asEditor) {
        if (this.targetUser.username === this.user.username) return 'You are editing this experiment.';
        return `${name} is editing this experiment.`;
      }
      return name;
    },
  },
  methods: {
    hashCode(s) {
      return s.split('').reduce((a, b) => { a = ((a < 5) - a) + b.charCodeAt(0); return a && a; }, 0);
    },
    computeColor() {
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
      const colorIndex = Math.abs(this.hashCode(this.targetUser.username) % colors.length);
      return colors[colorIndex];
    },
  },
};
</script>

<template>
  <v-tooltip
    v-if="targetUser"
    bottom
  >
    <template #activator="{ on, attrs }">
      <v-avatar
        v-bind="attrs"
        :color="computeColor()"
        size="30"
        style="border-radius: 50%"
        class="mx-2"
        v-on="on"
      >
        <span
          v-if="targetUser.first_name && targetUser.last_name"
          class="white--text text--h5"
        >
          {{ targetUser.first_name[0] }}{{ targetUser.last_name[0] }}
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
      {{ tooltipText }}
    </span>
  </v-tooltip>
</template>
