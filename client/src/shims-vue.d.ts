declare module 'vue' {
  import Vue from 'vue';
  import { PropType } from 'vue';
  function ref<T>(value: T): Ref<T>;

  export default Vue;
  export { PropType, ref };
}

declare module '*.vue' {
  import { Component } from 'vue';
  var component: Component;

  export default component;
}
