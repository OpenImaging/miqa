<script>
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
  }),
  computed: {
    ...mapState(['currentProject', 'allUsers']),
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
    changesMade() {
      return JSON.stringify(this.permissions)
        !== JSON.stringify(this.selectedPermissionSet);
    },
  },
  watch: {
    currentProject(newProj) {
      this.selectedPermissionSet = { ...newProj.settings.permissions };
    },
  },
  mounted() {
    this.$store.dispatch('loadAllUsers');
    this.selectedPermissionSet = { ...this.permissions };
  },
  methods: {
    ...mapActions(['loadAllUsers']),
    ...mapMutations(['setCurrentProject']),
    getGroup(user) {
      return Object.entries(this.permissions).filter(
        ([, value]) => value.includes(user),
      )[0][0].replace(/_/g, ' ');
    },
    async savePermissions() {
      const newSettings = { ...this.currentProject.settings };
      newSettings.permissions = Object.fromEntries(
        Object.entries(this.selectedPermissionSet).map(
          ([group, list]) => [group, list.map((user) => user.username || user)],
        ),
      );
      try {
        const resp = await djangoRest.setSettings(this.currentProject.id, newSettings);
        this.showAddMemberOverlay = false;
        this.showAddCollaboratorOverlay = false;
        const changedProject = { ...this.currentProject };
        changedProject.settings.permissions = resp.permissions;
        this.setCurrentProject(changedProject);
      } catch (e) {
        this.$snackbar({
          text: 'Failed to save permissions.',
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
          Members
          <v-tooltip
            v-if="user.is_superuser"
            bottom
            style="display: inline; padding-left: 5px"
          >
            <template v-slot:activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                v-on="on"
                @click="showAddMemberOverlay = true"
                color="blue darken-2"
              >
                mdi-cog
              </v-icon>
            </template>
            <span>Grant/revoke review access</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row
        v-for="(user, index) in members"
        :key="'member_'+index"
        no-gutters
        class="py-1"
      >
        <v-col cols="1">
          <UserAvatar :targetUser="user" />
        </v-col>
        <v-col cols="11">
          {{ user.username }}
          <span class="gray-info">
            {{ getGroup(user) }}
          </span>
        </v-col>
      </v-row>
      <v-row
        no-gutters
        class="pt-5 pb-3"
      >
        <v-col cols="12">
          Collaborators <span class="gray-info">(Read only)</span>
          <v-tooltip
            v-if="user.is_superuser"
            bottom
            style="display: inline; padding-left: 5px"
          >
            <template v-slot:activator="{ on, attrs }">
              <v-icon
                v-bind="attrs"
                v-on="on"
                @click="showAddCollaboratorOverlay = true"
                color="blue darken-2"
              >
                mdi-cog
              </v-icon>
            </template>
            <span>Grant/revoke read access</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row
        v-for="(user, index) in collaborators"
        :key="'collaborator_'+index"
        no-gutters
        class="py-1"
      >
        <v-col cols="1">
          <UserAvatar :targetUser="user" />
        </v-col>
        <v-col cols="11">
          {{ user.username }}
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
            @click="showAddMemberOverlay = false"
            icon
            style="float: right"
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
            item-text="username"
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
            item-text="username"
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
            @click="savePermissions"
            color="primary"
            block
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
            @click="showAddCollaboratorOverlay = false"
            icon
            style="float: right"
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
            item-text="username"
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
            @click="savePermissions"
            color="primary"
            block
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
  color: '#333333'!important;
}
</style>
