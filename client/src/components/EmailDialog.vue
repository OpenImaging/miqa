<script>
import _ from 'lodash';
import { mapState, mapGetters, mapMutations } from 'vuex';

import EmailRecipientCombobox from './EmailRecipientCombobox.vue';

export default {
  name: 'EmailDialog',
  components: {
    EmailRecipientCombobox,
  },
  inject: ['djangoRest', 'user'],
  props: {
    value: {
      type: Boolean,
      required: true,
    },
    notes: {
      type: Array,
      default: () => [],
    },
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
  computed: {
    ...mapState(['screenshots']),
    ...mapGetters([
      'currentDataset',
      'currentSession',
      'siteMap',
    ]),
  },
  watch: {
    user(value) {
      if (value) {
        this.initialize();
      }
    },
    currentDataset(value) {
      if (value) {
        this.initialize();
      }
    },
    value(value) {
      if (value && !this.initialized) {
        this.initialize();
      }
    },
    notes(value) {
      if (value) {
        this.initialize();
      }
    },
  },
  methods: {
    ...mapMutations(['removeScreenshot']),
    initialize() {
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
      if (!this.currentSession) {
        return;
      }
      this.selectedScreenshots = [];
      this.toCandidates = [];
      this.ccCandidates = [];
      this.bccCandidates = [];
      const site = this.siteMap[this.currentSession.site];
      if (site && site.meta) {
        Object.values(site.meta).forEach((value) => {
          if (_.isArray(value)) {
            value.forEach((contact) => {
              switch (contact.mode) {
                case 'to':
                  this.toCandidates.push(contact);
                  break;
                case 'cc':
                  this.ccCandidates.push(contact);
                  break;
                case 'bcc':
                  this.bccCandidates.push(contact);
                  break;
                default:
                  break;
              }
            });
          }
        });
      }
      this.to = this.toCandidates.map((c) => c.name);
      this.cc = this.ccCandidates.map((c) => c.name);
      this.bcc = this.bccCandidates.map((c) => c.name);
      if (this.user) {
        this.bcc.push(this.user.email);
      }
      this.showCC = !!this.cc.length;
      this.showBCC = !!this.bcc.length;
      const experiment = `Regarding ${this.currentSession.experiment}, ${this.currentSession.name}`;
      this.subject = experiment;
      this.body = `Experiment: ${this.currentSession.experiment}
Scan: ${this.currentSession.name}`;
      if (this.notes) {
        this.body = `${this.body}
Notes:
`;
        this.body = this.notes
          .map(
            (note) => `${note.creator.first_name} ${note.creator.last_name}: ${note.created}\n${note.note}`,
          )
          .join('\n');
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
      await this.djangoRest.sendEmail({
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
};
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
                label="to"
                :candidates="toCandidates.map(c => c.name)"
                :required="true"
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
                label="cc"
                :candidates="ccCandidates.map(c => c.name)"
                :required="false"
              />
            </v-flex>
          </v-layout>
          <v-layout v-if="showBCC">
            <v-flex>
              <EmailRecipientCombobox
                v-model="bcc"
                label="bcc"
                :candidates="bccCandidates.map(c => c.name)"
                :required="false"
              />
            </v-flex>
          </v-layout>
          <v-layout>
            <v-flex>
              <v-text-field
                v-model="subject"
                label="Subject"
                placeholder=" "
                name="miqa_subject"
                autocomplete="on"
                :rules="[v => !!v || 'Subject is required']"
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
                <v-hover #default="{ hover }">
                  <v-card
                    class="screenshot"
                    :style="{
                      borderColor: getBorder(screenshot)
                    }"
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
            color="primary"
            text
            :loading="sending"
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
