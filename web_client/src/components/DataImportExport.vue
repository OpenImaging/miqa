<script lang="ts">
import { computed, defineComponent, ref } from 'vue';
import store from '@/store';
import djangoRest from '@/django';
import { Project } from '@/types';

export default defineComponent({
  name: 'DataImportExport',
  components: {},
  props: {
    importPath: {
      type: String,
      required: false,
      default: '',
    },
    exportPath: {
      type: String,
      required: false,
      default: '',
    },
  },
  setup(props, context) {
    const currentProject = computed(() => store.state.currentProject);
    const projects = computed(() => store.state.projects);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);
    const setTaskOverview = (overview) => store.commit('SET_TASK_OVERVIEW', overview);
    const loadProject = (project: Project) => store.dispatch('loadProject', project);
    const isGlobal = computed(() => store.getters.isGlobal);

    const importing = ref(false);
    const importDialog = ref(false);
    const importErrorText = ref('');
    const importErrorList = ref([]);
    const importErrors = ref(false);
    const exporting = ref(false);

    async function importData() {
      context.emit('save', async () => {
        importing.value = true;
        importErrorText.value = '';
        importErrors.value = false;
        try {
          let response;
          if (isGlobal.value) {
            response = await djangoRest.globalImport();
          } else {
            response = await djangoRest.projectImport(currentProject.value.id);
          }
          importing.value = false;
          if (response.detail) {
            importErrors.value = true;
            importErrorText.value = response.detail;
            importErrorList.value = response.errors;
          } else {
            setSnackbar('Import finished.');
          }

          if (!isGlobal.value) {
            await loadProject(currentProject.value);
          } else {
            projects.value.forEach(
              async (project: Project) => {
                setTaskOverview(await djangoRest.projectTaskOverview(project.id));
              },
            );
          }
        } catch (ex) {
          const text = ex || 'Import failed due to server error.';
          importErrors.value = true;
          importErrorText.value = text;
          importing.value = false;
        }
        importDialog.value = false;
      });
    }
    async function exportData() {
      context.emit('save', async () => {
        exporting.value = true;
        try {
          let response;
          if (isGlobal.value) {
            response = await djangoRest.globalExport();
          } else {
            response = await djangoRest.projectExport(currentProject.value.id);
          }
          if (response.detail) {
            importErrors.value = true;
            importErrorText.value = response.detail;
            importErrorList.value = response.warnings;
          } else {
            setSnackbar('Saved data to file successfully.');
          }
        } catch (ex) {
          const text = ex || 'Export failed due to server error.';
          importErrors.value = true;
          importErrorText.value = text;
          importing.value = false;
        }
        exporting.value = false;
      });
    }

    return {
      currentProject,
      isGlobal,
      loadProject,
      importing,
      importDialog,
      importErrorText,
      importErrorList,
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
    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          :disabled="importing || importPath === ''"
          v-bind="attrs"
          text
          color="primary"
          v-on="on"
          @click="importDialog = true"
        >
          <v-progress-circular
            v-if="importing"
            :size="25"
            :width="2"
            indeterminate
            color="primary"
          />
          <span v-else>
            Import
          </span>
        </v-btn>
      </template>
      <span>Import from {{ importPath }}</span>
    </v-tooltip>

    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          :disabled="exporting || exportPath === ''"
          v-bind="attrs"
          text
          color="primary"
          v-on="on"
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
      </template>
      <span>Export to {{ exportPath }}</span>
    </v-tooltip>

    <v-dialog
      v-model="importDialog"
      :persistent="importing"
      width="500"
    >
      <v-card>
        <v-btn
          icon
          style="float:right"
          @click="importDialog = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
        <v-card-title class="text-h6">
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
            text
            @click="importDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            :loading="importing"
            text
            color="primary"
            @click="importData"
          >
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-model="importErrors"
      width="500px"
    >
      <v-card
        class="pa-5"
        style="overflow: auto"
      >
        <v-spacer />
        <v-btn
          icon
          @click="importErrors = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
        <v-card-title class="text-h6">
          Messages Encountered
        </v-card-title>
        <div class="px-5">
          {{ importErrorText }}
        </div>
        <v-divider class="my-3" />

        <v-card-text
          v-for="(importError, index) in importErrorList"
          :key="index"
          class="console-format"
        >
          {{ importError }}
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
.console-format {
  font-family: monospace;
}
</style>
