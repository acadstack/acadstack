<!--
Application settings: one field per scalar setting, and one address per line
for broadcast_emails. The other settings whose value is a list or object are
edited on the Lists screen, and grading_schemes on the Grading Scheme screen.
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
            <textarea v-else-if="s.key == 'broadcast_emails'" rows="3" class="form-control" v-model="s.value" />
            <input v-else-if="typeof s.default == 'string'" type="text" class="form-control" v-model.trim="s.value" />
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
    show(body) {
      // broadcast_emails is edited as text, one address per line
      this.scalars = body.filter(s => typeof s.default != "object" || s.key == "broadcast_emails")
        .map(s => s.key == "broadcast_emails" ? { ...s, value: s.value.join("\n") } : s);
    },
    load() {
      return this.doHttp(true, "settings", null, this.show, this.setStatusMessage);
    },
    async save(s) {
      const value = s.key == "broadcast_emails"
        ? s.value.split("\n").map(a => a.trim()).filter(a => a) : s.value;
      await this.doHttp(false, "setting_save", { key: s.key, value }, (body) => {
        this.show(body);
        this.setStatusMessage(`Saved ${s.key}.`);
      }, this.setStatusMessage);
    },
  },
};
</script>
