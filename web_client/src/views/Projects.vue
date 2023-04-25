<script lang="ts">
import Vue, {
  computed, defineComponent, ref, reactive, watch,
} from 'vue';
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
  name: 'ProjectsView',
  components: {
    ExperimentsView,
    Navbar,
    ProjectSettings,
    ProjectUsers,
  },
  inject: ['user', 'MIQAConfig'],
  setup() {
    const SET_REVIEW_MODE = store.commit('SET_REVIEW_MODE');
    const loadingProjects = ref(true);
    store.dispatch('loadProjects').then(() => {
      loadingProjects.value = false;
    });
    const reviewMode = computed(() => store.state.reviewMode);
    const complete = window.location.hash.includes('complete');
    const currentProject = computed(() => store.state.currentProject);
    const currentTaskOverview = computed(() => store.state.currentTaskOverview);
    const projects = computed(() => store.state.projects);
    const isGlobal = computed(() => store.getters.isGlobal);
    const selectedProjectIndex = ref(projects.value.findIndex(
      (project) => project.id === currentProject.value?.id,
    ));
    // Loads global settings
    const selectGlobal = () => {
      store.dispatch('loadGlobal');
    };

    // Starts as an empty array
    const overviewSections = ref([]);
    // e.g., unreviewed, needs_2_tier_review, complete
    const scanStates = Object.keys(ScanState);
    const setOverviewSections = () => {
      if (projects.value && currentTaskOverview.value) {
        const scanStateCounts = ref(reactive(
          scanStates.map(
            (stateString) => {
              // Replaces _ with a space, e.g. needs_2_tier_review becomes needs 2 tier review
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
        // If the store / API values differ, update store to API
        if (JSON.stringify(store.state.currentTaskOverview) !== JSON.stringify(taskOverview)) {
          store.commit('SET_TASK_OVERVIEW', taskOverview);
        }
      }
    }

    async function refreshAllTaskOverviews() {
      // For each project
      projects.value.forEach(
        async (project: Project) => {
          // Gets the latest projectTaskOverview for each project from the API
          const taskOverview = await djangoRest.projectTaskOverview(project.id);
          await store.commit('SET_TASK_OVERVIEW', taskOverview);
        },
      );
    }

    async function getProjectFromURL() {
      if (complete) {
        const targetProjectIndex = projects.value.findIndex(
          (project) => project.id === window.location.hash.split('/')[1],
        );
        const targetProject = projects.value[targetProjectIndex];
        if (targetProject) store.commit('SET_CURRENT_PROJECT', targetProject);
        selectedProjectIndex.value = targetProjectIndex;
      }
    }

    const overviewPoll = setInterval(refreshTaskOverview, 10000); // 10 secs

    // Triggers functions when specified state changes
    watch(currentTaskOverview, setOverviewSections);
    watch(currentProject, refreshTaskOverview);
    watch(projects, getProjectFromURL);

    return {
      reviewMode,
      SET_REVIEW_MODE,
      complete,
      currentProject,
      loadingProjects,
      currentTaskOverview,
      selectedProjectIndex,
      projects,
      isGlobal,
      overviewPoll,
      selectGlobal,
      overviewSections,
      setOverviewSections,
      refreshAllTaskOverviews,
      getProjectFromURL,
    };
  },
  data: () => ({
    creating: false,
    newName: '',
  }),
  watch: {
    projects() {
      this.$nextTick(() => {
        if (this.$refs.proceed) this.$refs.proceed.$el.focus();
      });
    },
  },
  mounted() {
    this.setOverviewSections();
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        this.createProject();
      }
    });
    window.addEventListener('unauthorized', () => {
      this.$snackbar({
        text: 'Server session expired. Try again.',
        timeout: 6000,
      });
    });
  },
  beforeDestroy() {
    clearInterval(this.overviewPoll);
  },
  methods: {
    ...mapMutations([
      'SET_PROJECTS',
      'SET_CURRENT_PROJECT',
    ]),
    selectProject(project: Project) {
      if (this.complete) {
        this.complete = false;
      }
      store.dispatch('loadProject', project);
    },
    async createProject() {
      if (this.creating && this.newName.length > 0) {
        try {
          // Create project
          const newProject = await djangoRest.createProject(this.newName);
          this.SET_PROJECTS(this.projects.concat([newProject]));
          // Load project
          await store.dispatch('loadProject', newProject);
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
    async proceedToNext() {
      const nextProject = this.projects[this.selectedProjectIndex + 1];
      await store.dispatch('loadProject', nextProject);
      this.selectedProjectIndex += 1;
      await djangoRest.projectTaskOverview(nextProject.id).then(
        (taskOverview) => {
          let nextScanIndex = 0;
          let nextScan;
          let nextScanState;
          while (
            (!nextScan
            || (nextScanState === 'complete' && this.reviewMode))
            && nextProject.experiments[0].scans
            && nextScanIndex < nextProject.experiments[0].scans.length
          ) {
            nextScan = nextProject.experiments[0].scans[nextScanIndex];
            nextScanState = taskOverview.scan_states[nextScan.id];
            nextScanIndex += 1;
          }
          if (nextScan) {
            this.$router.push(`/${nextProject.id}/${nextScan.id}` || '');
          } else {
            this.$router.push('/');
          }
        },
      );
    },
  },
});
</script>

<template>
  <div v-if="user">
    <Navbar />
    <div class="d-flex">
      <v-card class="project-list-container">
        <v-navigation-drawer permanent>
          <v-card-title style="display: flex; justify-content: space-between">
            Projects
            <v-icon @click="refreshAllTaskOverviews">
              mdi-refresh
            </v-icon>
          </v-card-title>
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
              v-if="projects && projects.length > 0"
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
        v-if="currentProject !== undefined && !complete"
        class="flex-grow-1 ma-3 pa-5"
      >
        <v-card-title v-if="isGlobal">
          Perform Global Import / Export
        </v-card-title>
        <v-card-title v-else>
          Project: {{ currentProject ? currentProject.name : 'Global' }}
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
            v-if="currentTaskOverview && currentTaskOverview.total_scans > 0 && !isGlobal"
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
              <h2>{{ currentTaskOverview.total_scans }}</h2>
              <h4>scans</h4>
              <p>({{ currentTaskOverview.total_experiments }} experiments)</p>
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
            v-if="complete"
            class="text-h6 text-center"
          >
            Viewed all scans in Project {{ currentProject.name }}.
            <div
              v-if="selectedProjectIndex + 1 < projects.length"
            >
              Proceed to next Project, {{ projects[selectedProjectIndex + 1].name }}?
              <br>
              <v-form @submit.prevent="proceedToNext">
                <v-btn
                  ref="proceed"
                  class="my-3"
                  type="submit"
                >
                  Proceed
                </v-btn>
              </v-form>
            </div>
            <v-subheader
              class="mode-toggle"
            >
              <span>All scans</span>
              <v-switch
                :input-value="reviewMode"
                dense
                style="display: inline-block; max-height: 40px; max-width: 60px;"
                class="px-3 ma-0"
                @change="SET_REVIEW_MODE"
              />
              <span>Scans for my review</span>
            </v-subheader>
          </div>
          <div
            v-else-if="projects.length > 0"
            class="text-h6"
          >
            Select a project
          </div>
          <div
            v-else
            class="text-h6"
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
.mode-toggle {
  align-items: baseline;
  display: inline-block;
}
</style>
