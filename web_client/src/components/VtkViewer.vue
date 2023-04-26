<script lang="ts">
import {
  defineComponent,
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
} from 'vue';
import { vec3 } from 'gl-matrix';
import store from '@/store';
import CrosshairSet from '../utils/crosshairs';
import fill2DView from '../utils/fill2DView';
import { VIEW_ORIENTATIONS, ijkMapping } from '../vtk/constants';

export default defineComponent({
  name: 'VtkViewer',
  components: {},
  props: {
    view: {
      required: true,
      type: Object,
    },
  },
  setup(props) {
    const viewer = ref();
    const crosshairsCanvas = ref();
    const slice = ref(null);
    const resized = ref(false); // helper to avoid size flickering
    const fullscreen = ref(false);
    const renderSubscription = ref();
    const resizeObserver = ref();
    const screenshotContainer = document.createElement('div');

    const proxyManager = computed(() => store.state.proxyManager);
    const loadingFrame = computed(() => store.state.loadingFrame);
    const showCrosshairs = computed(() => store.state.showCrosshairs);
    const iIndexSlice = computed(() => store.state.iIndexSlice);
    const jIndexSlice = computed(() => store.state.jIndexSlice);
    const kIndexSlice = computed(() => store.state.kIndexSlice);
    const currentWindowWidth = computed(() => store.state.currentWindowWidth);
    const currentWindowLevel = computed(() => store.state.currentWindowLevel);
    const renderOrientation = computed(() => store.state.renderOrientation);

    const currentFrame = computed(() => store.getters.currentFrame);
    const currentViewData = computed(() => store.getters.currentViewData);

    const setCurrentScreenshot = (ss) => store.commit('SET_CURRENT_SCREENSHOT', ss);
    const setCurrentVtkIndexSlices = (slices) => store.commit('SET_CURRENT_VTK_INDEX_SLICES', slices);
    const setSliceLocation = (loc) => store.commit('SET_SLICE_LOCATION', loc);

    const representation = computed(
      // Returning representation from VTK
      // force add dependency on currentFrame
      () => currentFrame.value
        && proxyManager.value.getRepresentation(null, props.view),
    );
    const sliceDomain = computed(() => {
      // Returns the range of valid values and their step for the slice property
      if (!representation.value) return null;
      return representation.value.getPropertyDomainByName('slice');
    });
    const name = computed(() => props.view.getName() as ('x' | 'y' | 'z'));
    const displayName = computed(() => {
      switch (name.value) {
        case 'x':
          return 'Sagittal';
        case 'y':
          return 'Coronal';
        case 'z':
          return 'Axial';
        default:
          return '';
      }
    });
    const ijkName = computed(() => ijkMapping[name.value] as ('i' | 'j' | 'k'));
    const keyboardBindings = computed(() => {
      switch (name.value) {
        case 'z':
          return ['q', 'w', 'e'];
        case 'x':
          return ['a', 's', 'd'];
        case 'y':
          return ['z', 'x', 'c'];
        default:
          return '';
      }
    });

    function findClosestColumnToVector(inputVector, matrix) {
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
    }
    function applyCurrentWindowLevel() {
      const representationProperty = representation.value.getActors()[0].getProperty();
      representationProperty.setColorWindow(currentWindowWidth.value);
      representationProperty.setColorLevel(currentWindowLevel.value);
    }
    function trueAxis(axisName) {
      if (!representation.value.getInputDataSet()) return undefined;
      const orientation = representation.value.getInputDataSet().getDirection();
      const axisNumber = VIEW_ORIENTATIONS[renderOrientation.value][axisName].axis;
      const axisOrientation = [
        orientation[axisNumber],
        orientation[3 + axisNumber],
        orientation[6 + axisNumber],
      ].map(
        (val) => Math.abs(val),
      );
      const axisOrdering = ['x', 'y', 'z'];
      return axisOrdering[
        axisOrientation.indexOf(Math.max(...axisOrientation))
      ];
    }
    function drawLine(ctx, displayLine) {
      if (!displayLine) return;
      ctx.strokeStyle = displayLine.color;
      ctx.beginPath();
      ctx.moveTo(...displayLine.start);
      ctx.lineTo(...displayLine.end);
      ctx.stroke();
    }
    async function takeScreenshot() {
      const dataURL = await props.view.captureImage();

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

      if (showCrosshairs.value) {
        const crosshairSet = new CrosshairSet(
          name.value,
          ijkName.value,
          representation.value,
          props.view,
          canvas,
          iIndexSlice.value,
          jIndexSlice.value,
          kIndexSlice.value,
        );
        const originalColors = {
          x: '#fdd835',
          y: '#4caf50',
          z: '#b71c1c',
        };
        const trueColors = Object.fromEntries(
          Object.entries(originalColors).map(([axisName, hex]) => [trueAxis(axisName), hex]),
        );
        const [displayLine1, displayLine2] = crosshairSet.getCrosshairsForAxis(
          trueAxis(name.value),
          trueColors,
        );
        drawLine(ctx, displayLine1);
        drawLine(ctx, displayLine2);
      }
      setCurrentScreenshot({
        name: `${currentViewData.value.experimentName}/${
          currentViewData.value.scanName
        }/${currentFrame.value.frame_number}/${displayName.value}`,
        dataURL: canvas.toDataURL('image/jpeg'),
      });
    }
    function toggleFullscreen() {
      fullscreen.value = !fullscreen.value;
      setTimeout(() => {
        viewer.value.style.width = 'inherit';
        viewer.value.style.width = `${viewer.value.clientWidth - 3}px`;
      }, 100);
    }
    function changeSlice(newValue) {
      slice.value = newValue;
    }
    function roundSlice(value) {
      if (!value) return '';
      return Math.round(value * 100) / 100;
    }
    function updateCrosshairs() {
      const myCanvas: HTMLCanvasElement = document.getElementById(`crosshairs-${name.value}`) as HTMLCanvasElement;
      if (myCanvas && myCanvas.getContext) {
        const ctx = myCanvas.getContext('2d');
        ctx.clearRect(0, 0, myCanvas.width, myCanvas.height);

        if (showCrosshairs.value) {
          const crosshairSet = new CrosshairSet(
            name.value,
            ijkName.value,
            representation.value,
            props.view,
            myCanvas,
            iIndexSlice.value,
            jIndexSlice.value,
            kIndexSlice.value,
          );
          const originalColors = {
            x: '#fdd835',
            y: '#4caf50',
            z: '#b71c1c',
          };
          const trueColors = Object.fromEntries(
            Object.entries(originalColors).map(([axisName, hex]) => [trueAxis(axisName), hex]),
          );
          const [displayLine1, displayLine2] = crosshairSet.getCrosshairsForAxis(
            trueAxis(name.value),
            trueColors,
          );
          drawLine(ctx, displayLine1);
          drawLine(ctx, displayLine2);
        }
      }
    }
    /** Place crosshairs at the location of a click event */
    function placeCrosshairs(clickEvent) {
      const crosshairSet = new CrosshairSet(
        name.value,
        ijkName.value,
        representation.value,
        props.view,
        null,
        iIndexSlice.value,
        jIndexSlice.value,
        kIndexSlice.value,
      );
      const location = crosshairSet.locationOfClick(clickEvent);
      setSliceLocation(location);
    }
    function cleanup() {
      props.view.setContainer(null);
      if (renderSubscription.value) {
        renderSubscription.value.unsubscribe();
        resizeObserver.value.unobserve(viewer.value);
      }
    }
    function initializeSlice() {
      slice.value = representation.value.getSlice();
    }
    function initializeView() {
      props.view.setContainer(viewer.value);
      fill2DView(props.view);
      // add scroll interaction to change slice
      props.view.getInteractor().onMouseWheel(() => {
        if (!loadingFrame.value) {
          slice.value = representation.value.getSlice();
        }
      });
      // add click interaction to place crosshairs
      props.view.getInteractor().onLeftButtonPress((event) => placeCrosshairs(event));
      // remove drag interaction to change window
      const targetManipulator = props.view.getInteractor()
        .getInteractorStyle().getMouseManipulators().find(
          (manipulator) => manipulator.getClassName() === 'vtkMouseRangeManipulator',
        );
      if (targetManipulator) {
        targetManipulator.setDragEnabled(false);
      }
      setTimeout(() => {
        resized.value = true;
      });
    }
    function initializeCamera() {
      const camera = props.view.getCamera();
      const orientation = representation.value.getInputDataSet().getDirection();

      let newViewUp = VIEW_ORIENTATIONS[renderOrientation.value][name.value].viewUp.slice();
      let newDirectionOfProjection = VIEW_ORIENTATIONS[
        renderOrientation.value
      ][name.value].directionOfProjection;
      newViewUp = findClosestColumnToVector(
        newViewUp,
        orientation,
      );
      newDirectionOfProjection = findClosestColumnToVector(
        newDirectionOfProjection,
        orientation,
      );

      camera.setDirectionOfProjection(...newDirectionOfProjection);
      camera.setViewUp(...newViewUp);

      props.view.resetCamera();
      fill2DView(props.view);
    }
    function prepareViewer() {
      initializeView();
      initializeSlice();
      initializeCamera();
      updateCrosshairs();
      renderSubscription.value = props.view.getInteractor().onRenderEvent(() => {
        updateCrosshairs();
      });
      resizeObserver.value = new window.ResizeObserver((entries) => {
        if (entries.length === 1 && viewer.value && crosshairsCanvas.value) {
          const width = viewer.value.clientWidth;
          const height = viewer.value.clientHeight;
          crosshairsCanvas.value.width = width;
          crosshairsCanvas.value.height = height;
          crosshairsCanvas.value.style.width = `${width}px`;
          crosshairsCanvas.value.style.height = `${height}px`;
          initializeCamera();
          updateCrosshairs();
        }
      });
      resizeObserver.value.observe(viewer.value);
      applyCurrentWindowLevel();
    }
    function keyPress(event) {
      if (['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName)) return;
      switch (event.key) {
        case keyboardBindings.value[0]:
          changeSlice(slice.value - 1);
          break;
        case keyboardBindings.value[1]:
          changeSlice(slice.value + 1);
          break;
        case keyboardBindings.value[2]:
          toggleFullscreen();
          break;
        default:
          break;
      }
    }

    watch(slice, (newSlice) => {
      representation.value.setSlice(newSlice);
      if (setCurrentVtkIndexSlices) {
        setCurrentVtkIndexSlices({
          indexAxis: ijkMapping[trueAxis(name.value)],
          value: representation.value.getSliceIndex(),
        });
      }
    });
    watch(iIndexSlice, updateCrosshairs);
    watch(jIndexSlice, updateCrosshairs);
    watch(kIndexSlice, updateCrosshairs);
    watch(showCrosshairs, updateCrosshairs);
    watch(representation, () => {
      cleanup();
      initializeSlice();
      initializeView();
    });
    watch(currentFrame, (oldFrame, newFrame) => {
      // Only runs when changing scans
      representation.value.setSlice(slice.value);
      applyCurrentWindowLevel();
      updateCrosshairs();
      // use this instead of currentScan watcher
      // currentScan is computed from currentFrame and technically
      // will change every time currentFrame has changed
      if (oldFrame.scan !== newFrame.scan) {
        initializeSlice();
        initializeCamera();
      }
    });

    onMounted(() => {
      prepareViewer();
      window.addEventListener('keypress', keyPress);
    });

    onBeforeUnmount(() => {
      cleanup();
      window.removeEventListener('keypress', keyPress);
    });

    return {
      viewer,
      name,
      displayName,
      sliceDomain,
      crosshairsCanvas,
      slice,
      resized,
      fullscreen,
      screenshotContainer,
      changeSlice,
      roundSlice,
      keyboardBindings,
      toggleFullscreen,
      takeScreenshot,
    };
  },
});
</script>

<template>
  <div
    :class="{ fullscreen }"
    class="vtk-viewer"
    style="font-size: 20px"
  >
    <div
      :class="name"
      class="header"
    >
      <v-layout align-center>
        <v-slider
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
