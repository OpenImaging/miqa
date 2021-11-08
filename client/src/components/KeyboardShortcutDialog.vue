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
      ['Next frame', [['→']]],
      ['Previous frame', [['←']]],
      [
        'Change slices',
        [
          ['q', 'w'],
          ['a', 's'],
          ['z', 'x'],
        ],
      ],
      ['Toggle fullscreen', [['e', 'd', 'c']]],
      ['Zooming', [['right button + dragging']]],
      ['Panning', [['shift + dragging']]],
      ['Cancel on confirm dialog', [['esc']]],
      ['Increase/decrease window', [['=', '-']]],
      ['Increase/decrease window level', [['[', ']']]],
      ['Focus to note', [['n']]],
      ['Show note history', [['h']]],
      ['Unfocus from note', [['esc']]],
      ['Mark as bad/good/usable extra', [['b', 'g', 'u']]],
      ['Save', [['alt + s']]],
      ['Save on confirm dialog', [['y']]],
      ["Don't save on confirm dialog", [['n']]],
      ['Cancel on confirm dialog', [['esc']]],
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
    @input="$emit('input', $event)"
    max-width="500"
    scrollable
  >
    <v-card>
      <v-card-title
        class="title"
        primary-title
      >
        Keyboard shortcuts
      </v-card-title>
      <v-divider />
      <v-card-text style="height: 500px;">
        <v-data-table
          :items="shortcuts"
          hide-default-footer
          hide-default-header
        >
          <template v-slot:item="{ item }">
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
          @click="$emit('input', false)"
          color="primary"
          text
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
