<script lang="ts">
import Vue from 'vue';
import {
  computed, defineComponent, ref, reactive, watch,
} from '@vue/composition-api';
import Donut from 'vue-css-donut-chart';
import 'vue-css-donut-chart/dist/vcdonut.css';
import { mapMutations } from 'vuex';
import store from '@/store';
import djangoRest from '@/django';
import { Project, ScanState } from '@/types';
import ExperimentsView from '@/components/ExperimentsView.vue';
import Navbar from '@/components/Navbar.vue';
import ProjectSettings from '@/components/ProjectSettings.vue';
import ProjectUsers from '@/components/ProjectUsers.vue';

Vue.use(Donut);

export default defineComponent({
  name: 'Projects',
  components: {
    ExperimentsView,
    Navbar,
    ProjectSettings,
    ProjectUsers,
  },
  inject: ['user', 'MIQAConfig'],
  setup() {
    const loadingProjects = ref(true);
    store.dispatch.loadProjects().then(() => {
      loadingProjects.value = false;
    });
    const currentProject = computed(() => store.state.currentProject);
    const currentTaskOverview = computed(() => store.state.currentTaskOverview);
    const projects = computed(() => store.state.projects);
    const isGlobal = computed(() => store.getters.isGlobal);
    const selectedProjectIndex = ref(projects.value.findIndex(
      (project) => project.id === currentProject.value?.id,
    ));
    const selectProject = (project: Project) => {
      store.dispatch.loadProject(project);
    };
    const selectGlobal = () => {
      store.dispatch.loadGlobal();
    };

    const overviewSections = ref([]);
    const scanStates = Object.keys(ScanState);
    const setOverviewSections = () => {
      if (projects.value && currentTaskOverview.value) {
        const scanStateCounts = ref(reactive(
          scanStates.map(
            (stateString) => {
              const stateCount = Object.entries(currentTaskOverview.value.scan_states).filter(
                ([, scanState]) => scanState === stateString.replace(/_/g, ' '),
              ).length;
              return [stateString, stateCount];
            },
          ),
        ));
        overviewSections.value = scanStateCounts.value.map(
          ([stateString, scanCount]: [string, number]) => ({
            value: scanCount,
            label: `${stateString.replace(/_/g, ' ')} (${scanCount})`,
            color: ScanState[stateString],
          }),
        );
      } else {
        overviewSections.value = [];
      }
    };

    async function refreshTaskOverview() {
      if (currentProject.value) {
        const taskOverview = await djangoRest.projectTaskOverview(currentProject.value.id);
        if (JSON.stringify(store.state.currentTaskOverview) !== JSON.stringify(taskOverview)) {
          store.commit.setTaskOverview(taskOverview);
        }
      }
    }

    const overviewPoll = setInterval(refreshTaskOverview, 10000);
    watch(currentTaskOverview, setOverviewSections);
    watch(currentProject, refreshTaskOverview);

    return {
      currentProject,
      loadingProjects,
      currentTaskOverview,
      selectedProjectIndex,
      projects,
      isGlobal,
      overviewPoll,
      selectProject,
      selectGlobal,
      overviewSections,
      setOverviewSections,
    };
  },
  data: () => ({
    creating: false,
    newName: '',
  }),
  mounted() {
    this.setOverviewSections();
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        this.createProject();
      }
    });
  },
  beforeDestroy() {
    clearInterval(this.overviewPoll);
  },
  methods: {
    ...mapMutations(['setProjects', 'setCurrentProject']),
    async createProject() {
      if (this.creating && this.newName.length > 0) {
        try {
          const newProject = await djangoRest.createProject(this.newName);
          this.setProjects(this.projects.concat([newProject]));
          store.dispatch.loadProject(newProject);
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
});
</script>

<template>
  <div>
    <Navbar />
    <div class="d-flex">
      <v-card class="project-list-container">
        <v-navigation-drawer permanent>
          <v-card-title>Projects</v-card-title>
          <v-list-item-group
            v-model="selectedProjectIndex"
            class="project-list"
          >
            <v-list-item
              v-for="project in projects"
              :key="project.id"
              @click="selectProject(project)"
            >
              <v-tooltip
                v-if="project.status"
                right
              >
                <template #activator="{ on, attrs }">
                  <v-container
                    v-bind="attrs"
                    v-on="on"
                  >
                    <v-row dense>
                      <v-col cols="8">
                        {{ project.name }}
                      </v-col>
                      <v-col
                        cols="4"
                        align="right"
                      >
                        ({{ project.status.total_complete }}/{{ project.status.total_scans }})
                      </v-col>
                    </v-row>
                  </v-container>
                </template>
                <span>
                  {{ project.status.total_complete }} of {{ project.status.total_scans }}
                  scans complete
                </span>
              </v-tooltip>
            </v-list-item>
            <v-list-item
              v-if="user.is_superuser || MIQAConfig.NORMAL_USERS_CAN_CREATE_PROJECTS"
              style="text-align: center"
            >
              <v-text-field
                v-if="creating"
                v-model="newName"
                autofocus
                append-icon="mdi-arrow-right"
                label="New Project Name"
                filled
                dense
                @click:append="createProject"
              />
              <v-btn
                v-else
                class="green white--text"
                @click="creating = true"
              >
                + Create new Project
              </v-btn>
            </v-list-item>
            <div
              v-if="projects.length > 0"
              class="global-settings"
            >
              <v-btn
                class="primary white--text"
                @click="selectGlobal()"
              >
                Global import/export
              </v-btn>
            </div>
          </v-list-item-group>
        </v-navigation-drawer>
      </v-card>
      <div
        v-if="currentProject !== undefined"
        class="flex-grow-1 ma-3 pa-5"
      >
        <v-card-title v-if="isGlobal">
          Perform Global Import / Export
        </v-card-title>
        <v-card-title v-else>
          Project: {{ currentProject ?currentProject.name :'Global' }}
        </v-card-title>
        <div class="flex-container">
          <v-card
            class="flex-card"
            style="flex-grow: 4;"
          >
            <v-subheader v-if="isGlobal">
              WARNING: Global imports will modify all projects referenced in the import file.
            </v-subheader>
            <v-subheader v-else>
              Settings
            </v-subheader>

            <v-layout class="pa-5">
              <v-flex>
                <ProjectSettings />
              </v-flex>
            </v-layout>
          </v-card>
          <v-card
            v-if="currentTaskOverview && currentTaskOverview.total_scans > 0"
            class="flex-card"
          >
            <v-subheader>Overview</v-subheader>
            <vc-donut
              :sections="overviewSections"
              :size="200"
              :thickness="30"
              :total="currentTaskOverview.total_scans"
              has-legend
              legend-placement="right"
            >
              <h2>{{ currentTaskOverview.total_experiments }}</h2>
              <h4>experiments</h4>
              <p>({{ currentTaskOverview.total_scans }} scans)</p>
            </vc-donut>
          </v-card>
        </div>
        <div
          v-if="!isGlobal"
          class="flex-container"
        >
          <ExperimentsView />
          <ProjectUsers />
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
            <v-progress-circular
              v-if="loadingProjects"
              indeterminate
              color="primary"
            />
            <span v-else>You have not been added to any projects yet.</span>
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
.project-list-container {
  height: calc(100vh - 50px);
}
.project-list {
  height: calc(100% - 80px);
}
.global-settings {
  position: absolute;
  bottom: 10px;
  width: 100%;
  text-align: center;
}
</style>
