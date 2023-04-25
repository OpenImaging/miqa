<script lang="ts">
import {
  defineComponent, inject, computed,
} from 'vue';
import store from '@/store';
import { User } from '@/types';
import djangoRest from '@/django';
import EmailRecipientCombobox from './EmailRecipientCombobox.vue';

export default defineComponent({
  name: 'EmailDialog',
  components: {
    EmailRecipientCombobox,
  },
  inject: ['MIQAConfig'],
  props: {
    value: {
      type: Boolean,
      required: true,
    },
  },
  setup() {
    const screenshots = computed(() => store.state.screenshots);
    const currentViewData = computed(() => store.getters.currentViewData);
    const currentProject = computed(() => store.state.currentProject);
    const currentFrame = computed(() => store.getters.currentFrame);
    const currentScan = computed(() => store.getters.currentScan);
    const REMOVE_SCREENSHOT = store.commit('REMOVE_SCREENSHOT');

    const user = inject('user') as User;

    return {
      screenshots,
      currentViewData,
      currentProject,
      currentFrame,
      currentScan,
      REMOVE_SCREENSHOT,
      user,
    };
  },
  data: () => ({
    initialized: false,
    to: [],
    cc: [],
    bcc: [],
    showCC: false,
    showBCC: false,
    subject: '',
    body: '',
    selectedScreenshots: [],
    valid: true,
    sending: false,
  }),
  watch: {
    user(value) {
      if (value) {
        this.initialize();
      }
    },
    currentFrame(value) {
      if (value) {
        this.initialize();
      }
    },
    value(value) {
      if (value && !this.initialized) {
        this.initialize();
      }
    },
  },
  methods: {
    initialize() {
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
      if (!this.currentScan) {
        return;
      }
      this.selectedScreenshots = this.screenshots;
      this.to = this.currentProject.settings.default_email_recipients;
      this.cc = [];
      this.bcc = [];
      if (this.user) {
        this.cc.push(this.user.email);
      }
      this.showCC = !!this.cc.length;
      this.showBCC = !!this.bcc.length;
      this.subject = `Regarding ${this.currentViewData.projectName}, ${this.currentViewData.experimentName}, ${this.currentScan.name}`;
      this.body = `Project: ${this.currentViewData.projectName}\n`;
      this.body += `Experiment: ${this.currentViewData.experimentName}\n`;
      this.body += `Scan: ${this.currentScan.name}`;
      if (this.currentScan.link) this.body += ` (${this.currentScan.link})`;
      if (this.currentScan.subjectID) this.body += `, Subject: ${this.currentScan.subjectID}`;
      if (this.currentScan.sessionID) this.body += `, Session: ${this.currentScan.sessionID}`;
      this.body += '\n';
      if (this.currentViewData.scanDecisions.length > 0) {
        this.body += `Decisions:\n${this.currentViewData.scanDecisions.map(
          (decision) => `    ${decision.creator.email} (${decision.created}): `
          + `${decision.decision.toUpperCase()} ${decision.note.length > 0 ? `, ${decision.note}` : ''}`,
        ).join('\n')}`;
      }
      this.initialized = true;
    },
    toggleScreenshotSelection(screenshot) {
      const index = this.selectedScreenshots.indexOf(screenshot);
      if (index === -1) {
        this.selectedScreenshots.push(screenshot);
      } else {
        this.selectedScreenshots.splice(index, 1);
      }
    },
    async send() {
      if (!this.$refs.form.validate()) {
        return;
      }
      this.sending = true;
      await djangoRest.sendEmail({
        to: this.to,
        cc: this.cc,
        bcc: this.bcc,
        subject: this.subject,
        body: this.body,
        screenshots: this.screenshots.filter(
          (screenshot) => this.selectedScreenshots.indexOf(screenshot) !== -1,
        ),
      });
      this.sending = false;
      this.$emit('input', false);
      this.initialized = false;
      for (let i = this.screenshots.length - 1; i >= 0; i -= 1) {
        const screenshot = this.screenshots[i];
        if (this.selectedScreenshots.indexOf(screenshot) !== -1) {
          this.REMOVE_SCREENSHOT(screenshot);
        }
      }
      this.selectedScreenshots = [];
    },
    getBorder(screenshot) {
      if (this.selectedScreenshots.indexOf(screenshot) === -1) {
        return 'transparent';
      }
      return this.$vuetify.theme.currentTheme.primary;
    },
  },
});
</script>

<template>
  <v-dialog
    :value="value"
    max-width="60%"
    @input="$emit('input', $event)"
  >
    <v-form
      ref="form"
      v-model="valid"
      @submit.prevent="send"
    >
      <v-card>
        <v-card-title class="text-h5 grey lighten-4">
          Send email
          <v-spacer />
          <v-btn
            small
            icon
            class="ma-0"
            @click="$emit('input', false)"
          >
            <v-icon>close</v-icon>
          </v-btn>
        </v-card-title>
        <v-container
          grid-list-sm
          class="py-0"
        >
          <v-layout align-center>
            <v-flex>
              <EmailRecipientCombobox
                v-model="to"
                :candidates="to"
                :required="true"
                label="to"
              />
            </v-flex>
            <v-flex shrink>
              <a
                v-if="!showCC"
                class="px-2"
                @click="showCC = true"
                @keydown="showCC = true"
              >cc</a>
              <a
                v-if="!showBCC"
                class="px-2"
                @click="showBCC = true"
                @keydown="showBCC = true"
              >bcc</a>
            </v-flex>
          </v-layout>
          <v-layout v-if="showCC">
            <v-flex>
              <EmailRecipientCombobox
                v-model="cc"
                :candidates="cc"
                :required="false"
                label="cc"
              />
            </v-flex>
          </v-layout>
          <v-layout v-if="showBCC">
            <v-flex>
              <EmailRecipientCombobox
                v-model="bcc"
                :candidates="bcc"
                :required="false"
                label="bcc"
              />
            </v-flex>
          </v-layout>
          <v-layout>
            <v-flex>
              <v-text-field
                v-model="subject"
                :rules="[v => !!v || 'Subject is required']"
                label="Subject"
                placeholder=" "
                name="miqa_subject"
                autocomplete="on"
                required
              />
            </v-flex>
          </v-layout>
          <v-layout>
            <v-flex>
              <v-textarea
                v-model="body"
                label="Body"
                rows="8"
              />
            </v-flex>
          </v-layout>
          <template v-if="screenshots.length">
            <div class="caption">
              Include screenshots
            </div>
            <v-layout class="screenshot-row">
              <v-flex
                v-for="(screenshot, index) of screenshots"
                :key="index"
                shrink
              >
                <v-hover v-slot="{ hover }">
                  <v-card
                    :style="{
                      borderColor: getBorder(screenshot),
                    }"
                    class="screenshot"
                    @click="toggleScreenshotSelection(screenshot)"
                  >
                    <v-img
                      :src="screenshot.dataURL"
                      aspect-ratio="1"
                    />
                    <v-card-text class="text-truncate">
                      <v-tooltip top>
                        <template #activator="{ on }">
                          <span v-on="on">{{ screenshot.name }}</span>
                        </template>
                        <span>{{ screenshot.name }}</span>
                      </v-tooltip>
                    </v-card-text>
                    <v-fade-transition>
                      <v-btn
                        v-if="hover"
                        fab
                        small
                        color="primary"
                        class="close"
                        @click.stop="REMOVE_SCREENSHOT(screenshot)"
                      >
                        <v-icon>close</v-icon>
                      </v-btn>
                    </v-fade-transition>
                  </v-card>
                </v-hover>
              </v-flex>
            </v-layout>
          </template>
        </v-container>
        <v-card-actions>
          <v-spacer />
          <v-btn
            :loading="sending"
            :disabled="!valid"
            color="primary"
            text
            type="submit"
          >
            Send
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<style lang="scss" scoped>
.caption {
  color: rgba(0, 0, 0, 0.54);
}

.screenshot-row {
  overflow-x: auto;

  .screenshot {
    width: 160px;
    border: 2px solid transparent;

    .v-btn.close {
      height: 25px;
      width: 25px;
      position: absolute;
      top: 0;
      right: 0;

      .v-icon {
        font-size: 14px;
      }
    }
  }
}
</style>
