<script lang="ts">
import {
  defineComponent,
  computed,
  ref,
  watchEffect,
} from 'vue';
import store from '@/store';
import djangoRest from '@/django';
import DataImportExport from '@/components/DataImportExport.vue';
import { Project } from '@/types';

export default defineComponent({
  name: 'ProjectSettings',
  components: {
    DataImportExport,
  },
  setup() {
    const user = computed(() => store.state.me);
    const importPath = ref('');
    const exportPath = ref('');
    const anatomyOrientation = ref<string>();
    const showDeleteWarningOverlay = ref(false);
    const changed = ref(false);
    const importPathError = ref('');
    const exportPathError = ref('');
    const form = ref(null);

    const currentProject = computed(() => store.state.currentProject);
    const globalSettings = computed(() => store.state.globalSettings);
    const projects = computed(() => store.state.projects);
    const isGlobal = computed(() => store.getters.isGlobal);
    const userCanEditProject = computed(
      () => user.value.is_superuser || (
        currentProject.value && user.value.username === currentProject.value.creator
      ),
    );

    const setProjects = (projs: Project[]) => store.commit('SET_PROJECTS', projs);
    const setCurrentProject = (project) => store.commit('SET_CURRENT_PROJECT', project);
    const setRenderOrientation = (orientation) => store.commit('SET_RENDER_ORIENTATION', orientation);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);

    watchEffect(() => {
      if (isGlobal.value) {
        importPath.value = globalSettings.value.import_path;
        exportPath.value = globalSettings.value.export_path;
      } else {
        djangoRest.settings(currentProject.value.id).then((settings) => {
          importPath.value = settings.import_path;
          exportPath.value = settings.export_path;
          anatomyOrientation.value = settings.anatomy_orientation;
        });
      }
    });

    async function deleteProject() {
      try {
        await djangoRest.deleteProject(currentProject.value.id);
        setProjects(projects.value.filter((proj) => proj.id !== currentProject.value.id));
        setCurrentProject(undefined);
        showDeleteWarningOverlay.value = false;

        setSnackbar('Project deleted.');
      } catch (ex) {
        setSnackbar(ex || 'Project deletion failed.');
      }
    }

    async function save(callback) {
      if (!form.value.validate()) {
        return;
      }
      try {
        if (isGlobal.value) {
          await djangoRest.setGlobalSettings({
            import_path: importPath.value.trim(),
            export_path: exportPath.value.trim(),
          });
        } else {
          await djangoRest.setProjectSettings(currentProject.value.id, {
            import_path: importPath.value.trim(),
            export_path: exportPath.value.trim(),
            anatomy_orientation: anatomyOrientation.value,
          });
          setRenderOrientation(anatomyOrientation.value);
        }
        changed.value = false;
      } catch (e) {
        const { message } = e.response.data;
        if (message.includes('import')) {
          importPathError.value = message;
        } else {
          exportPathError.value = message;
        }
        setTimeout(() => {
          importPathError.value = '';
          exportPathError.value = '';
        }, 3000);
      }
      if (callback && callback instanceof Function) callback();
    }

    return {
      user,
      showDeleteWarningOverlay,
      userCanEditProject,
      currentProject,
      setProjects,
      setCurrentProject,
      isGlobal,
      projects,
      importPath,
      exportPath,
      anatomyOrientation,
      changed,
      importPathError,
      exportPathError,
      form,
      deleteProject,
      save,
    };
  },
});
</script>

<template>
  <v-form
    ref="form"
    @submit.prevent="save"
  >
    <v-text-field
      v-model="importPath"
      :rules="[
        v =>
          !v
          || v.endsWith('.json')
          || v.endsWith('.csv')
          || 'Needs to be a json or csv file',
      ]"
      :disabled="!userCanEditProject"
      :error-messages="importPathError"
      label="Import path"
      placeholder="Specify a server path to read an import file"
      autocomplete="on"
      name="miqa-json-import-path"
      @input="changed = true"
    >
      <template #append>
        <v-tooltip
          v-if="importPath"
          bottom
        >
          <template #activator="{ on }">
            <v-icon v-on="on">
              mdi-dots-horizontal
            </v-icon>
          </template>
          {{ importPath }}
        </v-tooltip>
      </template>
    </v-text-field>
    <v-text-field
      v-model="exportPath"
      :rules="[
        v =>
          !v
          || v.endsWith('.json')
          || v.endsWith('.csv')
          || 'Needs to be a json or csv file',
      ]"
      :disabled="!userCanEditProject"
      :error-messages="exportPathError"
      label="Export path"
      placeholder="Specify a server path to write an export file"
      autocomplete="on"
      name="miqa-json-export-path"
      @input="changed = true"
    >
      <template #append>
        <v-tooltip
          v-if="exportPath"
          bottom
        >
          <template #activator="{ on }">
            <v-icon v-on="on">
              mdi-dots-horizontal
            </v-icon>
          </template>
          {{ exportPath }}
        </v-tooltip>
      </template>
    </v-text-field>
    <v-select
      v-if="!isGlobal"
      v-model="anatomyOrientation"
      label="Project scans orientation"
      :items="[{ text: 'Neurology (LPS)', value: 'LPS' }, { text: 'Radiology (RAS)', value: 'RAS' }]"
      @change="changed = true"
    />
    <v-flex
      class="d-flex"
      style="flex-direction: row"
    >
      <v-btn
        v-if="userCanEditProject"
        :disabled="!changed"
        type="submit"
        color="primary"
        @click="save"
      >
        Save
      </v-btn>
      <DataImportExport
        :import-path="importPath"
        :export-path="exportPath"
        @save="save"
      />
      <div style="flex-grow:2">
        <v-btn
          v-if="userCanEditProject && !isGlobal"
          class="red white--text"
          style="float: right;"
          @click="showDeleteWarningOverlay = true"
        >
          DELETE PROJECT
        </v-btn>
      </div>
    </v-flex>
    <v-overlay
      v-if="userCanEditProject && !isGlobal"
      :value="showDeleteWarningOverlay"
      :dark="false"
    >
      <v-card
        class="dialog-box"
        style="min-width:600px"
      >
        <v-btn
          icon
          style="float: right"
          @click="showDeleteWarningOverlay = false"
        >
          <v-icon
            large
            color="red darken-2"
          >
            mdi-close
          </v-icon>
        </v-btn>
        <v-card-title>
          Delete {{ currentProject.name }}
        </v-card-title>
        Are you sure you want to recursively delete this
        project and its dependent objects (experiments, scans, etc.)?
        <br><br>
        <v-btn
          class="red white--text"
          block
          @click="deleteProject"
        >
          PERMANENTLY DELETE THIS PROJECT AND ITS EXPERIMENTS
        </v-btn>
      </v-card>
    </v-overlay>
  </v-form>
</template>

<style lang="scss" scoped>
.dialog-box {
  width: 30vw;
  min-height: 10vw;
  padding: 20px;
  background-color: white!important;
  color: #333333 !important;
}
</style>
