<!--
Application settings: one field per scalar setting. Settings whose value is a
list or object are edited on the Lists screen, and grading_schemes on the
Grading Scheme screen.
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">Settings</div>
      <div class="card-body">
        <div class="row mb-3" v-for="s in scalars" :key="s.key">
          <div class="col-md-3"><b>{{ s.key }}</b></div>
          <div class="col-md-3">
            <div v-if="typeof s.default == 'boolean'" class="form-check form-switch">
              <input class="form-check-input" type="checkbox" v-model="s.value" />
            </div>
            <input v-else type="number" step="any" class="form-control" v-model.number="s.value" />
          </div>
          <div class="col-md-1">
            <button type="button" class="btn btn-sm btn-outline-success" title="Save" @click="save(s)">
              <i class="bi bi-save"></i>
            </button>
          </div>
          <div class="col">
            <small class="text-muted">{{ s.description }} (Default: {{ s.default }})</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "AppSettings",
  data: function () {
    return { scalars: [] };
  },
  mounted: function () {
    this.load();
  },
  methods: {
    load() {
      return this.doHttp(true, "settings", null, (body) => {
        this.scalars = body.filter(s => typeof s.default != "object");
      }, this.setStatusMessage);
    },
    async save(s) {
      await this.doHttp(false, "setting_save", { key: s.key, value: s.value }, (body) => {
        this.scalars = body.filter(x => typeof x.default != "object");
        this.setStatusMessage(`Saved ${s.key}.`);
      }, this.setStatusMessage);
    },
  },
};
</script>
