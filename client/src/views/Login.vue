<script>
import { GirderAuthentication } from '@girder/components/src';

export default {
  name: 'Login',
  components: {
    GirderAuthentication,
  },
};
</script>

<template>
  <v-container>
    <v-dialog
      persistent
      max-width="500px"
    >
      <GirderAuthentication :register="true" />
    </v-dialog>
  </v-container>
</template>
