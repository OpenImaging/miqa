<script lang="ts">
import { ref } from 'vue';
import { defineComponent, inject } from '@vue/composition-api';
import { useStore } from 'vuex';
import { useSnackbar } from "vue3-snackbar";
import djangoRest from '@/django'
import { HTMLInputEvent, Session } from '@/types';

export default defineComponent({
  name: 'DataImportExport',
  components: {},
  setup() {
    const store = useStore();
    const snackbar = useSnackbar();

    const mainSession = inject('mainSession') as Session;
    const loadSession = (session: Session) => store.dispatch('loadSession', session);
    const loadLocalDataset = (files: FileList) => store.dispatch('loadLocalDataset', files);

    let importing = ref(false);
    let importDialog = ref(false);
    let importErrorText = ref('');
    let importErrors = ref(false);
    let exporting = ref(false);

    async function importData() {
      importing.value = true;
      importErrorText.value = '';
      importErrors.value = false;
      try {
        await djangoRest.import(mainSession.id);
        importing.value = false;

        snackbar.add({
          text: 'Import finished.',
          timeout: 6000,
        });

        await loadSession(mainSession);
      } catch (ex) {
        importing.value = false;
        snackbar.add({
          text: 'Import failed. Refer to server logs for details.',
        });
        console.error(ex);
      }
      importDialog.value = false;
    }
    async function exportData(){
      exporting.value = true;
      try {
        await djangoRest.export(mainSession.id);
        snackbar.add({
          text: 'Saved data to file successfully.',
          timeout: 6000,
        });
      } catch (err) {
        snackbar.add({
          text: `Export failed: ${err.response.data.detail || 'Server error'}`,
          timeout: 6000,

        });
      }
      exporting.value = false;
    }
    function activateInput(){
      ref('load').click();
    }
    function loadFiles(event: HTMLInputEvent){
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
      importData,
      exportData,
      activateInput,
      loadFiles
    };
  },
});
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
