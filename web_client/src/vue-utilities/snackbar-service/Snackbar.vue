<template>
  <v-snackbar
    v-model="show"
    v-bind="options"
    :timeout="timeout"
  >
    {{ text }}
    <v-btn
      v-if="callback"
      color="primary"
      text
      @click="buttonClicked"
    >
      {{ button }}
    </v-btn>
  </v-snackbar>
</template>

<script lang="ts">
interface SnackbarData {
  show: boolean;
  text: string;
  button: string;
  callback: (() => void) | null;
  timeout: number;
  options: { left: boolean };
}

export default {
  // eslint-disable-next-line vue/multi-word-component-names
  name: 'Snackbar',
  data: () => ({
    show: false,
    text: '',
    button: '',
    callback: null,
    timeout: -1,
    options: { left: true },
  } as SnackbarData),
  methods: {
    buttonClicked() {
      this.callback();
      this.show = false;
    },
  },
};
</script>
