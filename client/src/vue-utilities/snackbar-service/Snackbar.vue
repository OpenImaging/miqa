<template>
  <v-snackbar
    v-model="show"
    v-bind="options"
    :timeout="timeout"
  >
    {{ text }}
    <v-btn
      v-if="callback"
      @click="buttonClicked"
      color="primary"
      text
    >
      {{ button }}
    </v-btn>
  </v-snackbar>
</template>

<script>
export default {
  name: 'Snackbar',
  data: () => ({
    show: false,
    text: '',
    button: '',
    callback: null,
    timeout: 0,
    options: { left: true },
  }),
  methods: {
    buttonClicked() {
      this.callback();
      this.show = false;
    },
  },
};
</script>
