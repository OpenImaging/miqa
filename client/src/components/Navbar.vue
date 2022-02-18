<script lang="ts">
import { mapActions, mapState, mapGetters } from 'vuex';
import { computed, defineComponent } from '@vue/composition-api';

import UserButton from '@/components/UserButton.vue';
import ScreenshotDialog from '@/components/ScreenshotDialog.vue';
import TimeoutDialog from '@/components/TimeoutDialog.vue';
import EmailDialog from '@/components/EmailDialog.vue';
import KeyboardShortcutDialog from '@/components/KeyboardShortcutDialog.vue';
import UserAvatar from '@/components/UserAvatar.vue';

export default defineComponent({
  name: 'Navbar',
  inject: ['user'],
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
  data: () => ({
    emailDialog: false,
    keyboardShortcutDialog: false,
    advanceTimeoutId: null,
  }),
  setup() {
    const version = computed(() => process.env.VERSION);
    return { version };
  },
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
    ...mapActions(['logout']),
    async logoutUser() {
      await this.logout();
      this.$router.go('/'); // trigger re-render into oauth flow
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
        <span>v{{ version }}</span>
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
        @click="keyboardShortcutDialog = true"
        icon
        class="mr-4"
      >
        <v-icon>keyboard</v-icon>
      </v-btn>
      <v-btn
        :disabled="!currentFrame"
        @click="emailDialog = true"
        icon
        class="mr-4"
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

    <UserAvatar :target-user="user" />
    <UserButton
      @user="logoutUser()"
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
