<script>
import { mapState, mapActions } from 'vuex';

import SiteTableContactCell from '@/components/SiteTableContactCell.vue';
import SiteTableDisplayNameCell from '@/components/SiteTableDisplayNameCell.vue';

export default {
  name: 'SiteConfig',
  components: {
    SiteTableContactCell,
    SiteTableDisplayNameCell,
  },
  computed: {
    ...mapState(['sites']),
    headers: () => [
      { text: 'Site', value: 'name' },
      { text: 'Display Name', value: 'displayName' },
      { text: 'PI', value: 'pi' },
      { text: 'MRI Physicist', value: 'mriPhysicist' },
      { text: 'Technician', value: 'technician' },
      { text: 'lead RA', value: 'leadRA' },
    ],
    items() {
      if (!this.sites) {
        return [];
      }
      return this.sites.map((site) => ({
        site,
        name: site.name,
        displayName: site.meta ? site.meta.displayName : null,
        pi: site.meta ? site.meta.pi : [],
        mriPhysicist: site.meta ? site.meta.mriPhysicist : [],
        technician: site.meta ? site.meta.technician : [],
        leadRA: site.meta ? site.meta.leadRA : [],
      }));
    },
  },
  created() {
    this.loadSites();
  },
  methods: {
    ...mapActions(['loadSites']),
    async update(site, field, value) {
      if (!site.meta) {
        this.$set(site, 'meta', {});
      }
      this.$set(site.meta, field, value);
      // await this.girderRest.put(`item/${site._id}/metadata`, site.meta);
    },
  },
};
</script>

<template>
  <v-data-table
    class="site-config"
    :headers="headers"
    :items="items"
    hide-default-footer
  >
    <template #items="{ item }">
      <td>{{ item.name }}</td>
      <SiteTableDisplayNameCell
        :value="item.displayName"
        @input="update(item.site, 'displayName', $event)"
      />
      <SiteTableContactCell
        :value="item.pi"
        @input="update(item.site, 'pi', $event)"
      />
      <SiteTableContactCell
        :value="item.mriPhysicist"
        @input="update(item.site, 'mriPhysicist', $event)"
      />
      <SiteTableContactCell
        :value="item.technician"
        @input="update(item.site, 'technician', $event)"
      />
      <SiteTableContactCell
        :value="item.leadRA"
        @input="update(item.site, 'leadRA', $event)"
      />
    </template>
  </v-data-table>
</template>
