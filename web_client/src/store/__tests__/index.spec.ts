import { createLocalVue } from '@vue/test-utils';
import Vuex from 'vuex';
import cloneDeep from 'lodash/cloneDeep';
import { storeConfig } from '@/store';

describe('Vuex Mutations', () => {
  test('setCurrentVtkIndexSlices should update the i/j/k indexSlices', () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);
    const theStore = cloneDeep(storeConfig);
    const store = new Vuex.Store(theStore);
    expect(store.state.iIndexSlice).toBe(0);
    store.commit('SET_CURRENT_VTK_INDEX_SLICES', { indexAxis: 'i', value: 1 });
    expect(store.state.iIndexSlice).toBe(1);
    expect(store.state.jIndexSlice).toBe(0);
    store.commit('SET_CURRENT_VTK_INDEX_SLICES', { indexAxis: 'j', value: 1 });
    expect(store.state.jIndexSlice).toBe(1);
    expect(store.state.kIndexSlice).toBe(0);
    store.commit('SET_CURRENT_VTK_INDEX_SLICES', { indexAxis: 'k', value: 1 });
    expect(store.state.kIndexSlice).toBe(1);
  });
});
