<script>
import { mapState, mapMutations } from 'vuex';

export default {
  name: 'SessionLock',
  inject: ['user', 'djangoRest'],
  computed: {
    ...mapState(['mainSession']),
  },
  methods: {
    ...mapMutations(['setMainSession']),
    async acquireLock() {
      try {
        this.djangoRest.acquireSession(this.mainSession.id);
        this.setMainSession({ ...this.mainSession, lock_owner: this.user });
      } catch (err) {
        console.log(err);
      }
    },
    async releaseLock() {
      try {
        this.djangoRest.releaseSession(this.mainSession.id);
        this.setMainSession({ ...this.mainSession, lock_owner: null });
      } catch (err) {
        console.log(err);
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
