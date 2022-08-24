<script lang="ts">
import { mapState, mapGetters } from 'vuex';
import { defineComponent } from '@vue/composition-api';

import UserButton from '@/components/UserButton.vue';
import ScreenshotDialog from '@/components/ScreenshotDialog.vue';
import TimeoutDialog from '@/components/TimeoutDialog.vue';
import EmailDialog from '@/components/EmailDialog.vue';
import KeyboardShortcutDialog from '@/components/KeyboardShortcutDialog.vue';
import UserAvatar from '@/components/UserAvatar.vue';
import djangoClient from '@/django';

export default defineComponent({
  name: 'Navbar',
  components: {
    UserAvatar,
    UserButton,
    ScreenshotDialog,
    EmailDialog,
    TimeoutDialog,
    KeyboardShortcutDialog,
  },
  inject: ['user', 'MIQAConfig'],
  props: {
    frameView: {
      type: Boolean,
      default: false,
    },
  },
  data: () => ({
    emailDialog: false,
    keyboardShortcutDialog: false,
    advanceTimeoutId: null,
    documentationURL: 'https://openimaging.github.io/miqa/',
  }),
  computed: {
    ...mapState([
      'screenshots',
    ]),
    ...mapGetters([
      'currentFrame',
    ]),
    notes() {
      if (this.currentScan) {
        return this.currentScan.notes;
      }
      return [];
    },
  },
  methods: {
    async logoutUser() {
      await djangoClient.logout();
      this.$router.go('/'); // trigger re-render into oauth flow
    },
    openDocumentation() {
      window.open(this.documentationURL, '_blank');
    },
  },
});
</script>

<template>
  <v-app-bar
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
        <span>{{ MIQAConfig.version.length > 0 ? MIQAConfig.version : "Demo Instance" }}</span>
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
      @login="djangoRest.login()"
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
