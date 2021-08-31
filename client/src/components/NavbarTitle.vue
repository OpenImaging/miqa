<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'NavbarTitle',
  setup() {
    const version = computed(() => process.env.VERSION);
    return { version };
  },
});
</script>

<template>
  <v-toolbar-title>
    <v-tooltip
      open-delay="2000"
      bottom
    >
      <template #activator="{ on }">
        <span v-on="on">MIQA</span>
      </template>
      <span>v{{ version }}</span>
    </v-tooltip>
  </v-toolbar-title>
</template>
