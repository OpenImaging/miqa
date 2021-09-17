<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import store from '@/store';
import VtkViewer from './VtkViewer.vue';

export default defineComponent({
  name: 'Layout',
  components: {
    VtkViewer,
  },
  setup() {
    const vtkViews = computed(() => store.state.vtkViews);

    return {
      vtkViews,
    };
  },
});
</script>

<template>
  <div class="my-layout">
    <div
      v-for="(vtkView, index) in vtkViews"
      :key="index"
      class="view"
    >
      <VtkViewer :view="vtkView" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.my-layout {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;

  .view {
    position: relative;
    flex: 1 0 0px;

    border: 1.5px solid white;
    border-top: none;
    border-bottom: none;

    &:first-child {
      border-left: none;
    }

    &:last-child {
      border-right: none;
    }
  }
}
</style>
