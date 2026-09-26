<!--
Admin screen for DB-backed system settings and controlled vocabularies
(settings_store.py). Straightforward grouped CRUD: every value is edited
in place and saved back through settings_save, with client-side checks
mirroring settings_store's Spec validation so an invalid value is caught
here rather than rejected by the server.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid" v-if="hasPermission('system.manage_settings')">
        <div class="row mb-2">
            <div class="col">
                <h4>System Settings</h4>
                <small class="text-muted">
                    Operational settings and controlled vocabularies. Changes take
                    effect immediately, for every user.
                </small>
            </div>
        </div>

        <div class="card mb-3" v-for="grp in scalarGroups" :key="grp.name">
            <div class="card-header">
                <b>{{ grp.name }}</b>
                <span class="text-muted"> &mdash; {{ grp.doc }}</span>
            </div>
            <div class="card-body">
                <div v-if="grp.items.length == 0" class="text-muted">
                    Nothing declared in this group.
                </div>
                <div class="row row-striped mb-3 pb-2 border-bottom" v-for="it in grp.items" :key="it.key">
                    <div class="col-md-3">
                        <b>{{ it.name }}</b>
                        <div class="text-muted small">{{ it.doc }}</div>
                    </div>
                    <div class="col-md-5">
                        <!-- boolean -->
                        <div v-if="it.type == 'bool'" class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" role="switch"
                                v-model="formValues[it.key]" :id="'set_' + it.key">
                        </div>
                        <!-- string with choices -->
                        <select v-else-if="it.type == 'str' && it.choices" class="form-select"
                            v-model="formValues[it.key]">
                            <option v-for="c in it.choices" :key="c" :value="c">{{ c }}</option>
                        </select>
                        <!-- plain string -->
                        <input v-else-if="it.type == 'str'" type="text" class="form-control"
                            v-model.trim="formValues[it.key]">
                        <!-- number -->
                        <input v-else-if="it.type == 'int' || it.type == 'float'" type="number"
                            class="form-control" :step="it.type == 'int' ? 1 : 'any'"
                            :min="it.min_value" :max="it.max_value" v-model.number="formValues[it.key]">
                        <!-- list of role/coded values -->
                        <div v-else-if="it.type == 'list' && it.choices"
                            class="d-flex flex-wrap gap-3">
                            <div class="form-check form-check-inline" v-for="c in it.choices" :key="c">
                                <input class="form-check-input" type="checkbox" :value="c"
                                    v-model="formValues[it.key]" :id="'set_' + it.key + '_' + c">
                                <label class="form-check-label" :for="'set_' + it.key + '_' + c">{{ c }}</label>
                            </div>
                        </div>
                        <!-- anything else declared as JSON (dict, or a list with no choices) -->
                        <textarea v-else rows="3" class="form-control font-monospace small"
                            :value="jsonText(it.key)" @input="setFromJson(it, $event.target.value)"></textarea>
                        <div v-if="errors[it.key]" class="text-danger small mt-1">{{ errors[it.key] }}</div>
                    </div>
                    <div class="col-md-4 small text-muted">
                        <div v-if="it.updated_by">
                            Last changed by <b>{{ it.updated_by }}</b> on {{ fmtTs(it.updated_ts) }}
                        </div>
                        <div v-else>Using the declared default &mdash; never explicitly set.</div>
                        <button class="btn btn-sm btn-outline-secondary mt-1" type="button"
                            :disabled="!it.updated_by" @click="resetSetting(it)">
                            Reset to default
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header">
                <b>Controlled Vocabularies</b>
                <span class="text-muted"> &mdash; dropdown/label lists used across the app</span>
            </div>
            <div class="card-body">
                <div class="card mb-3" v-for="it in vocabItems" :key="it.key">
                    <div class="card-header">
                        <span class="float-start">
                            <b>{{ it.name }}</b>
                            <span class="text-muted"> &mdash; {{ it.doc }}</span>
                        </span>
                        <span class="float-end">
                            <button class="btn btn-sm btn-outline-primary" type="button"
                                @click="addVocabRow(it)">
                                Add Item <i class="bi bi-plus-circle"></i>
                            </button>
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="row hdr-row mb-2 border-info border-bottom">
                            <div class="col-md-3">Code</div>
                            <div class="col-md-3">Label</div>
                            <div class="col-md-5">Other attributes</div>
                            <div class="col-md-1"></div>
                        </div>
                        <div v-if="!formValues[it.key] || formValues[it.key].length == 0"
                            class="text-muted mb-2">
                            No items yet.
                        </div>
                        <div class="row row-striped mb-2" v-for="(row, idx) in formValues[it.key]" :key="idx">
                            <div class="col-md-3">
                                <input type="text" class="form-control form-control-sm" v-model.trim="row.code">
                            </div>
                            <div class="col-md-3">
                                <input type="text" class="form-control form-control-sm" v-model.trim="row.label">
                            </div>
                            <div class="col-md-5">
                                <span class="me-3" v-for="k in extraKeys(row)" :key="k">
                                    <template v-if="typeof row[k] == 'boolean'">
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" v-model="row[k]"
                                                :id="'vc_' + it.key + '_' + idx + '_' + k">
                                            <label class="form-check-label"
                                                :for="'vc_' + it.key + '_' + idx + '_' + k">{{ k }}</label>
                                        </div>
                                    </template>
                                    <template v-else>
                                        {{ k }}:
                                        <input type="text" class="form-control form-control-sm d-inline-block"
                                            style="width: 8rem" v-model="row[k]">
                                    </template>
                                </span>
                            </div>
                            <div class="col-md-1">
                                <button class="btn btn-sm btn-outline-danger" type="button"
                                    @click="removeVocabRow(it, idx)">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div v-if="errors[it.key]" class="text-danger small mt-1">{{ errors[it.key] }}</div>
                        <div class="small text-muted mt-1">
                            <span v-if="it.updated_by">
                                Last changed by <b>{{ it.updated_by }}</b> on {{ fmtTs(it.updated_ts) }}
                            </span>
                            <span v-else>Using the declared default &mdash; never explicitly set.</span>
                            <button class="btn btn-sm btn-outline-secondary ms-2" type="button"
                                :disabled="!it.updated_by" @click="resetSetting(it)">
                                Reset to default
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="sticky-bottom bg-white py-2 border-top">
            <button class="btn btn-outline-success me-2" type="button" :disabled="!hasChanges" @click="saveAll">
                Save Changes <i class="bi bi-save"></i>
            </button>
            <button class="btn btn-outline-danger" type="button" :disabled="!hasChanges" @click="discardChanges">
                Discard Changes <i class="bi bi-eraser"></i>
            </button>
        </div>
    </div>
    <div v-else class="container-fluid">
        <div class="alert alert-danger mt-3">You are not authorized to view this page.</div>
    </div>
</template>

<script>
export default {
    name: "SystemSettingsAdmin",
    data: function () {
        return {
            items: [],
            formValues: {},
            errors: {}
        };
    },
    computed: {
        scalarGroups() {
            const byGroup = {};
            for (const it of this.items) {
                if (it.group == "vocab") continue;
                if (!byGroup[it.group]) byGroup[it.group] = { name: it.group, doc: it.group_doc, items: [] };
                byGroup[it.group].items.push(it);
            }
            return Object.values(byGroup).sort((a, b) => a.name.localeCompare(b.name));
        },
        vocabItems() {
            return this.items.filter(it => it.group == "vocab");
        },
        hasChanges() {
            return this.items.some(it => this.isDirty(it));
        }
    },
    mounted() {
        this.loadSettings();
    },
    methods: {
        loadSettings() {
            let vm = this;
            vm.doHttp(true, "settings_describe", null,
                (body) => vm.applyDescribe(body),
                (err) => vm.setStatusMessage(err));
        },
        applyDescribe(body) {
            let vm = this;
            vm.items = body;
            const fv = {};
            for (const it of body) {
                fv[it.key] = JSON.parse(JSON.stringify(it.value));
            }
            vm.formValues = fv;
            vm.errors = {};
        },
        isDirty(it) {
            return JSON.stringify(this.formValues[it.key]) !== JSON.stringify(it.value);
        },
        extraKeys(row) {
            return Object.keys(row).filter(k => k != "code" && k != "label");
        },
        addVocabRow(it) {
            if (!this.formValues[it.key]) this.formValues[it.key] = [];
            this.formValues[it.key].push({ code: "", label: "" });
        },
        removeVocabRow(it, idx) {
            this.formValues[it.key].splice(idx, 1);
        },
        jsonText(key) {
            return JSON.stringify(this.formValues[key], null, 2);
        },
        setFromJson(it, text) {
            try {
                this.formValues[it.key] = JSON.parse(text);
                if (this.errors[it.key]) delete this.errors[it.key];
            } catch {
                this.errors[it.key] = "Not valid JSON.";
            }
        },
        fmtTs(ts) {
            if (!ts) return "";
            try {
                return new Date(ts).toLocaleString();
            } catch {
                return ts;
            }
        },
        // Mirrors the shape (not every custom validator) of
        // settings_store._validate_value(), so a user is stopped before
        // the round trip, not instead of it -- the server still validates
        // on save.
        validateItem(it) {
            const v = this.formValues[it.key];
            const errs = [];
            const empty = v === null || v === undefined || v === "";
            if (empty) {
                errs.push("Value is required.");
                return errs;
            }
            if (it.type == "int" || it.type == "float") {
                const num = Number(v);
                if (Number.isNaN(num)) {
                    errs.push("Must be a number.");
                } else {
                    if (it.type == "int" && !Number.isInteger(num)) errs.push("Must be a whole number.");
                    if (it.min_value != null && num < it.min_value) errs.push(`Must be at least ${it.min_value}.`);
                    if (it.max_value != null && num > it.max_value) errs.push(`Must be at most ${it.max_value}.`);
                }
            } else if (it.type == "str") {
                if (it.choices && !it.choices.includes(v)) errs.push("Not one of the allowed values.");
                if (it.min_value != null && v.length < it.min_value)
                    errs.push(`Must be at least ${it.min_value} character(s).`);
                if (it.max_value != null && v.length > it.max_value)
                    errs.push(`Must be at most ${it.max_value} character(s).`);
            } else if (it.type == "list") {
                if (!Array.isArray(v)) {
                    errs.push("Must be a list.");
                } else {
                    if (it.min_value != null && v.length < it.min_value)
                        errs.push(`Must have at least ${it.min_value} item(s).`);
                    if (it.max_value != null && v.length > it.max_value)
                        errs.push(`Must have at most ${it.max_value} item(s).`);
                    if (it.group == "vocab") {
                        const seen = new Set();
                        for (const row of v) {
                            if (!row.code || !row.code.trim()) errs.push("Every item needs a non-empty code.");
                            if (!row.label || !row.label.trim()) errs.push("Every item needs a non-empty label.");
                            if (row.code && seen.has(row.code)) errs.push(`Duplicate code '${row.code}'.`);
                            if (row.code) seen.add(row.code);
                        }
                    } else if (it.choices) {
                        const bad = v.filter(x => !it.choices.includes(x));
                        if (bad.length) errs.push(`Not allowed: ${bad.join(", ")}.`);
                    }
                }
            } else if (it.type == "dict") {
                if (typeof v != "object" || Array.isArray(v)) errs.push("Must be a JSON object.");
            }
            return errs;
        },
        saveAll() {
            let vm = this;
            const changed = vm.items.filter(it => vm.isDirty(it));
            if (changed.length == 0) return;
            vm.errors = {};
            let valid = true;
            for (const it of changed) {
                const errs = vm.validateItem(it);
                if (errs.length) {
                    vm.errors[it.key] = errs.join(" ");
                    valid = false;
                }
            }
            if (!valid) {
                vm.setStatusMessage("Please fix the highlighted errors before saving.");
                return;
            }
            if (!confirm(`Confirm saving ${changed.length} changed setting(s)?`)) return;
            const values = {};
            for (const it of changed) values[it.key] = vm.formValues[it.key];
            vm.$http.post("settings_save", { values: values })
                .then(function (res) {
                    if (res.data.status == "OK") {
                        vm.setStatusMessage("Saved successfully!");
                        vm.applyDescribe(res.data.body);
                    } else {
                        vm.setStatusMessage(res.data.body);
                    }
                })
                .catch(function () {
                    vm.setStatusMessage("Error occurred when contacting the server.");
                });
        },
        discardChanges() {
            if (!confirm("Discard all unsaved changes?")) return;
            this.applyDescribe(this.items);
        },
        resetSetting(it) {
            if (!confirm(`Reset '${it.key}' to its declared default? This cannot be undone.`)) return;
            let vm = this;
            vm.$http.post("settings_delete", { key: it.key })
                .then(function (res) {
                    if (res.data.status == "OK") {
                        vm.setStatusMessage("Reset to default.");
                        vm.applyDescribe(res.data.body);
                    } else {
                        vm.setStatusMessage(res.data.body);
                    }
                })
                .catch(function () {
                    vm.setStatusMessage("Error occurred when contacting the server.");
                });
        }
    }
};
</script>
