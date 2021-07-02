<script>
export default {
  name: 'JSONConfig',
  inject: ['djangoRest', 'mainSession'],
  data: () => ({
    importpath: '',
    exportpath: '',
    changed: false,
    importpathError: '',
    exportpathError: '',
  }),
  async created() {
    const { importpath, exportpath } = await this.djangoRest.settings(this.mainSession.id);
    this.importpath = importpath;
    this.exportpath = exportpath;
  },
  methods: {
    async save() {
      if (!this.$refs.form.validate()) {
        return;
      }
      try {
        await this.djangoRest.setSettings(this.mainSession.id, {
          importpath: this.importpath,
          exportpath: this.exportpath,
        });
        this.changed = false;
      } catch (e) {
        const { message } = e.response.data;
        if (message.includes('import')) {
          this.importpathError = message;
        } else {
          this.exportpathError = message;
        }
        setTimeout(() => {
          this.importpathError = '';
          this.exportpathError = '';
        }, 3000);
      }
    },
  },
};
</script>

<template>
  <v-form
    ref="form"
    @submit.prevent="save"
  >
    <v-layout wrap>
      <v-flex
        lg6
        sm8
        xs12
      >
        <v-text-field
          v-model="importpath"
          label="Import path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-importpath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :error-messages="importpathError"
          @input="changed = true"
        />
      </v-flex>
      <v-flex
        lg6
        sm8
        xs12
      >
        <v-text-field
          v-model="exportpath"
          label="Export path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-exportpath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :error-messages="exportpathError"
          @input="changed = true"
        />
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex>
        <v-btn
          type="submit"
          color="primary"
          class="mx-0"
          :disabled="!changed"
        >
          Save
        </v-btn>
      </v-flex>
    </v-layout>
  </v-form>
</template>

<style lang="scss" scoped></style>
