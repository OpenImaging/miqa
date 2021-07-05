<script>
export default {
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
      type: Array,
      default: () => [],
    },
    required: {
      type: Boolean,
      default: false,
    },
  },
  methods: {
    isValid(recipient) {
      if (this.candidates.indexOf(recipient) !== -1) {
        return true;
      }
      return /.+@.+/.test(recipient);
    },
    allValid(recipients) {
      const invalid = recipients.find((recipient) => !this.isValid(recipient));
      return invalid ? 'Recipient is not valid' : true;
    },
  },
};
</script>

<template>
  <v-combobox
    :value="value"
    :items="candidates"
    :label="label"
    multiple
    deletable-chips
    small-chips
    :rules="[
      allValid,
      v =>
        !!v.length || (required ? `at least one recipient is required` : true)
    ]"
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
