<script lang="ts">
import { defineComponent, inject, ref } from '@vue/composition-api';
import djangoRest from '@/django';
import { Session } from '@/types';

export default defineComponent({
  name: 'JSONConfig',
  setup() {
    const mainSession = inject('mainSession') as Session;

    const importpath = ref('');
    const exportpath = ref('');
    const changed = ref(false);
    const importpathError = ref('');
    const exportpathError = ref('');
    const form = ref(null);

    async function created() {
      const { importpathFetched, exportpathFetched } = await djangoRest.settings(mainSession.id);
      importpath.value = importpathFetched;
      exportpath.value = exportpathFetched;
    }
    async function save() {
      if (!form.value.validate()) {
        return;
      }
      try {
        await djangoRest.setSettings(mainSession.id, {
          importpath,
          exportpath,
        });
        changed.value = false;
      } catch (e) {
        const { message } = e.response.data;
        if (message.includes('import')) {
          importpathError.value = message;
        } else {
          exportpathError.value = message;
        }
        setTimeout(() => {
          importpathError.value = '';
          exportpathError.value = '';
        }, 3000);
      }
    }

    return {
      mainSession,
      importpath,
      exportpath,
      changed,
      importpathError,
      exportpathError,
      form,
      created,
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
          v-model="importpath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :error-messages="importpathError"
          @input="changed = true"
          label="Import path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-importpath"
        />
      </v-flex>
      <v-flex
        lg6
        sm8
        xs12
      >
        <v-text-field
          v-model="exportpath"
          :rules="[
            v => !!v || 'path is required',
            v =>
              v.endsWith('.json') ||
              v.endsWith('.csv') ||
              'Needs to be a json or csv file'
          ]"
          :error-messages="exportpathError"
          @input="changed = true"
          label="Export path"
          placeholder=" "
          autocomplete="on"
          name="miqa-json-exportpath"
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
