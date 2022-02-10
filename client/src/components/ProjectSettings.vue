<script lang="ts">
import {
  computed, defineComponent, ref, watchEffect,
} from '@vue/composition-api';
import { mapMutations } from 'vuex';
import store from '@/store';
import djangoRest from '@/django';
import DataImportExport from '@/components/DataImportExport.vue';

export default defineComponent({
  name: 'ProjectSettings',
  components: {
    DataImportExport,
  },
  inject: ['user'],
  data: () => ({
    showDeleteWarningOverlay: false,
  }),
  setup() {
    const currentProject = computed(() => store.state.currentProject);
    const globalSettings = computed(() => store.state.globalSettings);
    const projects = computed(() => store.state.projects);
    const { isGlobal } = store.getters;

    const importPath = ref('');
    const exportPath = ref('');
    watchEffect(() => {
      if (isGlobal) {
        importPath.value = globalSettings.value.importPath;
        exportPath.value = globalSettings.value.exportPath;
      } else {
        djangoRest.settings(currentProject.value.id).then((settings) => {
          importPath.value = settings.importPath;
          exportPath.value = settings.exportPath;
        });
      }
    });

    const changed = ref(false);
    const importPathError = ref('');
    const exportPathError = ref('');
    const form = ref(null);

    async function save() {
      if (!form.value.validate()) {
        return;
      }
      try {
        if (isGlobal) {
          await djangoRest.setGlobalSettings({
            importPath: importPath.value,
            exportPath: exportPath.value,
          });
        } else {
          await djangoRest.setProjectSettings(currentProject.value.id, {
            importPath: importPath.value,
            exportPath: exportPath.value,
          });
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
    }

    return {
      currentProject,
      isGlobal,
      projects,
      importPath,
      exportPath,
      changed,
      importPathError,
      exportPathError,
      form,
      save,
    };
  },
  methods: {
    ...mapMutations(['setProjects', 'setCurrentProject']),
    async deleteProject() {
      try {
        await djangoRest.deleteProject(this.currentProject.id);
        this.setProjects(this.projects.filter((proj) => proj.id !== this.currentProject.id));
        this.setCurrentProject(undefined);
        this.showDeleteWarningOverlay = false;

        this.$snackbar({
          text: 'Project deleted.',
          timeout: 6000,
        });
      } catch (ex) {
        this.$snackbar({
          text: ex || 'Project deletion failed.',
        });
      }
    },
  },
});
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
          v-model="importPath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :disabled="!user.is_superuser"
          :error-messages="importPathError"
          @input="changed = true"
          label="Import path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-import-path"
        />
      </v-flex>
      <v-flex
        lg6
        sm8
        xs12
      >
        <v-text-field
          v-model="exportPath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :disabled="!user.is_superuser"
          :error-messages="exportPathError"
          @input="changed = true"
          label="Export path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-export-path"
        />
      </v-flex>
    </v-layout>
    <v-layout>
      <v-row>
        <v-col cols="1">
          <v-btn
            :disabled="!changed"
            v-if="user.is_superuser"
            type="submit"
            color="primary"
          >
            Save
          </v-btn>
        </v-col>
        <v-col cols="9">
          <DataImportExport />
        </v-col>
        <v-col
          cols="2"
          class="text-right"
        >
          <v-btn
            v-if="user.is_superuser && !isGlobal"
            @click="showDeleteWarningOverlay = true"
            class="red white--text"
            style="float: right"
          >
            DELETE PROJECT
          </v-btn>
        </v-col>
      </v-row>
    </v-layout>
    <v-overlay
      v-if="user.is_superuser && !isGlobal"
      :value="showDeleteWarningOverlay"
      :dark="false"
    >
      <v-card
        class="dialog-box"
      >
        <v-btn
          @click="showDeleteWarningOverlay = false"
          icon
          style="float: right"
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
          @click="deleteProject"
          class="red white--text"
          block
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
  color: '#333333'!important;
}
</style>
