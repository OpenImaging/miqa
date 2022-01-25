<script>
import { vec3 } from 'gl-matrix';

import Vue from 'vue';
import { mapState, mapGetters, mapMutations } from 'vuex';

import { cleanFrameName } from '@/utils/helper';
import CrosshairSet from '../utils/crosshairs';
import fill2DView from '../utils/fill2DView';
import { getView } from '../vtk/viewManager';
import { VIEW_ORIENTATIONS } from '../vtk/constants';

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
    originalZoom: undefined,
  }),
  computed: {
    ...mapState(['proxyManager', 'loadingFrame', 'showCrosshairs', 'iIndexSlice', 'jIndexSlice', 'kIndexSlice']),
    ...mapGetters(['currentFrame', 'currentScan']),
    representation() {
      return (
        // force add dependency on currentFrame
        this.currentFrame
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
      if (this.setCurrentVtkIndexSlices) {
        const ijkMapping = {
          x: 'i',
          y: 'j',
          z: 'k',
        };
        this.setCurrentVtkIndexSlices({
          indexAxis: ijkMapping[this.trueAxis(this.name)],
          value: this.representation.getSliceIndex(),
        });
      }
    },
    iIndexSlice() {
      this.updateCrosshairs();
    },
    jIndexSlice() {
      this.updateCrosshairs();
    },
    kIndexSlice() {
      this.updateCrosshairs();
    },
    view(view, oldView) {
      this.cleanup();
      oldView.setContainer(null);
      this.initializeSlice();
      this.initializeView();
    },
    currentFrame() {
      this.representation.setSlice(this.slice);
    },
    currentScan() {
      this.initializeSlice();
      this.initializeCamera();
    },
    showCrosshairs() {
      this.updateCrosshairs();
    },
  },
  mounted() {
    this.initializeView();
    this.initializeSlice();
    this.initializeCamera();
    this.updateCrosshairs();
    this.renderSubscription = this.view.getInteractor().onRenderEvent(() => {
      this.updateCrosshairs();
    });
    this.resizeObserver = new window.ResizeObserver((entries) => {
      if (entries.length === 1 && this.$refs.viewer && this.$refs.crosshairsCanvas) {
        const width = this.$refs.viewer.clientWidth;
        const height = this.$refs.viewer.clientHeight;
        this.$refs.crosshairsCanvas.width = width;
        this.$refs.crosshairsCanvas.height = height;
        this.$refs.crosshairsCanvas.style.width = `${width}px`;
        this.$refs.crosshairsCanvas.style.height = `${height}px`;
        this.initializeCamera();
        this.updateCrosshairs();
      }
    });
    this.resizeObserver.observe(this.$refs.viewer);
  },
  beforeUnmount() {
    this.cleanup();
  },
  methods: {
    ...mapMutations(['saveSlice', 'setCurrentScreenshot', 'setCurrentVtkIndexSlices']),
    initializeSlice() {
      if (this.name !== 'default') {
        this.slice = this.representation.getSlice();
      }
    },
    initializeView() {
      this.view.setContainer(this.$refs.viewer);
      fill2DView(this.view);
      this.originalZoom = this.view.getCamera().getParallelScale();
      if (this.name !== 'default') {
        this.modifiedSubscription = this.representation.onModified(() => {
          if (!this.loadingFrame) {
            this.slice = this.representation.getSlice();
          }
        });
      }
      setTimeout(() => {
        this.resized = true;
      });
    },
    initializeCamera() {
      const camera = this.view.getCamera();
      const orientation = this.representation.getInputDataSet().getDirection();

      let newViewUp = VIEW_ORIENTATIONS[this.name].viewUp.slice();
      let newDirectionOfProjection = VIEW_ORIENTATIONS[this.name].directionOfProjection;
      newViewUp = this.findClosestColumnToVector(
        newViewUp,
        orientation,
      );
      newDirectionOfProjection = this.findClosestColumnToVector(
        newDirectionOfProjection,
        orientation,
      );

      camera.setDirectionOfProjection(...newDirectionOfProjection);
      camera.setViewUp(...newViewUp);

      this.view.resetCamera();
      fill2DView(this.view);
    },
    findClosestColumnToVector(inputVector, matrix) {
      let currClosest = null;
      let currMax = 0;
      const inputVectorAxis = inputVector.findIndex((value) => value !== 0);
      for (let i = 0; i < 3; i += 1) {
        const currColumn = matrix.slice(i * 3, i * 3 + 3);
        const currValue = Math.abs(currColumn[inputVectorAxis]);
        if (currValue > currMax) {
          currClosest = currColumn;
          currMax = currValue;
        }
      }
      const flipCurrClosest = vec3.dot(
        inputVector,
        currClosest,
      );
      if (flipCurrClosest < 0) {
        currClosest = currClosest.map((value) => value * -1);
      }
      return currClosest;
    },
    trueAxis(axisName) {
      const orientation = this.representation.getInputDataSet().getDirection();
      const axisNumber = VIEW_ORIENTATIONS[axisName].axis;
      const axisOrientation = [
        orientation[axisNumber],
        orientation[3 + axisNumber],
        orientation[6 + axisNumber],
      ].map(
        (val) => Math.abs(val),
      );
      const axisOrdering = ['x', 'y', 'z'];
      const trueAxis = axisOrdering[
        axisOrientation.indexOf(Math.max(...axisOrientation))
      ];
      return trueAxis;
    },
    async takeScreenshot() {
      const view = getView(this.proxyManager, `ScreenshotView2D_${this.name}:${this.name}`, this.screenshotContainer);
      view.getOpenglRenderWindow().setSize(512, 512);
      fill2DView(view, 512, 512);
      const dataURL = await view.captureImage();
      this.setCurrentScreenshot({
        name: `${this.currentScan.experiment}/${
          this.currentScan.name
        }/${cleanFrameName(this.currentFrame.name)}/${this.displayName}`,
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
      if (this.resized && this.originalZoom === this.view.getCamera().getParallelScale()) {
        fill2DView(this.view);
      }
    },
    changeSlice(newValue) {
      this.slice = newValue;
    },
    roundSlice(value) {
      if (!value) return '';
      return Math.round(value * 100) / 100;
    },
    drawLine(ctx, displayLine) {
      ctx.strokeStyle = displayLine.color;
      ctx.beginPath();
      ctx.moveTo(...displayLine.start);
      ctx.lineTo(...displayLine.end);
      ctx.stroke();
    },
    updateCrosshairs() {
      const myCanvas = document.getElementById(`crosshairs-${this.name}`);
      if (myCanvas && myCanvas.getContext) {
        const ctx = myCanvas.getContext('2d');
        ctx.clearRect(0, 0, myCanvas.width, myCanvas.height);

        if (this.showCrosshairs) {
          const crosshairSet = new CrosshairSet(
            this.representation, this.view, myCanvas,
            this.iIndexSlice, this.jIndexSlice, this.kIndexSlice,
          );
          const originalColors = {
            x: '#fdd835',
            y: '#4caf50',
            z: '#b71c1c',
          };
          const trueColors = Object.fromEntries(
            Object.entries(originalColors).map(([axisName, hex]) => [this.trueAxis(axisName), hex]),
          );
          const [displayLine1, displayLine2] = crosshairSet.getCrosshairsForAxis(
            this.trueAxis(this.name), trueColors,
          );
          this.drawLine(ctx, displayLine1);
          this.drawLine(ctx, displayLine2);
        }
      }
    },
    cleanup() {
      if (this.renderSubscription) {
        this.renderSubscription.unsubscribe();
        this.resizeObserver.unobserve(this.$refs.viewer);
      }
      if (this.modifiedSubscription) {
        this.modifiedSubscription.unsubscribe();
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
          :value="slice"
          @change="changeSlice"
          v-mousetrap="[
            { bind: keyboardBindings[1] },
            { bind: keyboardBindings[0] }
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
      class="viewer"
    >
      <div
        ref="viewer"
        :style="{ visibility: resized ? 'unset' : 'hidden' }"
      />
      <canvas
        ref="crosshairsCanvas"
        :id="'crosshairs-'+name"
        class="crosshairs"
      />
    </div>
    <v-toolbar
      class="toolbar"
      dark
      flat
      color="#ffffff00"
      height="46"
      max-height="46"
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
    display: flex;
    flex-direction: column;
  }

  .viewer > div {
    flex: 1 1 0px;
    position: relative;
    overflow-y: hidden;
  }
}

.crosshairs {
  z-index: 3;
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
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
