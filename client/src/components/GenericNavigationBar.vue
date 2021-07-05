<script>
import { mapActions } from 'vuex';

import NavbarTitle from '@/components/NavbarTitle.vue';
import UserButton from '@/components/girder/UserButton.vue';
import NavigationTabs from '@/components/NavigationTabs.vue';

export default {
  name: 'GenericNavigationBar',
  components: {
    NavbarTitle,
    UserButton,
    NavigationTabs,
  },
  methods: {
    ...mapActions(['logout']),
  },
};
</script>

<template>
  <v-app-bar
    app
    dense
  >
    <NavbarTitle />
    <NavigationTabs />
    <v-spacer />
    <UserButton @user="logout()" />
  </v-app-bar>
</template>
