<script lang="ts">
import {
  computed, defineComponent, ref, watchEffect,
} from '@vue/composition-api';
import store from '@/store';
import djangoRest from '@/django';
import DataImportExport from '@/components/DataImportExport.vue';

export default defineComponent({
  name: 'ProjectSettings',
  components: {
    DataImportExport,
  },
  inject: ['user'],
  setup() {
    const currentProject = computed(() => store.state.currentProject);

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
      <v-tooltip top>
        <template v-slot:activator="{ on, attrs }">
          <div
            v-bind="attrs"
            v-on="on"
          >
            <v-switch
              v-model="globalImportExport"
              @click="changed = true"
              color="primary"
              label="Global import/export"
            />
          </div>
        </template>
        Global imports/exports will use the project name from the import file, which will
        potentially modify other projects.
      </v-tooltip>
    </v-layout>
    <v-btn
      :disabled="!changed"
      v-if="user.is_superuser"
      type="submit"
      color="primary"
      style="display: inline-block"
    >
      Save
    </v-btn>
    <DataImportExport v-if="user.is_superuser" />
  </v-form>
</template>
