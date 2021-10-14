<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import store from '@/store';
import { Project } from '@/types';
import ExperimentsView from '@/components/ExperimentsView.vue';
import GenericNavigationBar from '@/components/GenericNavigationBar.vue';
import JSONConfig from '@/components/JSONConfig.vue';
import SiteConfig from '@/components/SiteConfig.vue';

export default defineComponent({
  name: 'Projects',
  components: {
    ExperimentsView,
    GenericNavigationBar,
    JSONConfig,
    SiteConfig,
  },
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
  <div class="sites">
    <GenericNavigationBar />
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
        class="flex-grow-1 ma-3"
      >
        <v-card-title>Experiments</v-card-title>
        <ExperimentsView />
        <v-divider />
        <v-container grid-list-md>
          <div class="subheading">
            Import/Export files
          </div>
          <v-layout>
            <v-flex>
              <JSONConfig />
            </v-flex>
          </v-layout>
          <div class="subheading mt-4">
            Sites
          </div>
          <v-layout justify-center>
            <v-flex>
              <SiteConfig />
            </v-flex>
          </v-layout>
        </v-container>
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
          <div class="title">
            Select a project
          </div>
        </v-layout>
      </v-card>
    </div>
  </div>
</template>

<style lang="scss" scoped></style>
