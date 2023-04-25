<script lang="ts">
import { vec3 } from 'gl-matrix';

import { mapState, mapGetters, mapMutations } from 'vuex';

import CrosshairSet from '../utils/crosshairs';
import fill2DView from '../utils/fill2DView';
import { VIEW_ORIENTATIONS, ijkMapping } from '../vtk/constants';

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
    ...mapState([
      'proxyManager',
      'loadingFrame',
      'showCrosshairs',
      'sliceLocation',
      'iIndexSlice',
      'jIndexSlice',
      'kIndexSlice',
      'windowLocked',
      'currentWindowWidth',
      'currentWindowLevel',
      'renderOrientation',
    ]),
    ...mapGetters([
      'currentFrame',
      'currentScan',
      'currentViewData',
    ]),
    // Returning representation from VTK
    representation() {
      return (
        // force add dependency on currentFrame
        this.currentFrame
        && this.proxyManager.getRepresentation(null, this.view)
      );
    },
    // Returns the range of valid values and their step for the slice property
    sliceDomain() {
      if (!this.representation) return null;
      return this.representation.getPropertyDomainByName('slice');
    },
    name() : ('x' | 'y' | 'z') {
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
    ijkName() : ('i' | 'j' | 'k') {
      return ijkMapping[this.name];
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
    slice(newSlice) {
      this.representation.setSlice(newSlice);
      if (this.SET_CURRENT_VTK_INDEX_SLICES) {
        this.SET_CURRENT_VTK_INDEX_SLICES({
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
    // Only runs when changing scans
    view(view, oldView) {
      this.cleanup();
      oldView.setContainer(null);
      this.initializeSlice();
      this.initializeView();
    },
    // Only runs when changing scans
    currentFrame(oldFrame, newFrame) {
      this.representation.setSlice(this.slice);
      this.applyCurrentWindowLevel();
      this.updateCrosshairs();
      // use this instead of currentScan watcher
      // currentScan is computed from currentFrame and technically
      // will change every time currentFrame has changed
      if (oldFrame.scan !== newFrame.scan) {
        this.initializeSlice();
        this.initializeCamera();
      }
    },
    showCrosshairs() {
      this.updateCrosshairs();
    },
  },
  mounted() {
    this.prepareViewer();
  },
  beforeUnmount() {
    this.cleanup();
  },
  methods: {
    ...mapMutations([
      'SET_CURRENT_SCREENSHOT',
      'SET_CURRENT_VTK_INDEX_SLICES',
      'SET_SLICE_LOCATION',
    ]),
    prepareViewer() {
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
      this.applyCurrentWindowLevel();
    },
    initializeSlice() {
      if (this.name !== 'default') {
        this.slice = this.representation.getSlice();
      }
    },
    initializeView() {
      this.view.setContainer(this.$refs.viewer);
      fill2DView(this.view);
      // add scroll interaction to change slice
      this.view.getInteractor().onMouseWheel(() => {
        if (!this.loadingFrame) {
          this.slice = this.representation.getSlice();
        }
      });
      // add click interaction to place crosshairs
      this.view.getInteractor().onLeftButtonPress((event) => this.placeCrosshairs(event));
      // remove drag interaction to change window
      const targetManipulator = this.view.getInteractor()
        .getInteractorStyle().getMouseManipulators().find(
          (manipulator) => manipulator.getClassName() === 'vtkMouseRangeManipulator',
        );
      if (targetManipulator) {
        targetManipulator.setDragEnabled(false);
      }
      setTimeout(() => {
        this.resized = true;
      });
    },
    initializeCamera() {
      const camera = this.view.getCamera();
      const orientation = this.representation.getInputDataSet().getDirection();

      let newViewUp = VIEW_ORIENTATIONS[this.renderOrientation][this.name].viewUp.slice();
      let newDirectionOfProjection = VIEW_ORIENTATIONS[
        this.renderOrientation
      ][this.name].directionOfProjection;
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
    applyCurrentWindowLevel() {
      const representationProperty = this.representation.getActors()[0].getProperty();
      representationProperty.setColorWindow(this.currentWindowWidth);
      representationProperty.setColorLevel(this.currentWindowLevel);
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
      if (!this.representation.getInputDataSet()) return undefined;
      const orientation = this.representation.getInputDataSet().getDirection();
      const axisNumber = VIEW_ORIENTATIONS[this.renderOrientation][axisName].axis;
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
      const dataURL = await this.view.captureImage();

      const imageOutput = await (
        async (file) : Promise<HTMLImageElement> => new Promise<HTMLImageElement>((resolve) => {
          const img = new Image();
          img.onload = () => {
            resolve(img);
          };
          img.src = file;
        })
      )(dataURL);
      const canvas = document.createElement('canvas');
      canvas.width = imageOutput.width;
      canvas.height = imageOutput.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(imageOutput, 0, 0);

      if (this.showCrosshairs) {
        const crosshairSet = new CrosshairSet(
          this.name,
          this.ijkName,
          this.representation,
          this.view,
          canvas,
          this.iIndexSlice,
          this.jIndexSlice,
          this.kIndexSlice,
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
          this.trueAxis(this.name),
          trueColors,
        );
        this.drawLine(ctx, displayLine1);
        this.drawLine(ctx, displayLine2);
      }
      this.SET_CURRENT_SCREENSHOT({
        name: `${this.currentViewData.experimentName}/${
          this.currentViewData.scanName
        }/${this.currentFrame.frame_number}/${this.displayName}`,
        dataURL: canvas.toDataURL('image/jpeg'),
      });
    },
    toggleFullscreen() {
      this.fullscreen = !this.fullscreen;
      setTimeout(() => {
        this.$refs.viewer.style.width = 'inherit';
        this.$refs.viewer.style.width = `${this.$refs.viewer.clientWidth - 3}px`;
      }, 100);
    },
    changeSlice(newValue) {
      this.slice = newValue;
    },
    roundSlice(value) {
      if (!value) return '';
      return Math.round(value * 100) / 100;
    },
    drawLine(ctx, displayLine) {
      if (!displayLine) return;
      ctx.strokeStyle = displayLine.color;
      ctx.beginPath();
      ctx.moveTo(...displayLine.start);
      ctx.lineTo(...displayLine.end);
      ctx.stroke();
    },
    updateCrosshairs() {
      const myCanvas: HTMLCanvasElement = document.getElementById(`crosshairs-${this.name}`) as HTMLCanvasElement;
      if (myCanvas && myCanvas.getContext) {
        const ctx = myCanvas.getContext('2d');
        ctx.clearRect(0, 0, myCanvas.width, myCanvas.height);

        if (this.showCrosshairs) {
          const crosshairSet = new CrosshairSet(
            this.name,
            this.ijkName,
            this.representation,
            this.view,
            myCanvas,
            this.iIndexSlice,
            this.jIndexSlice,
            this.kIndexSlice,
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
            this.trueAxis(this.name),
            trueColors,
          );
          this.drawLine(ctx, displayLine1);
          this.drawLine(ctx, displayLine2);
        }
      }
    },
    /** Place crosshairs at the location of a click event */
    placeCrosshairs(clickEvent) {
      const crosshairSet = new CrosshairSet(
        this.name,
        this.ijkName,
        this.representation,
        this.view,
        null,
        this.iIndexSlice,
        this.jIndexSlice,
        this.kIndexSlice,
      );
      const location = crosshairSet.locationOfClick(clickEvent);
      this.SET_SLICE_LOCATION(location);
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
    :class="{ fullscreen }"
    class="vtk-viewer"
    style="font-size: 20px"
  >
    <div
      v-if="name !== 'default'"
      :class="name"
      class="header"
    >
      <v-layout align-center>
        <v-slider
          v-mousetrap="[
            { bind: keyboardBindings[1], handler: () => changeSlice(slice + 1) },
            { bind: keyboardBindings[0], handler: () => changeSlice(slice - 1) },
          ]"
          :value="slice"
          :min="sliceDomain.min"
          :max="sliceDomain.max"
          :step="sliceDomain.step"
          class="slice-slider mt-0 mx-4"
          hide-details
          @input="changeSlice"
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
        :id="'crosshairs-' + name"
        ref="crosshairsCanvas"
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
  background: black;
  z-index: 0;
  display: flex;
  flex-direction: column;

  &.fullscreen {
    position: fixed;
    top: 48px;
    left: 55px;
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
    flex: 1 1 0;
    position: relative;
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
  }

  .viewer > div {
    flex: 1 1 0;
    position: relative;
    overflow-y: hidden;
    cursor: crosshair!important;
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
