<script>
export default {
  name: 'SiteTableDisplayNameCell',
  props: {
    value: {
      required: true,
      type: String,
    },
  },
  data() {
    return {
      displayName: '',
      showMenu: false,
      nameRules: [(v) => !!v || 'Name is required'],
    };
  },
  watch: {
    showMenu(value) {
      if (value) {
        this.displayName = this.value || '';
      }
    },
  },
  methods: {
    save() {
      if (!this.$refs.form.validate()) {
        return;
      }
      this.showMenu = false;
      this.$emit('input', this.displayName);
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
      class="v-small-dialog"
      lazy
    >
      <div slot="activator">
        {{ value }}
      </div>
      <v-form
        ref="form"
        @submit.prevent="save"
      >
        <v-card>
          <v-container
            grid-list-md
            class="py-2"
          >
            <v-layout>
              <v-flex>
                <v-text-field
                  v-model="displayName"
                  label="Display Name"
                  name="miqa_site_name"
                  :rules="nameRules"
                  style="width:220px"
                />
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
