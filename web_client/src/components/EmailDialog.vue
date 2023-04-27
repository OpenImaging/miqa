<script lang="ts">
import {
  defineComponent,
  computed,
  ref,
  watch,
} from 'vue';
import store from '@/store';
import djangoRest from '@/django';
import EmailRecipientCombobox from './EmailRecipientCombobox.vue';

export default defineComponent({
  name: 'EmailDialog',
  components: {
    EmailRecipientCombobox,
  },
  props: {
    value: {
      type: Boolean,
      required: true,
    },
  },
  setup(props, context) {
    const user = computed(() => store.state.me);
    const initialized = ref(false);
    const to = ref([]);
    const cc = ref([]);
    const bcc = ref([]);
    const showCC = ref(false);
    const showBCC = ref(true);
    const subject = ref('');
    const body = ref('');
    const selectedScreenshots = ref([]);
    const valid = ref(true);
    const sending = ref(false);
    const form = ref();

    const screenshots = computed(() => store.state.screenshots);
    const currentViewData = computed(() => store.getters.currentViewData);
    const currentProject = computed(() => store.state.currentProject);
    const currentFrame = computed(() => store.getters.currentFrame);
    const currentScan = computed(() => store.getters.currentScan);
    const removeScreenshot = (ss) => store.commit('REMOVE_SCREENSHOT', ss);

    function initialize() {
      if (initialized.value) return;
      if (form.value) {
        form.value.resetValidation();
      }
      if (!currentScan.value) {
        return;
      }
      selectedScreenshots.value = screenshots.value;
      to.value = currentProject.value.settings.default_email_recipients;
      cc.value = [];
      bcc.value = [];
      if (user.value) {
        cc.value.push(user.value.email);
      }
      showCC.value = !!cc.value.length;
      showBCC.value = !!bcc.value.length;
      subject.value = `Regarding ${currentViewData.value.projectName}, ${currentViewData.value.experimentName}, ${currentScan.value.name}`;
      body.value = `Project: ${currentViewData.value.projectName}\n`;
      body.value += `Experiment: ${currentViewData.value.experimentName}\n`;
      body.value += `Scan: ${currentScan.value.name}`;
      if (currentScan.value.link) body.value += ` (${currentScan.value.link})`;
      if (currentScan.value.subjectID) body.value += `, Subject: ${currentScan.value.subjectID}`;
      if (currentScan.value.sessionID) body.value += `, Session: ${currentScan.value.sessionID}`;
      body.value += '\n';
      if (currentViewData.value.scanDecisions.length > 0) {
        body.value += `Decisions:\n${currentViewData.value.scanDecisions.map(
          (decision) => `    ${decision.creator.email} (${decision.created}): `
          + `${decision.decision.toUpperCase()} ${decision.note.length > 0 ? `, ${decision.note}` : ''}`,
        ).join('\n')}`;
      }
      initialized.value = true;
    }
    function toggleScreenshotSelection(screenshot) {
      const index = selectedScreenshots.value.indexOf(screenshot);
      if (index === -1) {
        selectedScreenshots.value.push(screenshot);
      } else {
        selectedScreenshots.value.splice(index, 1);
      }
    }
    async function send() {
      if (!form.value.validate()) {
        return;
      }
      sending.value = true;
      await djangoRest.sendEmail({
        to: to.value,
        cc: cc.value,
        bcc: bcc.value,
        subject: subject.value,
        body: body.value,
        screenshots: screenshots.value.filter(
          (screenshot) => selectedScreenshots.value.indexOf(screenshot) !== -1,
        ),
      });
      sending.value = false;
      context.emit('input', false);
      initialized.value = false;
      for (let i = screenshots.value.length - 1; i >= 0; i -= 1) {
        const screenshot = screenshots.value[i];
        if (selectedScreenshots.value.indexOf(screenshot) !== -1) {
          removeScreenshot(screenshot);
        }
      }
      selectedScreenshots.value = [];
    }
    function getBorder(screenshot) {
      if (selectedScreenshots.value.indexOf(screenshot) === -1) {
        return 'transparent';
      }
      return 'blue';
    }

    watch(user, initialize);
    watch(currentFrame, initialize);

    return {
      initialized,
      to,
      cc,
      bcc,
      showCC,
      showBCC,
      subject,
      body,
      selectedScreenshots,
      valid,
      sending,
      form,
      screenshots,
      currentViewData,
      currentProject,
      currentFrame,
      currentScan,
      removeScreenshot,
      user,
      send,
      getBorder,
      toggleScreenshotSelection,
    };
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
