<script lang="ts">
import { User } from '@/types';
import { defineComponent, inject } from '@vue/composition-api';

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
    icon
    color="black lighten-1"
    class="mr-4"
    @click="$emit('user')"
  >
    Logout
  </v-btn>
  <v-btn
    v-else
    text
    @click="$emit('login')"
  >
    Login
  </v-btn>
</template>

<style lang="scss">
button.user-avatar-btn .v-btn__content {
  height: inherit;
}
</style>
