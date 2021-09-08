declare module 'vue' {
  import Vue from 'vue';
  import { PropType } from 'vue';
  function ref<T>(value: T): Ref<T>;

  export default Vue;
  export { PropType, ref };
}

declare module "vuex" {
  import Vuex from 'vuex';
  function useStore<T = any>(key?: string): T;
  function mapState(map: Array<string> | Object<string | function>): Object;
  function mapMutations(map: Array<string> | Object<string | function>): Object;
  function mapActions(map: Array<string> | Object<string | function>): Object;

  export default Vuex;
  export {
    useStore,
    mapState,
    mapMutations,
    mapActions
  };
}

declare module '*.vue' {
  import Vue from 'vue';

  export { ref }
}
