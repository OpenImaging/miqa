<template>
  <v-dialog
    v-model="show"
    max-width="400"
  >
    <v-card>
      <v-card-title
        v-if="title"
        class="title"
      >
        {{ title }}
      </v-card-title>
      <v-card-text>
        {{ text }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          v-if="confirm"
          @click="negative"
          text
        >
          {{ negativeButton }}
        </v-btn>
        <v-btn
          @click="positive"
          color="primary"
          text
        >
          {{ positiveButton }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'Prompt',
  vuetify: null,
  props: {},
  data: () => ({
    show: false,
    title: '',
    text: '',
    positiveButton: 'Confirm',
    negativeButton: 'Cancel',
    confirm: false,
    resolve: null,
  }),
  watch: {
    show(value) {
      if (!value) {
        this.resolve(false);
      }
    },
  },
  methods: {
    negative() {
      this.show = false;
      this.resolve(false);
    },
    positive() {
      this.show = false;
      this.resolve(true);
    },
  },
};
</script>
