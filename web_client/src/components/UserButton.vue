<script lang="ts">
import { defineComponent, inject } from 'vue';
import { User } from '@/types';

// Login/Logout Button
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
    class="mx-4"
    @click="$emit('logout')"
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
