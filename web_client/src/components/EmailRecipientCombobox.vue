<script lang="ts">
import { defineComponent, PropType } from 'vue';

export default defineComponent({
  name: 'EmailRecipientCombobox',
  props: {
    label: {
      type: String,
      required: true,
    },
    value: {
      required: true,
      type: Array,
    },
    candidates: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    required: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    function isValid(recipient: string) {
      if (props.candidates.indexOf(recipient) !== -1) {
        return true;
      }
      return /.+@.+/.test(recipient);
    }
    function allValid(recipients: Array<string>) {
      const invalid = recipients.find((recipient) => !isValid(recipient));
      return invalid ? 'Recipient is not valid' : true;
    }

    return {
      isValid,
      allValid,
    };
  },
});
</script>

<template>
  <v-combobox
    :value="value"
    :items="candidates"
    :label="label"
    :rules="[
      allValid,
      v =>
        !!v.length || (required ? `at least one recipient is required` : true),
    ]"
    multiple
    deletable-chips
    small-chips
    hide-selected
    @input="$emit('input', $event)"
  >
    <template #selection="{ item, parent, selected }">
      <v-chip
        :key="JSON.stringify(item)"
        :color="isValid(item) ? '' : 'error'"
        :input-value="selected"
        small
        close
        @input="parent.selectItem(item)"
        @click:close="parent.selectItem(item)"
      >
        {{ item }}
      </v-chip>
    </template>
  </v-combobox>
</template>
