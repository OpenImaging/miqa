<script lang="ts">
import _ from 'lodash';
import {
  mapActions,
  mapState,
} from 'vuex';

import Navbar from '@/components/Navbar.vue';
import ControlPanel from '@/components/ControlPanel.vue';
import ExperimentsView from '@/components/ExperimentsView.vue';
import VtkViewer from '@/components/VtkViewer.vue';
import { ScanDecision } from '@/types';
import formatSize from '@/utils/helper';

export default {
  name: 'ScanView',
  components: {
    Navbar,
    ExperimentsView,
    VtkViewer,
    ControlPanel,
  },
  inject: ['user'],
  data() {
    return {
      downloadLoaded: 0,
      downloadTotal: 0,
    };
  },
  computed: {
    ...mapState([
      'currentFrameId',
      'vtkViews',
      'frames',
      'scanFrames',
      'loadingFrame',
      'errorLoadingFrame',
      'currentScan',
    ]),
    currentScanFrames() {
      return this.scanFrames[this.currentScan.id];
    },
    downloadProgressPercent() {
      return 100 * (this.downloadLoaded / this.downloadTotal);
    },
    loadProgressMessage() {
      if (this.downloadTotal && this.downloadLoaded === this.downloadTotal) {
        return 'Loading image viewer...';
      }
      return `Downloading image ${formatSize(this.downloadLoaded)} / ${formatSize(this.downloadTotal)}`;
    },
    currentFrame() {
      return this.frames[this.currentFrameId];
    },
  },
  watch: {
    currentScan(scan) {
      if (scan) {
        const last: ScanDecision = _.head(scan.decisions);
        this.decision = last ? last.decision : null;
        this.decisionChanged = false;
        this.newNote = '';
      }
    },
    async currentFrameId(frameId) {
      await this.swapToFrame({
        frame: this.frames[frameId],
        onDownloadProgress: this.onFrameDownloadProgress,
        loadAll: false,
      });
    },
    // Replaces `beforeRouteUpdate` and code in `created` handling frame load
    '$route.params.scanId': {
      handler: 'swapToScan',
      immediate: true,
    },
  },
  mounted() {
    window.addEventListener('unauthorized', () => {
      this.$snackbar({
        text: 'Server session expired. Try again.',
        timeout: 6000,
      });
    });
  },
  methods: {
    ...mapActions([
      'loadProject',
      'swapToFrame',
      'loadScan',
    ]),
    /** Update the download progress */
    onFrameDownloadProgress(e) {
      this.downloadLoaded = e.loaded;
      this.downloadTotal = e.total;
    },
    /** Loads a specific frame */
    async swapToScan() {
      // Get the project/frame id's from the URL
      const { projectId, scanId } = this.$route.params;
      const scan = await this.loadScan({ scanId, projectId });
      const frame = this.frames[this.scanFrames[scan.id][0]];
      if (frame) {
        await this.swapToFrame({
          frame,
          onDownloadProgress: this.onFrameDownloadProgress,
        });
      } else {
        this.$router.replace('/').catch(this.handleNavigationError);
      }
    },
  },
};
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
