<script>
import Vue from 'vue';
import { mapState, mapGetters, mapMutations } from 'vuex';

import { cleanDatasetName } from '@/utils/helper';
import fill2DView from '../utils/fill2DView';

export default {
  name: 'VtkViewer',
  components: {},
  props: {
    view: {
      required: true,
      type: Object,
    },
  },
  data: () => ({
    slice: null,
    // helper to avoid size flickering
    resized: false,
    fullscreen: false,
  }),
  computed: {
    ...mapState(['proxyManager', 'loadingDataset']),
    ...mapGetters(['currentDataset', 'currentSession']),
    representation() {
      return (
        // force add dependancy on currentDataset
        this.currentDataset
        && this.proxyManager.getRepresentation(null, this.view)
      );
    },
    sliceDomain() {
      return this.representation.getPropertyDomainByName('slice');
    },
    name() {
      return this.view.getName();
    },
    displayName() {
      switch (this.name) {
        case 'x':
          return 'Sagittal';
        case 'y':
          return 'Coronal';
        case 'z':
          return 'Axial';
        default:
          return '';
      }
    },
    keyboardBindings() {
      switch (this.name) {
        case 'z':
          return ['q', 'w', 'e'];
        case 'x':
          return ['a', 's', 'd'];
        case 'y':
          return ['z', 'x', 'c'];
        default:
          return '';
      }
    },
  },
  watch: {
    slice(value) {
      if (value !== this.representation.getSlice()) {
        this.representation.setSlice(value);
      }
    },
    view(view, oldView) {
      this.cleanup();
      oldView.setContainer(null);
      this.initializeSlice();
      this.initializeView();
    },
    currentDataset() {
      this.representation.setSlice(this.slice);
    },
    currentSession() {
      this.initializeSlice();
    },
  },
  mounted() {
    this.initializeView();
    this.initializeSlice();
  },
  beforeDestroy() {
    this.cleanup();
  },
  methods: {
    ...mapMutations(['saveSlice', 'setCurrentScreenshot']),
    initializeSlice() {
      if (this.name !== 'default') {
        this.slice = this.representation.getSlice();
      }
    },
    initializeView() {
      this.view.setContainer(this.$refs.viewer);
      fill2DView(this.view);
      if (this.name !== 'default') {
        this.modifiedSubscription = this.representation.onModified(() => {
          if (!this.loadingDataset) {
            this.slice = this.representation.getSlice();
          }
        });
      }
      setTimeout(() => {
        this.resized = true;
      });
    },
    cleanup() {
      if (this.modifiedSubscription) {
        this.modifiedSubscription.unsubscribe();
      }
    },
    increaseSlice() {
      const slice = Math.min(
        (this.slice += this.sliceDomain.step),
        this.sliceDomain.max,
      );
      this.slice = slice;
    },
    decreaseSlice() {
      const slice = Math.max(
        (this.slice -= this.sliceDomain.step),
        this.sliceDomain.min,
      );
      this.slice = slice;
    },
    async takeScreenshot() {
      const dataURL = await this.view.captureImage();
      this.setCurrentScreenshot({
        name: `${this.currentSession.experiment}/${
          this.currentSession.name
        }/${cleanDatasetName(this.currentDataset.name)}/${this.displayName}`,
        dataURL,
      });
    },
    toggleFullscreen() {
      this.fullscreen = !this.fullscreen;
      this.resized = false;
      Vue.nextTick(() => {
        fill2DView(this.view);
        setTimeout(() => {
          this.resized = true;
        });
      });
    },
    onWindowResize() {
      if (this.resized) {
        fill2DView(this.view);
      }
    },
    roundSlice(value) {
      if (!value) return '';
      return Math.round(value * 100) / 100;
    },
  },
};
</script>

<template>
  <div
    v-resize="onWindowResize"
    class="vtk-viewer"
    :class="{ fullscreen }"
  >
    <div
      v-if="name !== 'default'"
      class="header"
      :class="name"
    >
      <v-layout align-center>
        <v-slider
          v-model="slice"
          v-mousetrap="[
            { bind: keyboardBindings[1], handler: increaseSlice },
            { bind: keyboardBindings[0], handler: decreaseSlice }
          ]"
          class="slice-slider mt-0 mx-4"
          hide-details
          :min="sliceDomain.min"
          :max="sliceDomain.max"
          :step="sliceDomain.step"
        />
        <div class="slice caption px-2">
          {{ roundSlice(slice) }} mm
        </div>
      </v-layout>
    </div>
    <div
      ref="viewer"
      class="viewer"
      :style="{ visibility: resized ? 'unset' : 'hidden' }"
    />
    <v-toolbar
      class="toolbar"
      dark
      flat
      color="black"
      max-height="42"
    >
      <div
        class="indicator body-2"
        :class="name"
      >
        {{ displayName }}
      </div>
      <v-spacer />
      <v-btn
        v-mousetrap="{ bind: keyboardBindings[2], handler: toggleFullscreen }"
        icon
        @click="toggleFullscreen"
      >
        <v-icon v-if="!fullscreen">
          fullscreen
        </v-icon>
        <v-icon v-else>
          fullscreen_exit
        </v-icon>
      </v-btn>
      <v-btn
        icon
        @click="takeScreenshot"
      >
        <v-icon>add_a_photo</v-icon>
      </v-btn>
    </v-toolbar>
  </div>
</template>

<style lang="scss" scoped>
.vtk-viewer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(#3a3a3a, #1d1d1d);
  z-index: 0;

  display: flex;
  flex-direction: column;

  &.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    z-index: 2;
  }

  .header {
    .slice {
      height: 23px;
      line-height: 23px;
      color: white;
    }

    &.z {
      background-color: #ef5350;

      .slice {
        background-color: #b71c1c;
      }
    }

    &.x {
      background-color: #fdd835;

      .slice {
        background-color: #f9a825;
      }
    }

    &.y {
      background-color: #4caf50;

      .slice {
        background-color: #1b5e20;
      }
    }

    .slice {
      width: 85px;
    }
  }

  .toolbar {
    .indicator {
      &::before {
        content: " ";
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 6px;
        margin-right: 10px;
        position: relative;
        top: 1px;
      }

      &.z::before {
        background: #ef5350;
      }

      &.x::before {
        background: #fdd835;
      }

      &.y::before {
        background: #4caf50;
      }
    }
  }

  .viewer {
    flex: 1 1 0px;
    position: relative;
    overflow-y: hidden;
  }
}
</style>

<style lang="scss">
.vtk-viewer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;

  display: flex;
  flex-direction: column;

  .slice-slider .v-slider {
    height: 23px;
  }
}
</style>
