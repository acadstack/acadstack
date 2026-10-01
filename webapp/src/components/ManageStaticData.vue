<!--
Lists screen: the university's lists (departments, programs, course types and
so on), and the labels of the workflow codes that the application's logic
acts on.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <ul class="nav nav-tabs mb-2">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: tab == 'lists' }" href="#" @click.prevent="tab = 'lists'">
          University lists
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: tab == 'workflow' }" href="#" @click.prevent="tab = 'workflow'">
          Workflow labels
        </a>
      </li>
    </ul>

    <div class="card" v-if="tab == 'lists'">
      <div class="card-header">
        <label class="me-2" for="listName">List</label>
        <select id="listName" class="form-select d-inline-block w-auto" v-model="listName">
          <option v-for="n in listNames" :key="n" :value="n">{{ n }}</option>
        </select>
        <small class="text-muted ms-3">
          Codes can't be changed once saved. Hide an item instead of deleting it.
        </small>
      </div>
      <div class="card-body">
        <div class="row hdr-row mb-2 border-info border-bottom">
          <div class="col-md-1">Code</div>
          <div class="col-md-3">Label</div>
          <div class="col-md-1">Order</div>
          <div class="col">Attributes</div>
          <div class="col-md-1">Hidden</div>
          <div class="col-md-1"></div>
        </div>
        <div class="row row-striped mb-2" v-for="it in rows" :key="it.id || 'new'"
          :class="{ 'text-muted': it.is_deleted }">
          <div class="col-md-1">
            <input v-if="!it.id" type="text" class="form-control" v-model.trim="it.code" />
            <span v-else>{{ it.code }}</span>
          </div>
          <div class="col-md-3">
            <input type="text" class="form-control" maxlength="200" v-model="it.label" />
          </div>
          <div class="col-md-1">
            <input type="number" class="form-control" v-model.number="it.sort_order" />
          </div>
          <div class="col">
            <div class="input-group input-group-sm mb-1" v-for="(allowed, name) in attrDefs" :key="name">
              <span class="input-group-text">{{ name }}</span>
              <select v-if="allowed && allowed.length" class="form-select" v-model="it.attrs[name]">
                <option value="">--</option>
                <option v-for="a in allowed" :key="a" :value="a">{{ a }}</option>
              </select>
              <input v-else type="text" class="form-control" v-model="it.attrs[name]" />
            </div>
          </div>
          <div class="col-md-1">
            <input type="checkbox" class="form-check-input" v-model="it.is_deleted" />
          </div>
          <div class="col-md-1">
            <button class="btn btn-sm btn-outline-success" type="button" title="Save" @click="saveItem(it)">
              <i class="bi bi-save"></i>
            </button>
          </div>
        </div>
        <button type="button" class="btn btn-outline-primary" @click="addItem">Add item</button>
      </div>
    </div>

    <div class="card" v-else>
      <div class="card-header">
        Labels of the workflow codes
        <small class="text-muted ms-3">
          The codes are fixed because the application acts on them; only the labels shown can change.
        </small>
        <button type="button" class="btn btn-outline-success float-end" @click="saveWorkflow">
          Save <i class="bi bi-save"></i>
        </button>
      </div>
      <div class="card-body">
        <div v-for="w in workflowLists" :key="w.name" class="mb-3">
          <h6 class="border-bottom border-info">{{ w.name }}</h6>
          <div class="row mb-1" v-for="e in w.entries" :key="e.id">
            <div class="col-md-2">{{ e.id }}</div>
            <div class="col-md-4">
              <input type="text" class="form-control form-control-sm" v-model="labels[w.name][e.id]" />
            </div>
            <div class="col-md-2">
              <button v-if="overrides[w.name] && overrides[w.name][e.id]" type="button"
                class="btn btn-sm btn-outline-secondary" @click="resetLabel(w.name, e.id)">
                Use default
              </button>
            </div>
            <div class="col-md-2" v-if="w.name == 'EnrolTypes' && e.id != 'C'">
              <label>
                <input type="checkbox" class="form-check-input me-1" v-model="hidden[e.id]" />
                Hidden
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Workflow lists whose labels are not editable here.
const NOT_LABELLED = ["AcademicSessions", "UserRoles", "CourseGrades"];

export default {
  name: "ManageStaticData",
  data: function () {
    return {
      tab: "lists",
      items: {},
      attrDefs: {},
      allAttrs: {},
      listName: "",
      rows: [],
      overrides: {},
      hiddenEnrolTypes: [],
      labels: {},
      hidden: {},
    };
  },
  computed: {
    listNames() {
      return Object.keys(this.items);
    },
    workflowLists() {
      const lists = Object.keys(this.SD)
        .filter(n => !this.items[n] && !NOT_LABELLED.includes(n))
        .map(n => ({ name: n, entries: this.SD[n].filter(e => e.id) }));
      // Hidden enrolment types are absent from the static data.
      const et = lists.find(l => l.name == "EnrolTypes");
      if (et) {
        const shown = et.entries.map(e => e.id);
        for (const c of this.hiddenEnrolTypes)
          if (!shown.includes(c)) et.entries.push({ id: c, value: this.overrides.EnrolTypes?.[c] || c });
      }
      return lists;
    },
  },
  watch: {
    listName() {
      this.showList();
    },
    workflowLists() {
      this.initWorkflowForm();
    },
  },
  mounted: function () {
    this.loadVocab();
    this.loadWorkflowSettings();
  },
  methods: {
    showList() {
      this.attrDefs = this.allAttrs[this.listName] || {};
      this.rows = (this.items[this.listName] || []).map(this.editable);
    },
    editable(it) {
      const attrs = {};
      for (const n of Object.keys(this.attrDefs)) attrs[n] = it.attrs[n] || "";
      return { ...it, attrs };
    },
    addItem() {
      const order = Math.max(0, ...this.rows.map(r => r.sort_order)) + 1;
      this.rows.push(this.editable({ vocab: this.listName, code: "", label: "", sort_order: order, attrs: {}, is_deleted: false }));
    },
    applyVocab(body) {
      this.items = body.items;
      this.allAttrs = body.attrs;
      if (!this.listName) this.listName = Object.keys(body.items)[0];
      this.showList();
    },
    loadVocab() {
      return this.doHttp(true, "vocab", null, this.applyVocab, this.setStatusMessage);
    },
    async saveItem(it) {
      const attrs = {};
      for (const [n, v] of Object.entries(it.attrs)) if (v) attrs[n] = v;
      const payload = { ...it, vocab: this.listName, attrs };
      await this.doHttp(false, "vocab_save", payload, async (body) => {
        this.applyVocab(body);
        await this.refreshStaticData();
        this.setStatusMessage("Saved.");
      }, this.setStatusMessage);
    },
    async refreshStaticData() {
      await this.doHttp(true, "get_static_data", null, this.setStaticData, this.setStatusMessage);
    },
    loadWorkflowSettings() {
      return this.doHttp(true, "settings", null, (body) => {
        this.overrides = body.find(s => s.key == "label_overrides").value;
        this.hiddenEnrolTypes = body.find(s => s.key == "hidden_enrol_types").value;
        this.initWorkflowForm();
      }, this.setStatusMessage);
    },
    initWorkflowForm() {
      const labels = {};
      for (const w of this.workflowLists) {
        labels[w.name] = {};
        for (const e of w.entries) labels[w.name][e.id] = e.value;
      }
      this.labels = labels;
      this.hidden = Object.fromEntries(this.hiddenEnrolTypes.map(c => [c, true]));
    },
    async resetLabel(list, code) {
      const o = JSON.parse(JSON.stringify(this.overrides));
      delete o[list][code];
      if (!Object.keys(o[list]).length) delete o[list];
      await this.postSetting("label_overrides", o);
      await this.refreshStaticData();
    },
    postSetting(key, value) {
      return this.doHttp(false, "setting_save", { key, value }, (body) => {
        this.overrides = body.find(s => s.key == "label_overrides").value;
        this.hiddenEnrolTypes = body.find(s => s.key == "hidden_enrol_types").value;
      }, this.setStatusMessage);
    },
    async saveWorkflow() {
      // A label that differs from the one now shown becomes an override.
      const o = JSON.parse(JSON.stringify(this.overrides));
      for (const w of this.workflowLists) {
        for (const e of w.entries) {
          const text = (this.labels[w.name][e.id] || "").trim();
          if (text && text != e.value) (o[w.name] = o[w.name] || {})[e.id] = text;
        }
      }
      const hiddenCodes = Object.keys(this.hidden).filter(c => this.hidden[c]);
      await this.postSetting("label_overrides", o);
      await this.postSetting("hidden_enrol_types", hiddenCodes);
      await this.refreshStaticData();
      this.setStatusMessage("Saved.");
    },
  },
};
</script>
