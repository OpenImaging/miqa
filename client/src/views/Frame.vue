<script>
import _ from 'lodash';
import {
  mapState, mapActions, mapGetters,
} from 'vuex';

import Navbar from '@/components/Navbar.vue';
import ControlPanel from '@/components/ControlPanel.vue';
import ExperimentsView from '@/components/ExperimentsView.vue';
import VtkViewer from '@/components/VtkViewer.vue';
import { cleanFrameName } from '@/utils/helper';

export default {
  name: 'Frame',
  components: {
    Navbar,
    ExperimentsView,
    VtkViewer,
    ControlPanel,
  },
  inject: ['user'],
  computed: {
    ...mapState([
      'vtkViews',
      'scanCachedPercentage',
      'scanFrames',
      'loadingFrame',
      'errorLoadingFrame',
    ]),
    ...mapGetters([
      'currentFrame',
    ]),
    currentScanFrames() {
      return this.scanFrames[this.currentScan.id];
    },
  },
  watch: {
    currentScan(scan) {
      if (scan) {
        const last = _.head(scan.decisions);
        this.decision = last ? last.decision : null;
        this.decisionChanged = false;
        this.newNote = '';
      }
    },
  },
  async created() {
    this.debouncedFrameSliderChange = _.debounce(
      this.debouncedFrameSliderChange,
      30,
    );
    const { projectId, frameId } = this.$route.params;
    const frame = await this.getFrame({ frameId, projectId });
    if (frame) {
      await this.swapToFrame(frame);
    } else {
      this.$router.replace('/').catch(this.handleNavigationError);
    }
  },
  async beforeRouteUpdate(to, from, next) {
    const toFrame = await this.getFrame({ frameId: to.params.frameId, projectId: undefined });
    next(true);
    if (toFrame) {
      this.swapToFrame(toFrame);
    }
  },
  async beforeRouteLeave(to, from, next) {
    next(true);
  },
  methods: {
    ...mapActions([
      'loadProject',
      'reloadScan',
      'logout',
      'swapToFrame',
      'getFrame',
    ]),
    cleanFrameName,
    async logoutUser() {
      await this.logout();
      this.$router.go('/'); // trigger re-render into oauth flow
    },
    debouncedFrameSliderChange(index) {
      const frameId = this.currentScanFrames[index];
      this.$router.push(frameId).catch(this.handleNavigationError);
    },
    advanceLoop() {
      if (this.scanning) {
        this.updateFrame();
        this.nextAnimRequest = window.requestAnimationFrame(this.advanceLoop);
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
      width="350"
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
      row
      fill-height
    >
      <v-progress-circular
        :width="4"
        :size="50"
        color="primary"
        indeterminate
      />
    </v-layout>
    <template v-if="currentFrame">
      <v-flex class="layout-container">
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
          <div class="title">
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
    flex: 1 0 0px;

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
    background: #ffffff57;
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
  /*font-weight: bold;*/
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
