<script>
import {
  mapState, mapActions, mapMutations,
} from 'vuex';

const initMinutes = 1;
const initSeconds = 59;

export default {
  name: 'TimeoutDialog',
  data: () => ({
    show: false,
    minutes: initMinutes,
    seconds: initSeconds,
  }),
  inject: ['djangoRest'],
  computed: {
    ...mapState(['actionTimeout']),
    minutesStr() {
      switch (this.minutes) {
        case 0:
          return '';
        case 1:
          return '1 minute';
        default:
          return `${this.minutes} minutes`;
      }
    },
    secondsStr() {
      switch (this.seconds) {
        case 0:
          return '';
        case 1:
          return '1 second';
        default:
          return `${this.seconds} seconds`;
      }
    },
    done() {
      return this.minutes <= 0 && this.seconds <= 0;
    },
  },
  watch: {
    // vue-idle: Adds a computed value 'isAppIdle' to all Vue objects
    isAppIdle(idle) {
      if (idle && !this.show) {
        this.show = true;
        this.decrement();
      }
    },
    actionTimeout(timeout) {
      if (timeout && !this.show) {
        this.show = true;
        this.decrement();
      }
    },
  },
  created() {
    this.startActionTimer();
  },
  methods: {
    ...mapActions(['startActionTimer', 'resetActionTimer']),
    ...mapMutations(['setActionTimeout']),
    reset() {
      // reset dialog
      this.show = false;
      this.minutes = initMinutes;
      this.seconds = initSeconds;

      // reset no-action timer
      this.setActionTimeout(false);
      this.resetActionTimer();
    },
    logout() {
      this.minutes = 0;
      this.seconds = 0;
    },
    reload() {
      this.$router.go();
    },
    decrement() {
      if (this.show) {
        setTimeout(() => {
          this.seconds -= 1;

          if (this.minutes <= 0 && this.seconds <= 0) {
            this.djangoRest.logout();
            return;
          }

          if (this.seconds === 0) {
            this.minutes -= 1;
            this.seconds = initSeconds;
          }

          this.decrement();
        }, 1000);
      }
    },
  },
};
</script>

<template>
  <v-dialog
    v-model="show"
    width="500"
    persistent
  >
    <v-card>
      <v-card-title class="text-h5 grey lighten-2">
        Warning
      </v-card-title>

      <v-card-text class="py-4 px-6">
        <p v-if="done">
          You have been logged out due to inactivity. Refresh the page to log
          back in
        </p>
        <p v-else>
          You have been inactive for more than 1 hour. Your session will
          automatically terminate in {{ minutesStr }} {{ secondsStr }}
        </p>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn
          v-if="!done"
          color="primary"
          text
          @click="reset"
        >
          Continue Session
        </v-btn>
        <v-btn
          v-if="!done"
          color="secondary"
          text
          @click="logout"
        >
          Logout
        </v-btn>
        <v-btn
          v-if="done"
          color="primary"
          text
          @click="reload"
        >
          Reload
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
