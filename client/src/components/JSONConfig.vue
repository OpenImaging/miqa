<script lang="ts">
import {
  computed, defineComponent, ref, watchEffect,
} from '@vue/composition-api';
import store from '@/store';
import djangoRest from '@/django';

export default defineComponent({
  name: 'JSONConfig',
  setup() {
    const currentProject = computed(() => store.state.currentProject);

    const importPath = ref('');
    const exportPath = ref('');
    watchEffect(() => {
      djangoRest.settings(currentProject.value.id).then((settings) => {
        importPath.value = settings.importPath;
        exportPath.value = settings.exportPath;
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
      <v-flex>
        <v-btn
          :disabled="!changed"
          type="submit"
          color="primary"
          class="mx-0"
        >
          Save
        </v-btn>
      </v-flex>
    </v-layout>
  </v-form>
</template>

<style lang="scss" scoped></style>
