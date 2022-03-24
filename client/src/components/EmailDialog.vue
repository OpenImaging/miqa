<script lang="ts">
import {
  defineComponent, inject, computed,
} from '@vue/composition-api';
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
    const { removeScreenshot } = store.commit;

    const user = inject('user') as User;

    return {
      screenshots,
      currentViewData,
      currentProject,
      currentFrame,
      currentScan,
      removeScreenshot,
      user,
    };
  },
  data: () => ({
    initialized: false,
    to: [],
    cc: [],
    bcc: [],
    toCandidates: [],
    ccCandidates: [],
    bccCandidates: [],
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
      this.selectedScreenshots = [];
      this.toCandidates = this.currentProject.settings.default_email_recipients.map(
        (emailString) => ({
          name: emailString,
        }),
      );
      this.ccCandidates = [];
      this.bccCandidates = [];
      this.to = this.toCandidates.map((c) => c.name);
      this.cc = this.ccCandidates.map((c) => c.name);
      this.bcc = this.bccCandidates.map((c) => c.name);
      if (this.user) {
        this.cc.push(this.user.email);
      }
      this.showCC = !!this.cc.length;
      this.showBCC = !!this.bcc.length;
      this.subject = `Regarding ${this.currentViewData.projectName}, ${this.currentViewData.experimentName}, ${this.currentScan.name}`;
      this.body = `Experiment: ${this.currentViewData.experimentName}\nScan: ${this.currentScan.name}\n`;
      if (this.currentViewData.scanDecisions.length > 0) {
        this.body += `Decisions:\n ${this.currentViewData.scanDecisions.map(
          (decision) => `    ${decision.creator.email} (${decision.created}): `
          + `${decision.decision.toUpperCase()} ${decision.note.length > 0 ? `, ${decision.note}` : ''}`,
        )}`;
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
      const toAddresses = this.to.map((recipient) => {
        const candidate = this.toCandidates.find((c) => c.name === recipient);
        return candidate ? candidate.email : recipient;
      });
      const ccAddresses = this.cc.map((recipient) => {
        const candidate = this.ccCandidates.find((c) => c.name === recipient);
        return candidate ? candidate.email : recipient;
      });
      const bccAddresses = this.bcc.map((recipient) => {
        const candidate = this.bccCandidates.find((c) => c.name === recipient);
        return candidate ? candidate.email : recipient;
      });
      this.sending = true;
      await djangoRest.sendEmail({
        to: toAddresses,
        cc: ccAddresses,
        bcc: bccAddresses,
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
          this.removeScreenshot(screenshot);
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
      @submit.prevent="send"
    >
      <v-card>
        <v-card-title class="headline grey lighten-4">
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
                :candidates="toCandidates.map(c => c.name)"
                :required="true"
                label="to"
              />
            </v-flex>
            <v-flex shrink>
              <a
                v-if="!showCC"
                class="px-2"
                @click="showCC = true"
              >cc</a>
              <a
                v-if="!showBCC"
                class="px-2"
                @click="showBCC = true"
              >bcc</a>
            </v-flex>
          </v-layout>
          <v-layout v-if="showCC">
            <v-flex>
              <EmailRecipientCombobox
                v-model="cc"
                :candidates="ccCandidates.map(c => c.name)"
                :required="false"
                label="cc"
              />
            </v-flex>
          </v-layout>
          <v-layout v-if="showBCC">
            <v-flex>
              <EmailRecipientCombobox
                v-model="bcc"
                :candidates="bccCandidates.map(c => c.name)"
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
                      borderColor: getBorder(screenshot)
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
                        @click.stop="removeScreenshot(screenshot)"
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
