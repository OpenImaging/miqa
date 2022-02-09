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
    const projects = computed(() => store.state.projects);

    const importPath = ref('');
    const exportPath = ref('');
    const globalImportExport = ref(false);
    watchEffect(() => {
      djangoRest.settings(currentProject.value.id).then((settings) => {
        importPath.value = settings.importPath;
        exportPath.value = settings.exportPath;
        globalImportExport.value = settings.globalImportExport;
      });
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
        await djangoRest.setSettings(currentProject.value.id, {
          importPath: importPath.value,
          exportPath: exportPath.value,
          globalImportExport: globalImportExport.value,
        });
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
      projects,
      importPath,
      exportPath,
      globalImportExport,
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
        this.setCurrentProject(null);
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
      <v-switch
        v-model="globalImportExport"
        :disabled="!user.is_superuser"
        @click="changed = true"
        color="primary"
        label="Global import/export"
      />
      <v-tooltip top>
        <template v-slot:activator="{ on, attrs }">
          <v-icon
            v-bind="attrs"
            v-on="on"
            color="primary"
            small
            class="mx-1"
          >
            mdi-information-outline
          </v-icon>
        </template>
        Global imports/exports will use the project name from the import file, which will
        potentially modify other projects.
      </v-tooltip>
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
            v-if="user.is_superuser"
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
