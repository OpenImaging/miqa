<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import store from '@/store';
import djangoRest from '@/django';
import { Project } from '@/types';

export default defineComponent({
  name: 'DataImportExport',
  components: {},
  props: {
    importOnly: {
      type: Boolean,
      default: false,
    },
    exportOnly: {
      type: Boolean,
      default: false,
    },
  },
  setup() {
    const currentProject = computed(() => store.state.currentProject);
    const loadProject = (project: Project) => store.dispatch.loadProject(project);
    const { isGlobal } = store.getters;

    const importing = ref(false);
    const importDialog = ref(false);
    const importErrorText = ref('');
    const importErrors = ref(false);
    const exporting = ref(false);

    async function importData() {
      importing.value = true;
      importErrorText.value = '';
      importErrors.value = false;
      try {
        if (isGlobal) {
          await djangoRest.globalImport();
        } else {
          await djangoRest.projectImport(currentProject.value.id);
        }
        importing.value = false;

        this.$snackbar({
          text: 'Import finished.',
          timeout: 6000,
        });

        if (!isGlobal) {
          await loadProject(currentProject.value);
        }
      } catch (ex) {
        importing.value = false;
        this.$snackbar({
          text: ex || 'Import failed. Refer to server logs for details.',
        });
        console.error(ex);
      }
      importDialog.value = false;
    }
    async function exportData() {
      exporting.value = true;
      try {
        if (isGlobal) {
          await djangoRest.globalExport();
        } else {
          await djangoRest.projectExport(currentProject.value.id);
        }
        this.$snackbar({
          text: 'Saved data to file successfully.',
          timeout: 6000,
        });
      } catch (err) {
        this.$snackbar({
          text: err || `Export failed: ${err.response.data.detail || 'Server error'}`,
          timeout: 6000,

        });
      }
      exporting.value = false;
    }

    return {
      currentProject,
      isGlobal,
      loadProject,
      importing,
      importDialog,
      importErrorText,
      importErrors,
      exporting,
      importData,
      exportData,
    };
  },
});
</script>

<template>
  <div
    class="pl-3"
  >
    <v-tooltip
      v-if="!exportOnly"
      top
    >
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          @click="importDialog = true"
          v-bind="attrs"
          v-on="on"
          text
          color="primary"
        >
          Import
        </v-btn>
      </template>
      <span>Import from import path</span>
    </v-tooltip>

    <v-tooltip
      v-if="!importOnly"
      top
    >
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          :disabled="exporting"
          @click="exportData"
          v-bind="attrs"
          v-on="on"
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
      </template>
      <span>Export to export path</span>
    </v-tooltip>

    <v-dialog
      v-model="importDialog"
      :persistent="importing"
      width="500"
    >
      <v-card>
        <v-card-title class="title">
          Import
        </v-card-title>
        <v-card-text v-if="isGlobal">
          Importing data will overwrite all objects in every project listed in the import file.
          Are you sure you want to overwrite all objects in multiple projects?
        </v-card-text><v-card-text v-else>
          Importing data will overwrite all objects in this project, do you want
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
