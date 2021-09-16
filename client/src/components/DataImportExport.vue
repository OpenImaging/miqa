<script lang="ts">
import { defineComponent, inject, ref } from '@vue/composition-api';
import { useStore } from 'vuex';
import djangoRest from '@/django';
import { HTMLInputEvent, Session } from '@/types';

export default defineComponent({
  name: 'DataImportExport',
  components: {},
  setup() {
    const store = useStore();

    const mainSession = inject('mainSession') as Session;
    const loadSession = (session: Session) => store.dispatch.loadSession(session);
    const loadLocalDataset = (files: FileList) => store.dispatch.loadLocalDataset(files);

    const importing = ref(false);
    const importDialog = ref(false);
    const importErrorText = ref('');
    const importErrors = ref(false);
    const exporting = ref(false);
    const load = ref(null);

    async function importData() {
      importing.value = true;
      importErrorText.value = '';
      importErrors.value = false;
      try {
        await djangoRest.import(mainSession.id);
        importing.value = false;

        this.$snackbar({
          text: 'Import finished.',
          timeout: 6000,
        });

        await loadSession(mainSession);
      } catch (ex) {
        importing.value = false;
        this.$snackbar({
          text: 'Import failed. Refer to server logs for details.',
        });
        console.error(ex);
      }
      importDialog.value = false;
    }
    async function exportData() {
      exporting.value = true;
      try {
        await djangoRest.export(mainSession.id);
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
      exporting.value = false;
    }
    function activateInput() {
      load.click();
    }
    function loadFiles(event: HTMLInputEvent) {
      loadLocalDataset(event.target.files as FileList);
    }

    return {
      mainSession,
      loadSession,
      loadLocalDataset,
      importing,
      importDialog,
      importErrorText,
      importErrors,
      exporting,
      load,
      importData,
      exportData,
      activateInput,
      loadFiles,
    };
  },
});
</script>

<template>
  <div>
    <v-btn
      @click="importDialog = true"
      text
      color="primary"
    >
      Import
    </v-btn>
    <v-btn
      :disabled="exporting"
      @click="exportData"
      text
      color="primary"
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
      @click="activateInput"
      text
      color="secondary"
    >
      Load
    </v-btn>

    <input
      ref="load"
      @change="loadFiles"
      type="file"
      multiple
      style="display: none;"
    >
    <v-dialog
      v-model="importDialog"
      :persistent="importing"
      width="500"
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
            :disabled="importing"
            @click="importDialog = false"
            text
          >
            Cancel
          </v-btn>
          <v-btn
            :loading="importing"
            @click="importData"
            text
            color="primary"
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
            @click="importErrors = false"
            color="primary"
            text
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
