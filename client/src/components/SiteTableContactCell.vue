<script>
import _ from 'lodash';

export default {
  name: 'SiteTableContactCell',
  props: {
    value: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      contacts: [],
      showMenu: false,
      nameRules: [(v) => !!v || 'Name is required'],
      emailRules: [
        (v) => !!v || 'E-mail is required',
        (v) => /.+@.+/.test(v) || 'E-mail must be valid',
      ],
    };
  },
  watch: {
    showMenu(value) {
      if (value) {
        this.contacts = _.cloneDeep(this.value) || [];
      }
    },
  },
  methods: {
    add() {
      this.contacts.push({ mode: 'to', name: '', email: '' });
    },
    remove(contact) {
      this.contacts.splice(this.contacts.indexOf(contact), 1);
    },
    save() {
      if (!this.$refs.form.validate()) {
        return;
      }
      this.showMenu = false;
      this.$emit('input', this.contacts);
    },
    cancel() {
      this.showMenu = false;
    },
  },
};
</script>

<template>
  <td>
    <v-menu
      v-model="showMenu"
      :close-on-content-click="false"
      :min-width="614"
      max-height="70vh"
      offset-x
      left
      class="v-small-dialog"
    >
      <div slot="activator">
        <div
          v-for="(contact, i) in value"
          :key="i"
        >
          {{ contact.mode }}: {{ contact.name }} ({{ contact.email }})
        </div>
      </div>
      <v-form
        ref="form"
        @submit.prevent="save"
      >
        <v-card>
          <v-container
            grid-list-md
            class="pb-0"
          >
            <v-layout v-if="!contacts.length">
              <v-flex>
                No contacts
              </v-flex>
            </v-layout>
            <v-layout
              v-for="(contact, i) in contacts"
              :key="i"
              align-center
            >
              <v-flex shrink>
                <v-select
                  v-model="contact.mode"
                  :items="['to', 'cc', 'bcc']"
                  style="width:50px"
                />
              </v-flex>
              <v-flex shrink>
                <v-text-field
                  v-model="contact.name"
                  label="Name"
                  name="miqa_name"
                  required
                  :rules="nameRules"
                  style="width:200px"
                />
              </v-flex>
              <v-flex shrink>
                <v-text-field
                  v-model="contact.email"
                  label="Email"
                  name="miqa_email"
                  type="email"
                  required
                  :rules="emailRules"
                  style="width:250px"
                />
              </v-flex>
              <v-flex shrink>
                <v-btn
                  text
                  icon
                  color="primary"
                  @click="remove(contact)"
                >
                  <v-icon>remove_circle</v-icon>
                </v-btn>
              </v-flex>
            </v-layout>
            <v-layout>
              <v-spacer />
              <v-flex shrink>
                <v-btn
                  text
                  icon
                  color="primary"
                  @click="add"
                >
                  <v-icon>add_circle</v-icon>
                </v-btn>
              </v-flex>
            </v-layout>
          </v-container>
          <v-card-actions>
            <v-spacer />
            <v-btn
              text
              @click="cancel"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              text
              type="submit"
            >
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-form>
    </v-menu>
  </td>
</template>
