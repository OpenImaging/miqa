<script>
import Vue from 'vue';
import { mapState, mapGetters, mapMutations } from 'vuex';
import { vec3 } from 'gl-matrix';

import { cleanFrameName } from '@/utils/helper';
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
  }),
  computed: {
    ...mapState(['proxyManager', 'loadingFrame', 'showCrosshairs', 'xSlice', 'ySlice', 'zSlice', 'iIndexSlice', 'jIndexSlice', 'kIndexSlice']),
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
      return this.normalizedAxis(this.view.getName());
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
        const ijkMapping = {
          x: 'i',
          y: 'j',
          z: 'k',
        };
        this.setCurrentVtkSlices({ axis: this.name, value: this.roundSlice(value) });
        this.setCurrentVtkIndexSlices({
          indexAxis: ijkMapping[this.name],
          value: this.representation.getSliceIndex(),
        });
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
    currentFrame() {
      this.representation.setSlice(this.slice);
    },
    currentScan() {
      this.initializeSlice();
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
    ...mapMutations(['saveSlice', 'setCurrentScreenshot', 'setCurrentVtkSlices', 'setCurrentVtkIndexSlices']),
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
      const orientation = this.representation.getInputDataSet().getDirection();
      const camera = this.view.getCamera();

      let newOrientation = orientation.slice();
      newOrientation = newOrientation.map(
        (value) => value * VIEW_ORIENTATIONS[this.name].orientation,
      );

      if (this.name === 'x') {
        newOrientation = orientation.slice(0, 3);
      } else if (this.name === 'y') {
        newOrientation = orientation.slice(3, 6);
      } else if (this.name === 'z') {
        newOrientation = orientation.slice(6, 9);
      }
      camera.setDirectionOfProjection(...newOrientation);

      const newViewUp = VIEW_ORIENTATIONS[this.name].viewUp.slice();
      vec3.transformMat3(newViewUp, newViewUp, orientation);
      camera.setViewUp(newViewUp);

      this.view.resetCamera();
      fill2DView(this.view);
    },
    normalizedAxis(oldAxis) {
      const orientation = this.representation.getInputDataSet().getDirection();
      const normalizedOrientation = orientation.map((value) => Math.abs(Math.round(value)));
      const axisMapping = {
        x: normalizedOrientation.slice(0, 3),
        y: normalizedOrientation.slice(3, 6),
        z: normalizedOrientation.slice(6, 9),
      };
      const newAxis = Object.entries(axisMapping).filter(([, slice]) => {
        if (oldAxis === 'x') {
          return slice[0] === 1;
        } if (oldAxis === 'y') {
          return slice[1] === 1;
        }
        return slice[2] === 1;
      }).map((entry) => entry[0])[0];

      return newAxis;
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
      if (this.resized) {
        fill2DView(this.view);
      }
    },
    roundSlice(value) {
      if (!value) return '';
      return Math.round(value * 100) / 100;
    },
    convertWorldSlicesToLines() {
      const imageData = this.representation.getInputDataSet();
      const [iMax, jMax, kMax] = imageData.getDimensions();
      if (this.name === 'x') {
        return [
          [
            imageData.indexToWorld([this.iIndexSlice, 0, this.kIndexSlice]),
            imageData.indexToWorld([this.iIndexSlice, jMax - 1, this.kIndexSlice]),
          ],
          [
            imageData.indexToWorld([this.iIndexSlice, this.jIndexSlice, 0]),
            imageData.indexToWorld([this.iIndexSlice, this.jIndexSlice, kMax - 1]),
          ],
        ];
      } if (this.name === 'y') {
        return [
          [
            imageData.indexToWorld([0, this.jIndexSlice, this.kIndexSlice]),
            imageData.indexToWorld([iMax - 1, this.jIndexSlice, this.kIndexSlice]),
          ],
          [
            imageData.indexToWorld([this.iIndexSlice, this.jIndexSlice, 0]),
            imageData.indexToWorld([this.iIndexSlice, this.jIndexSlice, kMax - 1]),
          ],
        ];
      }
      if (this.name === 'z') {
        return [
          [
            imageData.indexToWorld([0, this.jIndexSlice, this.kIndexSlice]),
            imageData.indexToWorld([iMax - 1, this.jIndexSlice, this.kIndexSlice]),
          ],
          [
            imageData.indexToWorld([this.iIndexSlice, 0, this.kIndexSlice]),
            imageData.indexToWorld([this.iIndexSlice, jMax - 1, this.kIndexSlice]),
          ],
        ];
      }
      return null;
    },
    convertWorldLinesToDisplayLines(worldLines) {
      const renderer = this.view.getRenderer();
      const renderWindow = this.view.getOpenglRenderWindow();
      const mappedLine0 = worldLines[0].map(
        (line) => renderWindow.worldToDisplay(line[0], line[1], line[2], renderer)
          .map((c) => c / devicePixelRatio).slice(0, 2),
      );
      const mappedLine1 = worldLines[1].map(
        (line) => renderWindow.worldToDisplay(line[0], line[1], line[2], renderer)
          .map((c) => c / devicePixelRatio).slice(0, 2),
      );
      return [mappedLine0, mappedLine1];
    },
    drawLine(ctx, point1, point2, color) {
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(...point1);
      ctx.lineTo(...point2);
      ctx.stroke();
    },
    updateCrosshairs() {
      const myCanvas = document.getElementById(`crosshairs-${this.name}`);
      if (myCanvas && myCanvas.getContext) {
        const ctx = myCanvas.getContext('2d');
        ctx.clearRect(0, 0, myCanvas.width, myCanvas.height);

        if (this.showCrosshairs) {
          const worldLines = this.convertWorldSlicesToLines();
          const [displayLine1, displayLine2] = this.convertWorldLinesToDisplayLines(worldLines);
          displayLine1[0][1] = myCanvas.height - displayLine1[0][1];
          displayLine1[1][1] = myCanvas.height - displayLine1[1][1];
          displayLine2[0][1] = myCanvas.height - displayLine2[0][1];
          displayLine2[1][1] = myCanvas.height - displayLine2[1][1];
          if (this.name === 'x') {
            this.drawLine(ctx, displayLine1[0], displayLine1[1], '#b71c1c');
            this.drawLine(ctx, displayLine2[0], displayLine2[1], '#4caf50');
          }
          if (this.name === 'y') {
            this.drawLine(ctx, displayLine1[0], displayLine1[1], '#b71c1c');
            this.drawLine(ctx, displayLine2[0], displayLine2[1], '#fdd835');
          }
          if (this.name === 'z') {
            this.drawLine(ctx, displayLine1[0], displayLine1[1], '#4caf50');
            this.drawLine(ctx, displayLine2[0], displayLine2[1], '#fdd835');
          }
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
