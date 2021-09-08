declare module 'vue' {
  import Vue from 'vue';
  function ref<T>(value: T): Ref<T>

  export default Vue;
  export { ref }
}

declare module "vuex" {
  function useStore<T = any>(key?: string): T
}

declare module '*.vue' {
  import Vue from 'vue';

  export { ref }
}
