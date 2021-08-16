<script>
import { mapState, mapMutations } from "vuex";

import GenericNavigationBar from "@/components/GenericNavigationBar.vue";

export default {
  name: "TaskList",
  components: {
    GenericNavigationBar,
  },
  data: () => ({
    sessions: [],
    tasks: []
  }),
  computed: {
    ...mapState(["mainSession"]),
  },
  inject: ["djangoRest", "user"],
  methods: {
    ...mapMutations(["setMainSession"]),
  },
  async created() {
    this.sessions = await this.djangoRest.sessions();
    // this.tasks = await this.djangoRest.tasks();

  },
};
</script>

<template>
  <v-container>
    <GenericNavigationBar />
    <div v-if="user.is_superuser">
      <h1>Sessions</h1>
      <v-simple-table>
        <thead>
          <tr>
            <th class="text-left">Name</th>
            <th class="text-left">Archived</th>
            <th class="text-left"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in sessions" :key="session.name">
            <td>{{ session.name }}</td>
            <td>{{ session.archived }}</td>
            <td>
              <v-btn
                v-if="mainSession.id === session.id"
                small
                color="green"
                class="disable-events white--text"
                >Current</v-btn
              >
              <v-btn v-else small color="primary" @click="setMainSession(session)"
                >Use</v-btn
              >
            </td>
          </tr>
        </tbody>
      </v-simple-table>
    </div>
    <h1>Tasks</h1>

  </v-container>
</template>

<style lang="scss" scoped>
.disable-events {
  pointer-events: none;
}
</style>