declare module '*.vue' {
  import Vue from 'vue';
  import { Component } from 'vue';
  export function ref<T>(value: T): Ref<T>;
  export var component: Component;

  export default Vue;
}
