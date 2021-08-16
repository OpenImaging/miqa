<script>
import { mapState, mapMutations, mapActions } from "vuex";

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
    ...mapMutations(['setMainSession', 'setMode', 'setDrawer']),
    ...mapActions(['loadTask']),
    mapExperiments(experiments) {
      return experiments.map(experiment => {
        return experiment.name;
      }).join(', ')
    },
    switchToSession(session) {
      this.setMode('SESSION');
      this.setMainSession(session);
      this.$router.push('/');
    },
    async switchToTask(task) {
      await this.loadTask(task);
      this.setMainSession(task);
      this.$router.push('/');
      this.setDrawer(true);
    }
  },
  async created() {
    this.sessions = await this.djangoRest.sessions();
    this.tasks = await this.djangoRest.tasks();
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
            <td>{{ session.archived ? "yes" : "no" }}</td>
            <td>
              <v-btn
                v-if="mainSession.id === session.id"
                small
                color="green"
                class="disable-events white--text"
                >Current</v-btn
              >
              <v-btn v-else small color="primary" @click="switchToSession(session)"
                >Use</v-btn
              >
            </td>
          </tr>
        </tbody>
      </v-simple-table>
    </div>
    <h1>Tasks</h1>
    <v-simple-table>
      <thead>
        <tr>
          <th class="text-left">Name</th>
          <th class="text-left">Experiments</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.name">
          <td>{{ task.name }}</td>
          <td>{{ mapExperiments(task.experiments) }}</td>
          <td>
            <v-btn
              v-if="mainSession.id === task.id"
              small
              color="green"
              class="disable-events white--text"
              >Current</v-btn
            >
            <v-btn v-else small color="primary" @click="switchToTask(task)"
              >Use</v-btn
            >
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </v-container>
</template>

<style lang="scss" scoped>
.disable-events {
  pointer-events: none;
}
</style>