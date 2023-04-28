<script lang="ts">
import {
  defineComponent,
  computed,
  ref,
  watch,
  onMounted,
} from 'vue';
import _ from 'lodash';
import router from '@/router';
import store from '@/store';

import Navbar from '@/components/Navbar.vue';
import ControlPanel from '@/components/ControlPanel.vue';
import ExperimentsView from '@/components/ExperimentsView.vue';
import VtkViewer from '@/components/VtkViewer.vue';
import { ScanDecision } from '@/types';
import formatSize from '@/utils/helper';

export default defineComponent({
  name: 'ScanView',
  components: {
    Navbar,
    ExperimentsView,
    VtkViewer,
    ControlPanel,
  },
  setup() {
    const user = computed(() => store.state.me);
    const downloadLoaded = ref(0);
    const downloadTotal = ref(0);
    const decision = ref();
    const decisionChanged = ref(false);
    const newNote = ref('');

    const currentFrameId = computed(() => store.state.currentFrameId);
    const vtkViews = computed(() => store.state.vtkViews);
    const frames = computed(() => store.state.frames);
    const scanFrames = computed(() => store.state.scanFrames);
    const loadingFrame = computed(() => store.state.loadingFrame);
    const errorLoadingFrame = computed(() => store.state.errorLoadingFrame);
    const currentScan = computed(() => store.getters.currentScan);

    const loadScan = (scan) => store.dispatch('loadScan', scan);
    const swapToFrame = (info) => store.dispatch('swapToFrame', info);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);

    const currentFrame = computed(() => frames.value[currentFrameId.value]);
    const currentScanFrames = computed(() => scanFrames[currentScan.value.id]);
    const downloadProgressPercent = computed(
      () => (downloadTotal.value ? 100 * (downloadLoaded.value / downloadTotal.value) : 0),
    );
    const loadProgressMessage = computed(() => {
      if (downloadTotal.value && downloadLoaded.value === downloadTotal.value) {
        return 'Loading image viewer...';
      }
      return `Downloading image ${formatSize(downloadLoaded.value)} / ${formatSize(downloadTotal.value)}`;
    });

    /** Update the download progress */
    function onFrameDownloadProgress(e) {
      downloadLoaded.value = e.loaded;
      downloadTotal.value = e.total;
    }
    /** Loads a specific frame */
    async function swapToScan() {
      // Get the project/frame id's from the URL
      const { projectId, scanId } = router.app.$route.params;
      const scan = await loadScan({ scanId, projectId });
      const frame = frames.value[scanFrames.value[scan.id][0]];
      if (frame) {
        await swapToFrame({
          frame,
          onDownloadProgress: onFrameDownloadProgress,
        });
      } else {
        router.replace('/');
      }
    }

    watch(currentScan, (scan) => {
      if (scan) {
        const last: ScanDecision = _.head(scan.decisions);
        decision.value = last ? last.decision : null;
        decisionChanged.value = false;
        newNote.value = '';
      }
    });
    watch(currentFrameId, (frameId) => {
      swapToFrame({
        frame: frames.value[frameId],
        onDownloadProgress: onFrameDownloadProgress,
        loadAll: false,
      });
    });

    onMounted(() => {
      window.addEventListener('unauthorized', () => {
        setSnackbar('Server session expired. Try again.');
      });
    });

    return {
      user,
      downloadLoaded,
      downloadTotal,
      currentFrameId,
      vtkViews,
      frames,
      scanFrames,
      loadingFrame,
      errorLoadingFrame,
      currentFrame,
      currentScanFrames,
      downloadProgressPercent,
      loadProgressMessage,
      swapToScan,
    };
  },
  watch: {
    // Replaces `beforeRouteUpdate` and code in `created` handling frame load
    '$route.params.scanId': {
      handler: 'swapToScan',
      immediate: true,
    },
  },
});
</script>

<template>
  <v-layout
    class="frame"
    fill-height
    column
  >
    <Navbar frame-view />
    <v-navigation-drawer
      expand-on-hover
      permanent
      app
      width="350px"
    >
      <v-list>
        <v-list-item>
          <v-icon>fas fa-list</v-icon>
          <v-toolbar-title class="pl-5">
            Experiments
          </v-toolbar-title>
        </v-list-item>
        <v-list-item>
          <v-icon />
          <ExperimentsView
            class="mt-1"
            minimal
          />
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-layout
      v-if="loadingFrame"
      class="loading-indicator-container"
      align-center
      justify-center
      fill-height
    >
      <v-col>
        <v-row justify="center">
          <v-progress-circular
            :width="4"
            :size="56"
            :rotate="-90"
            :value="downloadProgressPercent"
            :indeterminate="downloadTotal === 0 || downloadTotal === downloadLoaded"
            color="primary"
          >
            {{ Math.round(downloadProgressPercent || 0) }}%
          </v-progress-circular>
        </v-row>
        <v-row
          justify="center"
          class="mt-2"
        >
          <div class="text-center">
            {{ loadProgressMessage }}
          </div>
        </v-row>
      </v-col>
    </v-layout>
    <template v-if="currentFrame">
      <v-flex
        class="layout-container"
      >
        <div class="my-layout">
          <div
            v-for="(vtkView, index) in vtkViews"
            :key="index"
            class="view"
          >
            <VtkViewer :view="vtkView" />
          </div>
        </div>
        <v-layout
          v-if="errorLoadingFrame"
          align-center
          justify-center
          fill-height
        >
          <div class="text-h6">
            Error loading this frame
          </div>
        </v-layout>
      </v-flex>
      <ControlPanel />
    </template>
  </v-layout>
</template>

<style lang="scss" scoped>
.my-layout {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;

  .view {
    position: relative;
    flex: 1 0 0;

    border: 1.5px solid white;
    border-top: none;
    border-bottom: none;

    &:first-child {
      border-left: none;
    }

    &:last-child {
      border-right: none;
    }
  }
}

.frame {
  .scans-bar {
    display: flex;
    flex-direction: column;
    height: 100%;

    .scans-view {
      overflow: auto;
    }
  }

  .experiment-note {
    max-width: 250px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .loading-indicator-container {
    background: #ffffffcc;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1;
  }

  .layout-container {
    position: relative;
  }

  .v-btn.smaller {
    height: 35px;
    width: 35px;
  }

  .bottom {
    > .container {
      position: relative;
    }

    .buttons {
      width: 100%;

      .v-btn {
        height: 36px;
        opacity: 1;
        flex: 1;
      }
    }
  }
}

.theme--light.v-btn.v-btn--disabled:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.theme--light.v-btn:not(.v-btn--flat):not(.v-btn--text):not(.v-btn-outlined),
.v-btn::before {
  background-color: transparent !important;
}

</style>

<style lang="scss">
.load-completion {
  font-size: 1.1em;
}

.justifyRight {
  text-align: right;
}

.frame {
  .v-text-field.small .v-input__control {
    min-height: 36px !important;
  }

  .note-field .v-input__control {
    min-height: 36px !important;
  }

  .v-input--slider.frame-slider {
    margin-top: 0;
  }
}

.v-list-item__content.note-history {
  width: 500px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
