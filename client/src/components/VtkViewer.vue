<script>
import Vue from 'vue';
import { mapState, mapGetters, mapMutations } from 'vuex';

import { cleanDatasetName } from '@/utils/helper';
import fill2DView from '../utils/fill2DView';
import { getView } from '../vtk/viewManager';

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
    screenshotContainer: document.createElement('div'),
  }),
  computed: {
    ...mapState(['proxyManager', 'loadingDataset', 'xSlice', 'ySlice', 'zSlice']),
    ...mapGetters(['currentDataset', 'currentScan']),
    representation() {
      return (
        // force add dependency on currentDataset
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
      this.representation.setSlice(value);
      if (this.setCurrentVtkSlices) {
        this.setCurrentVtkSlices({ axis: this.name, value: this.roundSlice(value) });
      }
    },
    xSlice() {
      this.updateCrosshairs();
    },
    ySlice() {
      this.updateCrosshairs();
    },
    zSlice() {
      this.updateCrosshairs();
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
    currentScan() {
      this.initializeSlice();
    },
  },
  mounted() {
    this.initializeView();
    this.initializeSlice();
    this.updateCrosshairs();
  },
  beforeDestroy() {
    this.cleanup();
  },
  methods: {
    ...mapMutations(['saveSlice', 'setCurrentScreenshot', 'setCurrentVtkSlices']),
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
      this.slice = Math.min(
        (this.slice + this.sliceDomain.step),
        this.sliceDomain.max,
      );
    },
    decreaseSlice() {
      this.slice = Math.max(
        (this.slice - this.sliceDomain.step),
        this.sliceDomain.min,
      );
    },
    async takeScreenshot() {
      const view = getView(this.proxyManager, `ScreenshotView2D_${this.name}:${this.name}`, this.screenshotContainer);
      view.getOpenglRenderWindow().setSize(512, 512);
      fill2DView(view, 512, 512);
      const dataURL = await view.captureImage();
      this.setCurrentScreenshot({
        name: `${this.currentScan.experiment}/${
          this.currentScan.name
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
    updateCrosshairs() {
      const myCanvas = document.getElementById(`crosshairs-${this.name}`);
      if (myCanvas.getContext) {
        const ctx = myCanvas.getContext('2d');
        ctx.clearRect(0, 0, myCanvas.width, myCanvas.height);
        const originX = myCanvas.width / 2;
        const originY = myCanvas.height / 2;
        const crosshairHeight = myCanvas.height - 30;
        const crosshairWidth = myCanvas.width - 80;
        if (this.name === 'x') {
          ctx.fillStyle = '#4caf50';
          ctx.fillRect(originX + this.ySlice, originY - crosshairHeight / 2, 1, crosshairHeight);
          ctx.fillStyle = '#b71c1c';
          ctx.fillRect(originX - crosshairWidth / 2, originY - this.zSlice, crosshairWidth, 1);
        } else if (this.name === 'y') {
          ctx.fillStyle = '#fdd835';
          ctx.fillRect(originX + this.xSlice, originY - crosshairHeight / 2, 1, crosshairHeight);
          ctx.fillStyle = '#b71c1c';
          ctx.fillRect(originX - crosshairWidth / 2, originY - this.zSlice, crosshairWidth, 1);
        } else if (this.name === 'z') {
          ctx.fillStyle = '#fdd835';
          ctx.fillRect(originX + this.xSlice, originY - crosshairHeight / 2, 1, crosshairHeight);
          ctx.fillStyle = '#4caf50';
          ctx.fillRect(originX - crosshairWidth / 2, originY + this.ySlice, crosshairWidth, 1);
        }
      }
    },
  },
};
</script>

<template>
  <div
    v-resize="onWindowResize"
    :class="{ fullscreen }"
    class="vtk-viewer"
  >
    <div
      v-if="name !== 'default'"
      :class="name"
      class="header"
    >
      <v-layout align-center>
        <v-slider
          v-model="slice"
          v-mousetrap="[
            { bind: keyboardBindings[1], handler: increaseSlice },
            { bind: keyboardBindings[0], handler: decreaseSlice }
          ]"
          :min="sliceDomain.min"
          :max="sliceDomain.max"
          :step="sliceDomain.step"
          class="slice-slider mt-0 mx-4"
          hide-details
        />
        <div class="slice caption px-2">
          {{ roundSlice(slice) }} mm
        </div>
      </v-layout>
    </div>
    <div
      ref="viewer"
      :style="{ visibility: resized ? 'unset' : 'hidden' }"
      class="viewer"
    />
    <canvas
      :id="'crosshairs-'+name"
      class="crosshairs"
    />
    <v-toolbar
      class="toolbar"
      dark
      flat
      color="black"
      max-height="42"
    >
      <div
        :class="name"
        class="indicator body-2"
      >
        {{ displayName }}
      </div>
      <v-spacer />
      <v-btn
        v-mousetrap="{ bind: keyboardBindings[2], handler: toggleFullscreen }"
        @click="toggleFullscreen"
        icon
      >
        <v-icon v-if="!fullscreen">
          fullscreen
        </v-icon>
        <v-icon v-else>
          fullscreen_exit
        </v-icon>
      </v-btn>
      <v-btn
        @click="takeScreenshot"
        icon
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
  background: black;
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

.crosshairs {
  z-index: 3;
  position: absolute;
  top: 30px;
  width: 100%;
  height: calc(100% - 60px);
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
