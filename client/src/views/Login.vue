<script>
import { mapMutations, mapActions } from "vuex";
import { GirderAuthentication } from "@girder/components/src";

export default {
  name: "Login",
  components: {
    GirderAuthentication
  },
  inject: ["girderRest"],
  data() {
    return {
      form: "login",
      userDialog: true
    };
  },
  methods: {
    ...mapMutations(["setCurrentUser", "setSessionStatus"]),
    ...mapActions(["startLoginMonitor"])
  },
  watch: {
    "girderRest.user"(user) {
      if (user) {
        this.setCurrentUser(user);
        this.setSessionStatus("active");
        this.$router.push("/");
        this.startLoginMonitor();
      }
    }
  }
};
</script>

<template>
  <v-container>
    <v-dialog :value="userDialog" persistent max-width="500px">
      <GirderAuthentication :register="true" />
    </v-dialog>
  </v-container>
</template>
