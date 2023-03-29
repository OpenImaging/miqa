<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'KeyboardShortcutDialog',
  props: {
    value: {
      type: Boolean,
      required: true,
    },
  },
  data: () => ({
    shortcuts: [
      ['Previous/next scan', [['↑', '↓']]],
      ['Previous/next frame', [['←', '→']]],
      [
        'Change slices',
        [
          ['q', 'w'],
          ['a', 's'],
          ['z', 'x'],
        ],
      ],
      ['Toggle fullscreen', [['e', 'd', 'c']]],
      ['Mark as usable/usable extra/questionable/unusable', [['u', 'i', 'o', 'p']]],
      ['Place crosshairs at location', [['click']]],
      ['Zooming', [['right button + dragging'], ['Ctrl + dragging'], ['Alt + dragging']]],
      ['Panning', [['shift + dragging']]],
      ['Cancel on confirm dialog', [['esc']]],
      ['Confirm on confirm dialog', [['enter']]],
    ],
  }),
  methods: {
    formatCodes(codes) {
      return codes
        .map((keylist) => keylist.map((keychar) => `<code>${keychar}</code>`).join(' / '))
        .join(', ');
    },
  },
});
</script>
<template>
  <v-dialog
    :value="value"
    max-width="600"
    scrollable
    @input="$emit('input', $event)"
  >
    <v-card>
      <v-card-title
        class="text-h6"
        primary-title
      >
        Keyboard shortcuts & Viewer Interaction
      </v-card-title>
      <v-divider />
      <v-card-text style="overflow-y:auto">
        <v-data-table
          :items="shortcuts"
          hide-default-footer
          hide-default-header
          disable-pagination
        >
          <template #item="{ item }">
            <tr>
              <td>{{ item[0] }}</td>
              <!-- eslint-disable vue/no-v-html -->
              <td v-html="formatCodes(item[1])" />
              <!-- eslint-enable vue/no-v-html -->
            </tr>
          </template>
        </v-data-table>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          color="primary"
          text
          @click="$emit('input', false)"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
