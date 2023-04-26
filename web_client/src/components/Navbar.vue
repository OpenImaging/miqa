<script lang="ts">
import {
  defineComponent,
  ref,
  computed,
} from 'vue';
import store from '@/store';
import router from '@/router';

import UserButton from '@/components/UserButton.vue';
import ScreenshotDialog from '@/components/ScreenshotDialog.vue';
import TimeoutDialog from '@/components/TimeoutDialog.vue';
import EmailDialog from '@/components/EmailDialog.vue';
import KeyboardShortcutDialog from '@/components/KeyboardShortcutDialog.vue';
import UserAvatar from '@/components/UserAvatar.vue';
import djangoClient from '@/django';

export default defineComponent({
  // eslint-disable-next-line vue/multi-word-component-names
  name: 'Navbar',
  components: {
    UserAvatar,
    UserButton,
    ScreenshotDialog,
    EmailDialog,
    TimeoutDialog,
    KeyboardShortcutDialog,
  },
  props: {
    frameView: {
      type: Boolean,
      default: false,
    },
  },
  setup() {
    const user = computed(() => store.state.me);
    const miqaConfig = computed(() => store.state.MIQAConfig);
    const emailDialog = ref(false);
    const keyboardShortcutDialog = ref(false);
    const advanceTimeoutId = ref();
    const documentationURL = 'https://openimaging.github.io/miqa/';
    const screenshots = computed(() => store.state.screenshots);
    const currentFrame = computed(() => store.getters.currentFrame);
    const currentScan = computed(() => store.getters.currentScan);
    const notes = computed(() => {
      if (currentScan.value) {
        return currentScan.value.notes;
      }
      return [];
    });

    async function logoutUser() {
      await djangoClient.logout();
      router.replace('/'); // trigger re-render into oauth flow
    }
    function openDocumentation() {
      window.open(documentationURL, '_blank');
    }

    return {
      miqaConfig,
      user,
      emailDialog,
      keyboardShortcutDialog,
      advanceTimeoutId,
      documentationURL,
      screenshots,
      currentFrame,
      notes,
      logoutUser,
      openDocumentation,
      djangoClient,
    };
  },
});
</script>

<template>
  <v-app-bar
    v-if="miqaConfig"
    app
    dense
  >
    <v-toolbar-title>
      <v-tooltip
        bottom
      >
        <template #activator="{ on }">
          <span v-on="on">MIQA</span>
        </template>
        <span>{{ miqaConfig.version || "Demo Instance" }}</span>
      </v-tooltip>
    </v-toolbar-title>
    <v-tabs
      class="navigation-tabs ml-3"
      background-color="transparent"
    >
      <v-tab
        to="/"
      >
        <v-icon>view_column</v-icon>
        Projects
      </v-tab>
    </v-tabs>
    <v-spacer />

    <div v-if="frameView">
      <v-btn
        icon
        class="mr-4"
        @click="keyboardShortcutDialog = true"
      >
        <v-icon>keyboard</v-icon>
      </v-btn>
      <v-btn
        :disabled="!currentFrame"
        icon
        class="mr-4"
        @click="emailDialog = true"
      >
        <v-badge
          :value="screenshots.length"
          right
        >
          <span
            slot="badge"
            dark
          >{{ screenshots.length }}</span>
          <v-icon>email</v-icon>
        </v-badge>
      </v-btn>
      <KeyboardShortcutDialog v-model="keyboardShortcutDialog" />
      <ScreenshotDialog />
      <EmailDialog
        v-model="emailDialog"
        :notes="notes"
      />
    </div>

    <v-btn
      elevation="0"
      class="mx-2"
      @click="openDocumentation"
    >
      Help
      <v-icon>mdi-open-in-new</v-icon>
    </v-btn>

    <UserAvatar
      v-if="user"
      :target-user="user"
    />
    <UserButton
      @logout="logoutUser()"
      @login="djangoClient.login()"
    />
    <TimeoutDialog />
  </v-app-bar>
</template>

<style lang="scss">
.v-toolbar .navigation-tabs.v-tabs {
  width: unset;

  .v-tabs__container--icons-and-text .v-tabs__div {
    min-width: 120px;
  }
}
</style>
