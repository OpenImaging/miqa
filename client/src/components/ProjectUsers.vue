<script>
import { mapState } from 'vuex';
import UserAvatar from '@/components/UserAvatar.vue';

export default {
  name: 'ProjectUsers',
  components: {
    UserAvatar,
  },
  computed: {
    ...mapState(['currentProject']),
    permissions() {
      return this.currentProject.settings.permissions;
    },
    members() {
      const members = [...this.permissions.tier_1_reviewer];
      members.push(...this.permissions.tier_2_reviewer);
      return members;
    },
    collaborators() {
      return this.permissions.collaborator;
    },
  },
  mounted() {
    console.log(this.permissions);
  },
  methods: {
    getGroup(user) {
      return Object.entries(this.permissions).filter(
        ([, value]) => value.includes(user),
      )[0][0].replace(/_/g, ' ');
    },
  },
};
</script>

<template>
  <v-container class="pl-8">
    <v-row>
      <v-col cols="12">
        Members
      </v-col>
    </v-row>
    <v-row
      v-for="(user, index) in members"
      :key="index"
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
    <v-row>
      <v-col cols="12">
        Collaborators <span class="gray-info">(Read only)</span>
      </v-col>
    </v-row>
    <v-row
      v-for="(user, index) in collaborators"
      :key="index"
    >
      <v-col cols="1">
        <UserAvatar :targetUser="user" />
      </v-col>
      <v-col cols="11">
        {{ user.username }}
      </v-col>
    </v-row>
  </v-container>
</template>

<style lang="scss" scoped>
.gray-info {
  color: gray;
  padding-left: 10px;
  text-transform: capitalize;
}
</style>
