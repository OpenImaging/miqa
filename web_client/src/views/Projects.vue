<script lang="ts">
import Vue, {
  defineComponent,
  computed,
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick,
} from 'vue';
import Donut from 'vue-css-donut-chart';
import router from '@/router';
import store from '@/store';
import 'vue-css-donut-chart/dist/vcdonut.css';
import djangoRest from '@/django';
import {
  Project, ScanState,
} from '@/types';
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
  setup() {
    let complete = window.location.hash.includes('complete');
    const user = computed(() => store.state.me);
    const miqaConfig = computed(() => store.state.MIQAConfig);
    const loadingProjects = ref(true);
    const creating = ref(false);
    const newName = ref('');
    const overviewSections = ref([]);
    const overviewPoll = ref();
    const proceed = ref();

    const setProjects = (projects) => store.commit('SET_PROJECTS', projects);
    const setCurrentProject = (currentProject) => store.commit('SET_CURRENT_PROJECT', currentProject);
    const setReviewMode = (mode) => store.commit('SET_REVIEW_MODE', mode);
    const setTaskOverview = (overview) => store.commit('SET_TASK_OVERVIEW', overview);
    const setSnackbar = (text) => store.commit('SET_SNACKBAR', text);
    const loadProjects = () => store.dispatch('loadProjects');

    const reviewMode = computed(() => store.state.reviewMode);
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

    // e.g., unreviewed, needs_2_tier_review, complete
    const scanStates = Object.keys(ScanState);
    function setOverviewSections() {
      if (projects.value && currentTaskOverview.value) {
        const scanStateCounts = ref(
          scanStates.map(
            (stateString) => {
              // Replaces _ with a space, e.g. needs_2_tier_review becomes needs 2 tier review
              const stateCount = Object.entries(currentTaskOverview.value.scan_states).filter(
                ([, scanState]) => scanState === stateString.replace(/_/g, ' '),
              ).length;
              return [stateString, stateCount];
            },
          ),
        );
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
    }
    async function refreshTaskOverview() {
      if (currentProject.value) {
        const taskOverview = await djangoRest.projectTaskOverview(currentProject.value.id);
        // If the store / API values differ, update store to API
        if (JSON.stringify(store.state.currentTaskOverview) !== JSON.stringify(taskOverview)) {
          setTaskOverview(taskOverview);
        }
      }
    }
    async function refreshAllTaskOverviews() {
      // For each project
      projects.value.forEach(
        async (project: Project) => {
          // Gets the latest projectTaskOverview for each project from the API
          const taskOverview = await djangoRest.projectTaskOverview(project.id);
          setTaskOverview(taskOverview);
        },
      );
    }
    async function getProjectFromURL() {
      if (complete) {
        const targetProjectIndex = projects.value.findIndex(
          (project) => project.id === window.location.hash.split('/')[1],
        );
        const targetProject = projects.value[targetProjectIndex];
        if (targetProject) setCurrentProject(targetProject);
        selectedProjectIndex.value = targetProjectIndex;
      }
    }
    function selectProject(project: Project) {
      if (complete) {
        complete = false;
      }
      store.dispatch('loadProject', project);
    }
    async function createProject() {
      if (creating.value && newName.value.length > 0) {
        try {
          // Create project
          const newProject = await djangoRest.createProject(newName.value);
          setProjects(projects.value.concat([newProject]));
          // Load project
          await store.dispatch('loadProject', newProject);
          creating.value = false;
          newName.value = '';

          setSnackbar('New project created.');
        } catch (ex) {
          setSnackbar(ex || 'Project creation failed.');
        }
      }
    }
    async function proceedToNext() {
      const nextProject = projects.value[selectedProjectIndex.value + 1];
      await store.dispatch('loadProject', nextProject);
      selectedProjectIndex.value += 1;
      await djangoRest.projectTaskOverview(nextProject.id).then(
        (taskOverview) => {
          let nextScanIndex = 0;
          let nextScan;
          let nextScanState;
          while (
            (!nextScan
            || (nextScanState === 'complete' && reviewMode.value))
            && nextProject.experiments[0].scans
            && nextScanIndex < nextProject.experiments[0].scans.length
          ) {
            nextScan = nextProject.experiments[0].scans[nextScanIndex];
            nextScanState = taskOverview.scan_states[nextScan.id];
            nextScanIndex += 1;
          }
          if (nextScan) {
            router.push(`/${nextProject.id}/${nextScan.id}` || '');
          } else {
            router.push('/');
          }
        },
      );
    }

    watch(currentTaskOverview, setOverviewSections);
    watch(currentProject, refreshTaskOverview);
    watch(projects, getProjectFromURL);
    watch(projects, () => {
      nextTick(() => {
        if (proceed.value) proceed.value.focus();
      });
    });

    onMounted(() => {
      loadProjects().then(() => {
        loadingProjects.value = false;
      });
      overviewPoll.value = setInterval(refreshTaskOverview, 10000); // 10 secs
      setOverviewSections();
      window.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          createProject();
        }
      });
      window.addEventListener('unauthorized', () => {
        setSnackbar('Server session expired. Try again.');
      });
    });
    onBeforeUnmount(() => clearInterval(overviewPoll.value));

    return {
      user,
      miqaConfig,
      reviewMode,
      setReviewMode,
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
      selectProject,
      proceedToNext,
      createProject,
      creating,
      newName,
    };
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
              v-if="user.is_superuser || miqaConfig.NORMAL_USERS_CAN_CREATE_PROJECTS"
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
                @change="setReviewMode"
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
