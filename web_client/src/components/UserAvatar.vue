<script lang="ts">
import {
  defineComponent,
  computed,
} from 'vue';
import store from '@/store';

export default defineComponent({
  name: 'UserAvatar',
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
  setup(props) {
    const user = computed(() => store.state.me);
    const tooltipText = computed(() => {
      let name = props.targetUser.username;
      if (props.targetUser.first_name && props.targetUser.last_name) {
        name = `${props.targetUser.first_name} ${props.targetUser.last_name}`;
      }
      if (props.asEditor) {
        if (props.targetUser.username === user.value.username) return 'You are editing this experiment.';
        return `${name} is editing this experiment.`;
      }
      return name;
    });
    function hashCode(s) {
      return s.split('')
        .reduce((a, b) => {
          const c = a < 5 ? 1 : 0;
          a = (c - a) + b.charCodeAt(0);
          return a && a;
        }, 0);
    }
    function computeColor() {
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
      const colorIndex = Math.abs(hashCode(props.targetUser.username) % colors.length);
      return colors[colorIndex];
    }

    return {
      user,
      tooltipText,
      hashCode,
      computeColor,
    };
  },
});
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
