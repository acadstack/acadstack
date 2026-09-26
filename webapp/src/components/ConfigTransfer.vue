<!--
Admin screen for exporting/importing the full configuration document
(config_transfer.py): every settings/vocabulary group (including the
permission->role mapping) plus the complete academic-policy history, as
one JSON file. Used for cloning a configured institution, seeding a test
fixture with known policy, or reviewing a policy change out-of-band by
diffing two exports.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid">
        <div class="row mb-2">
            <div class="col">
                <h4>Configuration Export / Import</h4>
                <small class="text-muted">
                    The institution's full DB-backed configuration -- settings, controlled
                    vocabularies, the permission-&gt;role mapping and academic-policy history --
                    as one JSON document.
                </small>
            </div>
        </div>

        <div class="card mb-3" v-if="hasPermission('system.export_config')">
            <div class="card-header"><b>Export</b></div>
            <div class="card-body">
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" id="exp_perms"
                        v-model="includePermissions">
                    <label class="form-check-label" for="exp_perms">
                        Include the permission-&gt;role mapping
                    </label>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="exp_hist"
                        v-model="includePolicyHistory">
                    <label class="form-check-label" for="exp_hist">
                        Include full academic-policy history (not just the version in force now)
                    </label>
                </div>
                <button class="btn btn-outline-primary" type="button" @click="exportConfig">
                    Download Configuration <i class="bi bi-download"></i>
                </button>
            </div>
        </div>

        <div class="card mb-3" v-if="hasPermission('system.import_config')">
            <div class="card-header"><b>Import</b></div>
            <div class="card-body">
                <input class="form-control mb-3" type="file" accept="application/json"
                    ref="fileInput" @change="onFileChosen">

                <div v-if="parseError" class="alert alert-danger">{{ parseError }}</div>

                <div v-if="pendingDoc">
                    <p class="mb-2">
                        Document version {{ pendingDoc.acadstack_config_version }},
                        exported {{ fmtTs(pendingDoc.exported_at) }}.
                    </p>
                    <ul>
                        <li v-if="settingsGroupCount">
                            {{ settingsGroupCount }} settings group(s):
                            {{ Object.keys(pendingDoc.settings || {}).join(", ") }}
                        </li>
                        <li v-if="workflowNames.length">
                            {{ workflowNames.length }} workflow(s):
                            {{ workflowNames.join(", ") }}
                        </li>
                        <li v-if="policyGroupCount">
                            {{ policyGroupCount }} policy group(s) with
                            {{ policyVersionCount }} version(s) total:
                            {{ Object.keys(pendingDoc.policy || {}).join(", ") }}
                        </li>
                    </ul>
                    <div class="alert alert-warning">
                        Importing REPLACES this install's current value for every settings/
                        vocabulary group and workflow named above. Policy versions can only be added (never
                        replace what is already recorded) -- one that clashes with an existing
                        version, or lands at or before a closed session, is skipped and reported,
                        not applied.
                    </div>
                    <button class="btn btn-outline-danger" type="button" @click="doImport">
                        Import This Document <i class="bi bi-upload"></i>
                    </button>
                </div>

                <div v-if="importReport" class="mt-3">
                    <h6>Import result</h6>
                    <p v-if="importReport.settings_applied.length">
                        Applied settings:
                        <code>{{ importReport.settings_applied.join(", ") }}</code>
                    </p>
                    <p v-if="(importReport.workflows_applied || []).length">
                        Applied workflows:
                        <code>{{ importReport.workflows_applied.join(", ") }}</code>
                    </p>
                    <div v-for="(entries, group) in importReport.policy" :key="group" class="mb-2">
                        <b>{{ group }}</b>
                        <ul class="mb-0">
                            <li v-for="e in entries" :key="e.effective_from_session">
                                {{ e.effective_from_session }} &mdash;
                                <span :class="e.status == 'applied' ? 'text-success' : 'text-muted'">
                                    {{ e.status }}
                                </span>
                                <span v-if="e.reason" class="text-muted"> ({{ e.reason }})</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="!hasPermission('system.export_config') && !hasPermission('system.import_config')"
            class="alert alert-danger mt-3">
            You are not authorized to view this page.
        </div>
    </div>
</template>

<script>
export default {
    name: "ConfigTransfer",
    data: function () {
        return {
            includePermissions: true,
            includePolicyHistory: true,
            pendingDoc: null,
            parseError: "",
            importReport: null
        };
    },
    computed: {
        settingsGroupCount() {
            return this.pendingDoc ? Object.keys(this.pendingDoc.settings || {}).length : 0;
        },
        workflowNames() {
            return this.pendingDoc ? Object.keys(this.pendingDoc.workflows || {}) : [];
        },
        policyGroupCount() {
            return this.pendingDoc ? Object.keys(this.pendingDoc.policy || {}).length : 0;
        },
        policyVersionCount() {
            if (!this.pendingDoc || !this.pendingDoc.policy) return 0;
            return Object.values(this.pendingDoc.policy).reduce((n, vs) => n + vs.length, 0);
        }
    },
    methods: {
        fmtTs(ts) {
            if (!ts) return "";
            try {
                return new Date(ts).toLocaleString();
            } catch {
                return ts;
            }
        },
        exportConfig() {
            let vm = this;
            const params = {
                include_permissions: vm.includePermissions,
                include_policy_history: vm.includePolicyHistory
            };
            vm.$http.get("config_export", { params: params })
                .then(function (res) {
                    if (res.data.status != "OK") {
                        vm.setStatusMessage(res.data.body);
                        return;
                    }
                    const doc = res.data.body;
                    const blob = new Blob([JSON.stringify(doc, null, 2)],
                        { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    const stamp = new Date().toISOString().slice(0, 10);
                    a.href = url;
                    a.download = `acadstack-config-${stamp}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                })
                .catch(function () {
                    vm.setStatusMessage("Error occurred when contacting the server.");
                });
        },
        onFileChosen(evt) {
            let vm = this;
            vm.pendingDoc = null;
            vm.parseError = "";
            vm.importReport = null;
            const file = evt.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function () {
                try {
                    vm.pendingDoc = JSON.parse(reader.result);
                } catch {
                    vm.parseError = "That file is not valid JSON.";
                }
            };
            reader.readAsText(file);
        },
        doImport() {
            let vm = this;
            if (!confirm("Import this configuration document? This will overwrite " +
                "matching settings/vocabulary groups on this install.")) return;
            vm.$http.post("config_import", { document: vm.pendingDoc })
                .then(function (res) {
                    if (res.data.status == "OK") {
                        vm.setStatusMessage("Import complete.");
                        vm.importReport = res.data.body;
                        vm.pendingDoc = null;
                        if (vm.$refs.fileInput) vm.$refs.fileInput.value = "";
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
