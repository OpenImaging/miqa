<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import store from '@/store';
import { Project } from '@/types';
import ExperimentsView from '@/components/ExperimentsView.vue';
import Navbar from '@/components/Navbar.vue';
import JSONConfig from '@/components/JSONConfig.vue';
import DataImportExport from '@/components/DataImportExport.vue';

export default defineComponent({
  name: 'Projects',
  components: {
    ExperimentsView,
    Navbar,
    JSONConfig,
    DataImportExport,
  },
  inject: ['user'],
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
          </v-list-item-group>
        </v-navigation-drawer>
      </v-card>
      <v-card
        v-if="currentProject"
        class="flex-grow-1 ma-3 pb-5"
      >
        <v-card-title>Project: {{ currentProject.name }}</v-card-title>
        <v-layout
          v-if="user.is_superuser"
          class="pa-5"
        >
          <v-flex>
            <JSONConfig />
            <DataImportExport />
          </v-flex>
        </v-layout>
        <v-divider />
        <v-card-subtitle>Experiments</v-card-subtitle>
        <ExperimentsView />
      </v-card>
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
