<script lang="ts">
import {
  defineComponent,
  computed,
  ref,
  onMounted,
  watch,
} from 'vue';
import store from '@/store';

export default defineComponent({
  name: 'ScreenshotDialog',
  setup() {
    const fileType = ref('jpg');
    const fileName = ref();
    const show = ref(false);
    const output = ref();
    const currentScreenshot = computed(() => store.state.currentScreenshot);
    const setCurrentScreenshot = (ss) => store.commit('SET_CURRENT_SCREENSHOT', ss);
    const addScreenshot = (ss) => store.commit('ADD_SCREENSHOT', ss);

    function getFileName() {
      return fileName.value ? fileName.value : currentScreenshot.value.name;
    }

    async function getOutput() {
      if (!currentScreenshot.value) {
        return null;
      }
      if (fileType.value === 'png') {
        return currentScreenshot.value.dataURL;
      }
      const { image, width, height }: {
        image: HTMLImageElement, width: number, height: number
      } = await (async (file) => new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          resolve({ image: img, width: img.width, height: img.height });
        };
        img.src = file;
      }))(currentScreenshot.value.dataURL);
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      return canvas.toDataURL('image/jpeg');
    }
    function save() {
      addScreenshot({
        dataURL: output.value,
        name: getFileName(),
      });
    }
    function close() {
      show.value = false;
    }

    watch(currentScreenshot, async (value) => {
      if (value) {
        output.value = await getOutput();
        fileName.value = currentScreenshot.value.name;
        show.value = true;
      }
    });
    watch(show, (value) => {
      if (!value) {
        setTimeout(() => setCurrentScreenshot(null), 300);
      }
    });

    onMounted(async () => {
      output.value = await getOutput();
      fileName.value = currentScreenshot.value.name;
    });

    return {
      fileType,
      fileName,
      getFileName,
      output,
      show,
      currentScreenshot,
      save,
      close,
    };
  },
});
</script>

<template>
  <v-dialog
    v-model="show"
    max-width="500px"
  >
    <v-card v-if="currentScreenshot">
      <v-btn
        icon
        style="float:right"
        @click="show = false"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
      <v-card-title>
        Save screenshot
      </v-card-title>
      <v-container
        grid-list-sm
        class="pb-0"
      >
        <v-layout>
          <v-flex>
            <v-card
              flat
              tile
            >
              <v-img
                :aspect-ratio="1"
                :src="currentScreenshot.dataURL"
              />
            </v-card>
          </v-flex>
        </v-layout>
        <v-layout>
          <v-flex>
            <v-text-field
              v-model="fileName"
              label="Filename"
              @keyup.enter="
                save();
                close();
              "
            />
          </v-flex>
          <v-flex xs2>
            <v-select
              v-model="fileType"
              :items="['jpg', 'png']"
              label="File type"
              hide-details
              single-line
            />
          </v-flex>
        </v-layout>
      </v-container>
      <v-card-actions>
        <v-spacer />
        <v-btn
          :disabled="!output"
          :download="`${fileName}.${fileType}`"
          :href="output"
          color="primary"
          text
        >
          Download
        </v-btn>
        <v-btn
          :disabled="!output"
          color="primary"
          text
          @click="
            save();
            close();
          "
        >
          Attach to email draft
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
