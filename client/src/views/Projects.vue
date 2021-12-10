<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import { mapMutations } from 'vuex';
import store from '@/store';
import djangoRest from '@/django';
import { Project } from '@/types';
import ExperimentsView from '@/components/ExperimentsView.vue';
import Navbar from '@/components/Navbar.vue';
import ProjectSettings from '@/components/ProjectSettings.vue';
import ProjectUsers from '@/components/ProjectUsers.vue';

export default defineComponent({
  name: 'Projects',
  components: {
    ExperimentsView,
    Navbar,
    ProjectSettings,
    ProjectUsers,
  },
  inject: ['user'],
  data: () => ({
    creating: false,
    newName: '',
  }),
  setup() {
    store.dispatch.loadProjects();
    const currentProject = computed(() => store.state.currentProject);
    const projects = computed(() => store.state.projects);
    // We don't actually use selectedProjectIndex for anything
    // It is determined here so that the projects list selects the current project when navigating
    // to it from a different tab.
    const selectedProjectIndex = ref(projects.value.findIndex(
      (project) => project.id === currentProject.value?.id,
    ));
    const selectProject = (project: Project) => {
      store.dispatch.loadProject(project);
    };

    return {
      currentProject,
      selectedProjectIndex,
      projects,
      selectProject,
    };
  },
  methods: {
    ...mapMutations(['setProjects', 'setCurrentProject']),
    async createProject() {
      if (this.creating && this.newName.length > 0) {
        try {
          const newProject = await djangoRest.createProject(this.newName);
          this.setProjects(this.projects.concat([newProject]));
          this.setCurrentProject(newProject);
          this.creating = false;
          this.newName = '';

          this.$snackbar({
            text: 'New project created.',
            timeout: 6000,
          });
        } catch (ex) {
          this.$snackbar({
            text: ex || 'Project creation failed.',
          });
        }
      }
    },
  },
  mounted() {
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        this.createProject();
      }
    });
  },
});
</script>

<template>
  <div>
    <Navbar />
    <div class="d-flex">
      <v-card>
        <v-navigation-drawer permanent>
          <v-card-title>Projects</v-card-title>
          <v-list-item-group v-model="selectedProjectIndex">
            <v-list-item
              v-for="project in projects"
              :key="project.id"
              @click="selectProject(project)"
            >
              {{ project.name }}
            </v-list-item>
            <v-list-item style="text-align: center">
              <v-text-field
                v-if="creating"
                v-model="newName"
                @click:append="createProject"
                autofocus
                append-icon="mdi-arrow-right"
                label="New Project Name"
                filled
                dense
              />
              <v-btn
                @click="creating = true"
                v-else
                class="green white--text"
              >
                + Create new Project
              </v-btn>
            </v-list-item>
          </v-list-item-group>
        </v-navigation-drawer>
      </v-card>
      <div
        v-if="currentProject"
        class="flex-grow-1 ma-3 pa-5"
      >
        <v-card-title>Project: {{ currentProject.name }}</v-card-title>
        <v-card v-if="user.is_superuser">
          <v-subheader>Settings</v-subheader>

          <v-layout class="pa-5">
            <v-flex>
              <ProjectSettings />
            </v-flex>
          </v-layout>
        </v-card>
        <div class="flex-container">
          <v-card class="flex-card">
            <v-subheader>Experiments</v-subheader>
            <ExperimentsView />
          </v-card>
          <v-card class="flex-card">
            <v-subheader>Users</v-subheader>
            <ProjectUsers />
          </v-card>
        </div>
      </div>
      <v-card
        v-else
        class="flex-grow-1 ma-3"
      >
        <v-layout
          align-center
          justify-center
          fill-height
        >
          <div
            v-if="projects.length > 0"
            class="title"
          >
            Select a project
          </div>
          <div
            v-else
            class="title"
          >
            You have not been added to any projects yet.
          </div>
        </v-layout>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.flex-container {
  display: flex;
  column-gap: 10px;
}
.flex-card {
  flex-grow: 1;
  margin-top: 10px;
  padding-bottom: 20px;
}
</style>
