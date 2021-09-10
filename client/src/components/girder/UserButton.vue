<script lang="ts">
import { defineComponent, inject } from '@vue/composition-api';
import { User } from '@/types';

export default defineComponent({
  name: 'UserButton',
  setup() {
    const user = inject('user') as User;
    return {
      user,
    };
  },
});
</script>

<template>
  <v-btn
    v-if="user"
    @click="$emit('user')"
    icon
    color="black lighten-1"
    class="mr-4"
  >
    Logout
  </v-btn>
  <v-btn
    v-else
    @click="$emit('login')"
    text
  >
    Login
  </v-btn>
</template>

<style lang="scss">
button.user-avatar-btn .v-btn__content {
  height: inherit;
}
</style>
