<script>
export default {
  name: 'NavbarTitle',
  computed: {
    version() {
      return process.env.VERSION;
    },
  },
};
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
