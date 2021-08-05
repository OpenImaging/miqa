<script>
import { mapState, mapActions, mapMutations } from 'vuex';

export default {
  name: 'SessionLock',
  inject: ['user', 'djangoRest'],
  computed: {
    ...mapState(['mainSession']),
  },
  methods: {
    ...mapActions(['updateCurrentSession']),
    ...mapMutations(['setMainSession']),
    async acquireLock() {
      try {
        await this.djangoRest.acquireSession(this.mainSession.id);
        this.setMainSession({ ...this.mainSession, lock_owner: this.user });
      } catch (err) {
        if (err.response && err.response.status !== 409) {
          throw err;
        }
      }
    },
    async releaseLock() {
      try {
        await this.djangoRest.releaseSession(this.mainSession.id);
        this.setMainSession({ ...this.mainSession, lock_owner: null });
      } catch (err) {
        if (err.response && err.response.status !== 409) {
          throw err;
        }
      }
    },
  },
};
</script>

<template>
  <div
    v-if="mainSession"
    class="mr-4 d-flex align-center"
  >
    <span class="mr-4">Session: {{ mainSession.name }}</span>
    <div v-if="mainSession.lock_owner">
      <div v-if="mainSession.lock_owner.id === user.id">
        <v-btn
          small
          color="green"
          class="white--text"
          @click="releaseLock"
        >
          Release
        </v-btn>
      </div>
      <div v-else>
        <v-btn
          small
          color="red"
          class="disable-events white--text"
        >
          READ-ONLY
        </v-btn>
      </div>
    </div>
    <v-btn
      v-else
      small
      color="primary"
      @click="acquireLock"
    >
      Acquire
    </v-btn>
  </div>
</template>

<style lang="scss">
.disable-events {
  pointer-events: none;
}
</style>
