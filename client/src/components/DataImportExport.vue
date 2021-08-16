<script>
import { mapActions, mapState } from 'vuex';

export default {
  name: 'DataImportExport',
  components: {},
  inject: ['djangoRest'],
  data: () => ({
    importing: false,
    importDialog: false,
    importErrorText: '',
    importErrors: false,
    exporting: false,
  }),
  computed: {
    ...mapState(['mainSession']),
  },
  methods: {
    ...mapActions(['loadSession', 'loadLocalDataset']),
    async importData() {
      this.importing = true;
      this.importErrorText = '';
      this.importErrors = false;
      try {
        await this.djangoRest.import(this.mainSession.id);
        this.importing = false;

        this.$snackbar({
          text: 'Import finished.',
          timeout: 6000,
        });

        await this.loadSession(this.mainSession);
      } catch (ex) {
        this.importing = false;
        this.$snackbar({
          text: 'Import failed. Refer to server logs for details.',
        });
        console.error(ex);
      }
      this.importDialog = false;
    },
    async exportData() {
      this.exporting = true;
      try {
        await this.djangoRest.export(this.mainSession.id);
        this.$snackbar({
          text: 'Saved data to file successfully.',
          timeout: 6000,
        });
      } catch (err) {
        this.$snackbar({
          text: `Export failed: ${err.response.data.detail || 'Server error'}`,
          timeout: 6000,

        });
      }
      this.exporting = false;
    },
    activateInput() {
      this.$refs.load.click();
    },
    loadFiles(event) {
      this.loadLocalDataset(event.target.files);
    },
  },
};
</script>

<template>
  <div>
    <v-btn
      text
      color="primary"
      @click="importDialog = true"
    >
      Import
    </v-btn>
    <v-btn
      :disabled="exporting"
      text
      color="primary"
      @click="exportData"
    >
      <v-progress-circular
        v-if="exporting"
        :size="25"
        :width="2"
        indeterminate
        color="primary"
      />
      <span v-else>
        Export
      </span>
    </v-btn>

    <v-btn
      text
      color="secondary"
      @click="activateInput"
    >
      Load
    </v-btn>

    <input
      ref="load"
      type="file"
      multiple
      style="display: none;"
      @change="loadFiles"
    >
    <v-dialog
      v-model="importDialog"
      width="500"
      :persistent="importing"
    >
      <v-card>
        <v-card-title class="title">
          Import
        </v-card-title>
        <v-card-text>
          Import data would delete outdated records from the system, do you want
          to continue?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            text
            :disabled="importing"
            @click="importDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            text
            color="primary"
            :loading="importing"
            @click="importData"
          >
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="importErrors"
      content-class="import-error-dialog"
    >
      <v-card>
        <v-card-title class="title">
          Import Errors Encountered
        </v-card-title>
        <v-card-text class="console-format">
          {{ importErrorText }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            text
            @click="importErrors = false"
          >
            Ok
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style lang="scss">
.import-error-dialog {
  position: relative;
  width: 100%;
  margin: 48px;
}
.console-format {
  white-space: pre-wrap;
  font-family: monospace;
}
</style>
