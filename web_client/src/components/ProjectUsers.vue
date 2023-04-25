<script lang="ts">
import { mapState, mapActions, mapMutations } from 'vuex';
import UserAvatar from '@/components/UserAvatar.vue';
import djangoRest from '@/django';

export default {
  name: 'ProjectUsers',
  components: {
    UserAvatar,
  },
  inject: ['user'],
  data: () => ({
    showAddMemberOverlay: false,
    showAddCollaboratorOverlay: false,
    selectedPermissionSet: {},
    emailList: [],
  }),
  computed: {
    ...mapState([
      'currentProject',
      'allUsers',
    ]),
    permissions() {
      return this.currentProject.settings.permissions;
    },
    members() {
      const members = [
        ...this.currentProject.settings.permissions.tier_1_reviewer,
        ...this.currentProject.settings.permissions.tier_2_reviewer,
      ];
      return members;
    },
    collaborators() {
      return this.currentProject.settings.permissions.collaborator;
    },
    emailOptions() {
      return this.members.concat(this.collaborators).map(
        (user) => user.email,
      );
    },
    emailListChanged() {
      return (
        JSON.stringify(this.emailList) !== JSON.stringify(
          this.currentProject.settings.default_email_recipients,
        )
      );
    },
    changesMade() {
      return JSON.stringify(this.permissions)
        !== JSON.stringify(this.selectedPermissionSet);
    },
    userCanEditProject() {
      return this.user.is_superuser || this.user.email === this.currentProject.creator;
    },
  },
  watch: {
    currentProject(newProj) {
      this.selectedPermissionSet = { ...newProj.settings.permissions };
      this.emailList = this.currentProject.settings.default_email_recipients;
    },
  },
  mounted() {
    this.loadAllUsers();
    this.selectedPermissionSet = { ...this.permissions };
    this.emailList = this.currentProject.settings.default_email_recipients;
  },
  methods: {
    ...mapActions([
      'loadAllUsers',
    ]),
    ...mapMutations([
      'SET_CURRENT_PROJECT',
    ]),
    getGroup(user) {
      return Object.entries(this.permissions).filter(
        ([, value]) => (value as any).includes(user),
      )[0][0].replace(/_/g, ' ');
    },
    userDisplayName(user) {
      if (!user.first_name || !user.last_name) {
        return user.username;
      }
      return `${user.first_name} ${user.last_name}`;
    },
    allEmails(inputs) {
      for (let i = 0; i < inputs.length; i += 1) {
        const match = String(inputs[i])
          .toLowerCase()
          .match(
            /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/,
          );
        if (!(match && match.length > 0)) return `${inputs[i]} is not a valid email address.`;
      }
      return true;
    },
    async savePermissions() {
      const newSettings = { ...this.currentProject.settings };
      newSettings.permissions = Object.fromEntries(
        Object.entries(this.selectedPermissionSet).map(
          ([group, list]) => [group, (list as any[]).map((user) => user.username || user)],
        ),
      );
      try {
        const resp = await djangoRest.setProjectSettings(this.currentProject.id, newSettings);
        this.showAddMemberOverlay = false;
        this.showAddCollaboratorOverlay = false;
        const changedProject = { ...this.currentProject };
        changedProject.settings.permissions = resp.permissions;
        this.SET_CURRENT_PROJECT(changedProject);
      } catch (e) {
        this.$snackbar({
          text: 'Failed to save permissions.',
          timeout: 6000,
        });
      }
    },
    async saveEmails() {
      const newSettings = { ...this.currentProject.settings };
      newSettings.default_email_recipients = this.emailList;
      delete newSettings.permissions;
      try {
        const resp = await djangoRest.setProjectSettings(this.currentProject.id, newSettings);
        const changedProject = { ...this.currentProject };
        changedProject.settings.default_email_recipients = resp.default_email_recipients;
        this.SET_CURRENT_PROJECT(changedProject);
      } catch (e) {
        this.$snackbar({
          text: 'Failed to save email list.',
          timeout: 6000,
        });
      }
    },
  },
};
</script>

<template>
  <v-card class="flex-card">
    <v-subheader>Users</v-subheader>
    <v-container class="pl-8">
      <v-row
        no-gutters
        class="pb-3"
      >
        <v-col cols="12">
          Project Creator:
          {{ currentProject.creator }}
        </v-col>
      </v-row>
      <v-row
        no-gutters
        class="pb-3"
      >
        <v-col cols="12">
          Members
          <v-tooltip
            v-if="userCanEditProject"
            bottom
            style="display: inline; padding-left: 5px"
          >
            <template #activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                color="blue darken-2"
                v-on="on"
                @click="showAddMemberOverlay = true"
              >
                mdi-cog
              </v-icon>
            </template>
            <span>Grant/revoke review access</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <div
        v-for="(user, index) in members"
        :key="'member_' + index"
        class="py-1 d-flex"
      >
        <UserAvatar :target-user="user" />
        {{ user.first_name }} {{ user.last_name }} ({{ user.username }})
        <span class="gray-info">
          {{ getGroup(user) }}
        </span>
      </div>
      <v-row
        no-gutters
        class="pt-5 pb-3"
      >
        <v-col cols="12">
          Collaborators <span class="gray-info">(Read only)</span>
          <v-tooltip
            v-if="userCanEditProject"
            bottom
            style="display: inline; padding-left: 5px"
          >
            <template #activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                color="blue darken-2"
                v-on="on"
                @click="showAddCollaboratorOverlay = true"
              >
                mdi-cog
              </v-icon>
            </template>
            <span>Grant/revoke read access</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <div
        v-for="(user, index) in collaborators"
        :key="'collaborator_' + index"
        class="py-1 d-flex"
      >
        <UserAvatar :target-user="user" />
        {{ user.first_name }} {{ user.last_name }} ({{ user.username }})
      </div>
      <v-row
        no-gutters
        class="pt-5"
      >
        <v-col cols="12">
          Default email recipients
          <v-tooltip
            bottom
            style="display: inline; padding-left: 5px"
          >
            <template #activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                color="blue darken-2"
                small
                v-on="on"
              >
                info
              </v-icon>
            </template>
            <span>Emails sent from MIQA about this project
              will include this list of recipients by default.</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row
        no-gutters
      >
        <v-col cols="12">
          <v-combobox
            v-model="emailList"
            :items="emailOptions"
            :disabled="!userCanEditProject"
            :label="userCanEditProject ? 'Select or type an email' : ''"
            :rules="[allEmails]"
            multiple
            chips
            deletable-chips
            hide-selected
            style="max-width:500px;"
          >
            <template #append-outer>
              <v-btn
                v-if="userCanEditProject"
                :disabled="!emailListChanged"
                color="primary"
                @click="saveEmails"
              >
                Save
              </v-btn>
            </template>
          </v-combobox>
        </v-col>
      </v-row>

      <v-overlay
        :value="showAddMemberOverlay"
        :dark="false"
      >
        <v-card
          class="dialog-box"
        >
          <v-btn
            icon
            style="float: right"
            @click="showAddMemberOverlay = false"
          >
            <v-icon
              large
              color="red darken-2"
            >
              mdi-close
            </v-icon>
          </v-btn>
          <v-card-title>
            Grant/Revoke Review Access
          </v-card-title>
          <v-select
            v-model="selectedPermissionSet.tier_1_reviewer"
            :items="allUsers"
            :item-text="userDisplayName"
            item-value="username"
            label="Select Tier 1 Reviewers"
            multiple
            clearable
            chips
            deletable-chips
            hint="Select Users by username"
            persistent-hint
            append-icon="mdi-account-search"
          />
          <br>
          <v-select
            v-model="selectedPermissionSet.tier_2_reviewer"
            :items="allUsers"
            :item-text="userDisplayName"
            item-value="username"
            label="Select Tier 2 Reviewers"
            multiple
            clearable
            chips
            deletable-chips
            hint="Select Users by username"
            persistent-hint
            append-icon="mdi-account-search"
          />
          <br>
          <v-btn
            :disabled="!changesMade"
            color="primary"
            block
            @click="savePermissions"
          >
            Save changes
          </v-btn>
        </v-card>
      </v-overlay>
      <v-overlay
        :value="showAddCollaboratorOverlay"
        :dark="false"
      >
        <v-card
          class="dialog-box"
        >
          <v-btn
            icon
            style="float: right"
            @click="showAddCollaboratorOverlay = false"
          >
            <v-icon
              large
              color="red darken-2"
            >
              mdi-close
            </v-icon>
          </v-btn>
          <v-card-title>
            Grant/Revoke Read Access
          </v-card-title>
          <v-select
            v-model="selectedPermissionSet.collaborator"
            :items="allUsers"
            :item-text="userDisplayName"
            item-value="username"
            label="Select Collaborators"
            multiple
            clearable
            chips
            deletable-chips
            hint="Select Users by username"
            persistent-hint
            append-icon="mdi-account-search"
          />
          <br>
          <v-btn
            :disabled="!changesMade"
            color="primary"
            block
            @click="savePermissions"
          >
            Save changes
          </v-btn>
        </v-card>
      </v-overlay>
    </v-container>
  </v-card>
</template>

<style lang="scss" scoped>
.gray-info {
  color: gray;
  padding-left: 10px;
  text-transform: capitalize;
}
.dialog-box {
  width: 40vw;
  min-height: 20vw;
  padding: 20px;
  background-color: white!important;
  color: #333333 !important;
}
</style>
