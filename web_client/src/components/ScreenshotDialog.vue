<script lang="ts">
import { mapState, mapMutations } from 'vuex';

export default {
  name: 'ScreenshotDialog',
  data: () => ({
    fileType: 'jpg',
    filename_: null,
    show: false,
  }),
  computed: {
    ...mapState([
      'currentScreenshot',
    ]),
    filename: {
      get() {
        return this.filename_ ? this.filename_ : this.currentScreenshot.name;
      },
      set(value) {
        this.filename_ = value;
      },
    },
  },
  asyncComputed: {
    async output() {
      if (!this.currentScreenshot) {
        return null;
      }
      if (this.fileType === 'png') {
        return this.currentScreenshot.dataURL;
      }
      const { image, width, height }: {
        image: HTMLImageElement, width: number, height: number
      } = await (async (file) => new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          resolve({ image: img, width: img.width, height: img.height });
        };
        img.src = file;
      }))(this.currentScreenshot.dataURL);
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      return canvas.toDataURL('image/jpeg');
    },
  },
  watch: {
    currentScreenshot(value) {
      if (value) {
        this.show = true;
      }
    },
    show(value) {
      if (!value) {
        setTimeout(() => this.SET_CURRENT_SCREENSHOT(null), 300);
      }
    },
  },
  methods: {
    ...mapMutations([
      'SET_CURRENT_SCREENSHOT',
      'ADD_SCREENSHOT',
    ]),
    save() {
      this.ADD_SCREENSHOT({
        dataURL: this.output,
        name: this.filename,
      });
    },
    close() {
      this.show = false;
    },
  },
};
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
              v-model="filename"
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
          :download="`${filename}.${fileType}`"
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
