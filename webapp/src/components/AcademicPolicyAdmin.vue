<!--
Admin screen for versioned, effective-dated academic policy (policy_store.py),
e.g. the grade point map. This is deliberately NOT an editor: a version
already referenced by a closed academic session is immutable, so every
recorded version below is read-only. The only write is "store a new
version" -- superseding, effective from a session that is still open.
There is no edit/delete action anywhere on this screen, by design.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid" v-if="hasPermission('system.manage_academic_policy')">
        <div class="row mb-2">
            <div class="col">
                <h4>Academic Policy Versions</h4>
                <small class="text-muted">
                    Effective-dated rulesets (e.g. the grade point map). A version
                    already used to compute a closed session's results is sealed and
                    cannot be changed &mdash; the only action is recording a new
                    version, effective from a session that is still open.
                </small>
            </div>
        </div>

        <div class="row mb-3">
            <div class="col-md-4">
                <label>Policy group</label>
                <select class="form-select" v-model="selectedGroup" @change="loadVersions">
                    <option value="" disabled>-Select-</option>
                    <option v-for="g in groups" :key="g.name" :value="g.name">{{ g.name }}</option>
                </select>
            </div>
        </div>

        <template v-if="selectedGroup">
            <div class="alert alert-secondary">
                <b>{{ selectedGroup }}</b> &mdash; {{ groupDoc }}
                <div class="mt-1">
                    <span v-if="sealLine">
                        Policy is <b>sealed</b> up to and including
                        <b>{{ sealLine }}</b> &mdash; a new version must take effect from a later
                        session.
                    </span>
                    <span v-else>No academic session has been closed yet; every version is still open.</span>
                </div>
            </div>

            <div class="card mb-3">
                <div class="card-header">Recorded versions (oldest first)</div>
                <div class="card-body">
                    <div v-if="versions.length == 0" class="text-muted">
                        No version of this policy group has been recorded yet.
                    </div>
                    <div class="row hdr-row mb-2 border-info border-bottom" v-if="versions.length">
                        <div class="col-md-2">Effective range</div>
                        <div class="col-md-1">Status</div>
                        <div class="col-md-3">Governs (closed sessions)</div>
                        <div class="col-md-2">Recorded by / when</div>
                        <div class="col-md-2">Note</div>
                        <div class="col-md-2"></div>
                    </div>
                    <template v-for="v in versions" :key="v.version_id">
                        <div class="row row-striped mb-2 align-items-start">
                            <div class="col-md-2">
                                <b>{{ v.effective_from }}</b> &rarr;
                                {{ v.effective_to ? v.effective_to : "(open-ended)" }}
                            </div>
                            <div class="col-md-1">
                                <span class="badge" :class="v.is_sealed ? 'bg-secondary' : 'bg-success'">
                                    {{ v.is_sealed ? "Sealed" : "Open" }}
                                </span>
                            </div>
                            <div class="col-md-3">
                                <span v-if="v.closed_sessions_governed.length == 0" class="text-muted">none closed yet</span>
                                <span v-else class="badge bg-light text-dark border me-1"
                                    v-for="s in v.closed_sessions_governed" :key="s">{{ s }}</span>
                            </div>
                            <div class="col-md-2 small">
                                {{ v.recorded_by || "-" }}<br>
                                {{ fmtTs(v.recorded_ts) }}
                            </div>
                            <div class="col-md-2 small">{{ v.note || "-" }}</div>
                            <div class="col-md-2">
                                <button class="btn btn-sm btn-outline-secondary me-1" type="button"
                                    @click="toggleView(v)">
                                    {{ expanded === v.version_id ? "Hide" : "View" }} payload
                                </button>
                                <button class="btn btn-sm btn-outline-primary" type="button"
                                    :disabled="v.version_id !== latestVersionId"
                                    :title="v.version_id !== latestVersionId ?
                                        'Only the latest version can be used as a starting point.' : ''"
                                    @click="useAsTemplate(v)">
                                    Use as template
                                </button>
                            </div>
                        </div>
                        <div class="row mb-3" v-if="expanded === v.version_id">
                            <div class="col">
                                <pre class="bg-light p-2 border small">{{ JSON.stringify(v.payload, null, 2) }}</pre>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <div class="card mb-3">
                <div class="card-header">
                    Store a new version
                    <span class="text-muted">&mdash; supersedes the ruleset above from a chosen session onward; it does not change any existing version</span>
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-md-4">
                            <acad-session label="Effective from session" v-bind:acad_session="form.effective_from_session"
                                v-on:update:acad_session="onSessionChange" />
                            <div v-if="!v$.form.effective_from_session.required && v$.form.effective_from_session.$dirty"
                                class="text-danger small">This is a required field</div>
                            <div v-else-if="!v$.form.effective_from_session.validsession && v$.form.effective_from_session.$dirty"
                                class="text-danger small">Session is invalid</div>
                        </div>
                        <div class="col-md-8">
                            <label>Note (authority for the change &mdash; circular/minute number)</label>
                            <input type="text" class="form-control" v-model.trim="form.note">
                        </div>
                    </div>
                    <div class="mb-2">
                        <label>
                            Complete ruleset payload (JSON) &mdash; the whole ruleset, not a patch on the
                            previous version
                        </label>
                        <textarea rows="16" class="form-control font-monospace small"
                            v-model="form.payloadText"></textarea>
                        <div v-if="!v$.form.payloadText.required && v$.form.payloadText.$dirty"
                            class="text-danger small">This is a required field</div>
                        <div v-else-if="!v$.form.payloadText.validjson && v$.form.payloadText.$dirty"
                            class="text-danger small">Not valid JSON</div>
                    </div>
                    <div v-if="validationMsg" :class="validationOk ? 'text-success' : 'text-danger'" class="mb-2">
                        {{ validationMsg }}
                    </div>
                    <button class="btn btn-outline-secondary me-2" type="button" @click="validatePayload">
                        Validate <i class="bi bi-check2-circle"></i>
                    </button>
                    <button class="btn btn-outline-success" type="button" @click="storeNewVersion">
                        Store New Version <i class="bi bi-save"></i>
                    </button>
                    <div class="text-muted small mt-2">
                        There is no "save" over an existing version &mdash; this always inserts a brand new
                        one, and every version recorded above remains exactly as it is.
                    </div>
                </div>
            </div>
        </template>
    </div>
    <div v-else class="container-fluid">
        <div class="alert alert-danger mt-3">You are not authorized to view this page.</div>
    </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required } from '@vuelidate/validators'
import AcadSession from "./AcadSession.vue"

export default {
    name: "AcademicPolicyAdmin",
    components: { "AcadSession": AcadSession },
    setup() {
        return { v$: useVuelidate() }
    },
    data: function () {
        return {
            groups: [],
            selectedGroup: "",
            groupDoc: "",
            sealLine: null,
            versions: [],
            expanded: null,
            validationMsg: "",
            validationOk: false,
            form: {
                effective_from_session: "",
                note: "",
                payloadText: ""
            }
        };
    },
    computed: {
        latestVersionId() {
            return this.versions.length ? this.versions[this.versions.length - 1].version_id : null;
        }
    },
    mounted() {
        this.loadGroups();
    },
    methods: {
        loadGroups() {
            let vm = this;
            vm.doHttp(true, "policy_groups", null,
                (body) => { vm.groups = body; },
                (err) => vm.setStatusMessage(err));
        },
        loadVersions() {
            let vm = this;
            vm.expanded = null;
            vm.validationMsg = "";
            if (!vm.selectedGroup) return;
            vm.doHttp(true, "policy_versions/" + vm.selectedGroup, null,
                (body) => {
                    vm.groupDoc = body.doc;
                    vm.sealLine = body.seal_line;
                    vm.versions = body.versions;
                },
                (err) => vm.setStatusMessage(err));
        },
        toggleView(v) {
            this.expanded = this.expanded === v.version_id ? null : v.version_id;
        },
        useAsTemplate(v) {
            this.form.note = "";
            this.form.effective_from_session = "";
            this.form.payloadText = JSON.stringify(v.payload, null, 2);
            this.validationMsg = "";
            this.v$.form.$reset();
        },
        onSessionChange(s) {
            this.form.effective_from_session = s;
        },
        parsedPayload() {
            try {
                return JSON.parse(this.form.payloadText);
            } catch {
                return null;
            }
        },
        validatePayload() {
            let vm = this;
            vm.v$.form.payloadText.$touch();
            const payload = vm.parsedPayload();
            if (payload === null) {
                vm.validationOk = false;
                vm.validationMsg = "Payload is not valid JSON.";
                return;
            }
            vm.$http.post("policy_validate", { group: vm.selectedGroup, payload: payload })
                .then(function (res) {
                    vm.validationOk = res.data.status == "OK";
                    vm.validationMsg = vm.validationOk ? "Payload is valid." : res.data.body;
                })
                .catch(function () {
                    vm.validationOk = false;
                    vm.validationMsg = "Error occurred when contacting the server.";
                });
        },
        storeNewVersion() {
            let vm = this;
            vm.v$.form.$touch();
            if (vm.v$.form.$invalid) {
                return;
            }
            const payload = vm.parsedPayload();
            if (payload === null) {
                vm.validationMsg = "Payload is not valid JSON.";
                vm.validationOk = false;
                return;
            }
            if (!confirm(
                `Store a new '${vm.selectedGroup}' policy version effective from ` +
                `${vm.form.effective_from_session}?\n\nThis adds a new version; it does ` +
                "not change any existing one, and it cannot be edited or removed later.")) {
                return;
            }
            vm.$http.post("policy_supersede", {
                group: vm.selectedGroup,
                effective_from_session: vm.form.effective_from_session,
                payload: payload,
                note: vm.form.note
            })
                .then(function (res) {
                    if (res.data.status == "OK") {
                        vm.setStatusMessage("New policy version stored.");
                        vm.sealLine = res.data.body.seal_line;
                        vm.versions = res.data.body.versions;
                        vm.form = { effective_from_session: "", note: "", payloadText: "" };
                        vm.v$.form.$reset();
                        vm.validationMsg = "";
                    } else {
                        vm.setStatusMessage(res.data.body);
                    }
                })
                .catch(function () {
                    vm.setStatusMessage("Error occurred when contacting the server.");
                });
        },
        fmtTs(ts) {
            if (!ts) return "";
            try {
                return new Date(ts).toLocaleString();
            } catch {
                return ts;
            }
        }
    },
    validations() {
        return {
            form: {
                effective_from_session: {
                    required,
                    validsession() {
                        return this.acadSessionRegExp.test(this.form.effective_from_session);
                    }
                },
                payloadText: {
                    required,
                    validjson() {
                        return this.parsedPayload() !== null;
                    }
                }
            }
        };
    }
};
</script>
