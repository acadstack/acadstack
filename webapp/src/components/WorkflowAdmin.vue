<!--
Admin screen for the approval workflows' transition tables
(domain/workflow.py). Pick a workflow, edit its rows as a table, save the
whole definition back through workflow_save, i.e. save_workflow(), which
validates it and refuses an edit that would strand records in a status
they could no longer leave. Its errors come back tagged with the row they
are about and are shown against that row.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid" v-if="hasPermission('system.manage_workflows')">
        <div class="row mb-2">
            <div class="col">
                <h4>Approval Workflows</h4>
                <small class="text-muted">
                    Each row lets holders of a permission move a record from one status to another,
                    when its guards hold and its checks pass. For each request the first applicable row,
                    by priority, is taken. Changes take effect immediately.
                </small>
            </div>
            <div class="col-md-3">
                <select class="form-select" :value="selectedName" @change="selectWorkflow($event)">
                    <option value="" disabled>-- choose a workflow --</option>
                    <option v-for="n in names" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>
        </div>

        <template v-if="form">
            <div class="alert alert-danger" v-if="generalErrors.length || strandedList.length">
                <div v-for="(e, i) in generalErrors" :key="'g' + i">{{ e }}</div>
                <div v-if="strandedList.length" class="mt-1">
                    Records are waiting in these statuses and would have no way out:
                    <span class="badge bg-danger me-1" v-for="s in strandedList" :key="s.code">
                        {{ statusLabel(s.code) }}: {{ s.count }}
                    </span>
                </div>
            </div>

            <div class="card mb-3">
                <div class="card-header">
                    <b>{{ form.name }}</b>
                    <span class="text-muted">
                        &mdash; statuses from <code>{{ form.status_vocab }}</code>; a request is matched on
                        <b>{{ form.match_on == 'action' ? 'the action named' : 'the status asked for' }}</b>
                    </span>
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-md-6">
                            <label class="form-label small mb-0">Locked message</label>
                            <input type="text" class="form-control form-control-sm" v-model="form.locked_message">
                            <div class="form-text">
                                Shown when no row leaving the record's status is open to the user.
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small mb-0">Denied message</label>
                            <input type="text" class="form-control form-control-sm" v-model="form.denied_message">
                            <div class="form-text">
                                Shown when rows are open to the user but none matches the request.
                                Both may use {role}, {from_label}, {to_label}, {from_status}, {to_status}.
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <label class="form-label small mb-0">Pre-checks (run before any row is chosen)</label>
                            <WorkflowStepsEditor v-model="form.pre_checks" :options="registered.checks"
                                noun="pre-check" />
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small mb-0">Checks (run for every chosen row)</label>
                            <WorkflowStepsEditor v-model="form.checks" :options="registered.checks" noun="check" />
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-3">
                <div class="card-header d-flex align-items-center gap-2">
                    <b class="me-auto">Transitions ({{ form.transitions.length }})</b>
                    <select class="form-select form-select-sm w-auto" v-model="statusFilter"
                        title="Show only rows leaving or entering this status">
                        <option value="">All statuses</option>
                        <option v-for="o in fromOptions" :key="o.code" :value="o.code">{{ o.label }}</option>
                    </select>
                    <div class="form-check form-check-inline mb-0" v-if="Object.keys(rowErrors).length">
                        <input class="form-check-input" type="checkbox" id="wf_err_only" v-model="errorsOnly">
                        <label class="form-check-label small" for="wf_err_only">Rows with errors only</label>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" type="button" @click="addRow">
                        Add Row <i class="bi bi-plus-circle"></i>
                    </button>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm mb-0 align-middle">
                            <thead>
                                <tr class="small">
                                    <th style="width: 6rem">Priority</th>
                                    <th>From</th>
                                    <th>To</th>
                                    <th>Action</th>
                                    <th>Label</th>
                                    <th>Permission</th>
                                    <th>Guards / Checks / Effects</th>
                                    <th class="text-center">Active</th>
                                    <th style="width: 7rem"></th>
                                </tr>
                            </thead>
                            <tbody>
                                <template v-for="row in visibleRows" :key="row.t._key">
                                    <tr :class="{
                                        'table-danger': rowErrors[row.idx],
                                        'text-muted': !row.t.is_active && !rowErrors[row.idx]
                                    }">
                                        <td>
                                            <input type="number" step="1" class="form-control form-control-sm"
                                                v-model.number="row.t.priority">
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm" v-model="row.t.from_status">
                                                <option v-for="o in fromOptions" :key="o.code" :value="o.code">
                                                    {{ o.label }}
                                                </option>
                                            </select>
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm" v-model="row.t.to_status">
                                                <option v-for="o in toOptions" :key="o.code" :value="o.code">
                                                    {{ o.label }}
                                                </option>
                                            </select>
                                        </td>
                                        <td>
                                            <input type="text" class="form-control form-control-sm"
                                                v-model.trim="row.t.action"
                                                :placeholder="form.match_on == 'action' ? 'required' : ''">
                                        </td>
                                        <td>
                                            <input type="text" class="form-control form-control-sm"
                                                v-model="row.t.label">
                                        </td>
                                        <td>
                                            <select class="form-select form-select-sm" v-model="row.t.permission">
                                                <option v-if="!permissions.includes(row.t.permission)"
                                                    :value="row.t.permission">
                                                    {{ row.t.permission || "-- choose --" }}
                                                </option>
                                                <option v-for="p in permissions" :key="p" :value="p">{{ p }}</option>
                                            </select>
                                        </td>
                                        <td class="small">
                                            <span class="badge bg-info text-dark me-1" v-for="g in row.t.guards" :key="'g' + g"
                                                title="guard">{{ g }}</span>
                                            <span class="badge bg-warning text-dark me-1" v-for="(s, i) in row.t.checks"
                                                :key="'c' + i" title="check">{{ s.name }}</span>
                                            <span class="badge bg-secondary me-1" v-for="(s, i) in row.t.effects"
                                                :key="'e' + i" title="effect">{{ s.name }}</span>
                                        </td>
                                        <td class="text-center">
                                            <input class="form-check-input" type="checkbox" v-model="row.t.is_active">
                                        </td>
                                        <td class="text-end text-nowrap">
                                            <button class="btn btn-sm btn-outline-secondary me-1" type="button"
                                                title="Edit guards, checks and effects" @click="toggleExpanded(row.t)">
                                                <i class="bi" :class="expanded[row.t._key]
                                                    ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-secondary me-1" type="button"
                                                title="Duplicate row" @click="duplicateRow(row.idx)">
                                                <i class="bi bi-files"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-danger" type="button"
                                                title="Remove row" @click="removeRow(row.idx)">
                                                <i class="bi bi-trash"></i>
                                            </button>
                                        </td>
                                    </tr>
                                    <tr v-if="rowErrors[row.idx]" class="table-danger">
                                        <td colspan="9" class="small text-danger pt-0">
                                            <div v-for="(e, i) in rowErrors[row.idx]" :key="i">{{ e }}</div>
                                        </td>
                                    </tr>
                                    <tr v-if="expanded[row.t._key]" class="table-light">
                                        <td colspan="9">
                                            <div class="row">
                                                <div class="col-md-4">
                                                    <label class="form-label small mb-1">
                                                        Guards &mdash; all must hold for the row to apply
                                                    </label>
                                                    <div class="mb-1" v-if="row.t.guards.length == 0">
                                                        <span class="small text-muted">None.</span>
                                                    </div>
                                                    <div class="d-flex align-items-center mb-1"
                                                        v-for="(g, gi) in row.t.guards" :key="gi">
                                                        <div class="form-check form-check-inline mb-0">
                                                            <input class="form-check-input" type="checkbox"
                                                                :id="'neg_' + row.t._key + '_' + gi"
                                                                :checked="g.startsWith('!')"
                                                                @change="negateGuard(row.t, gi, $event.target.checked)">
                                                            <label class="form-check-label small"
                                                                :for="'neg_' + row.t._key + '_' + gi">not</label>
                                                        </div>
                                                        <code class="me-auto">{{ g.replace(/^!/, "") }}</code>
                                                        <button class="btn btn-sm btn-outline-danger" type="button"
                                                            title="Remove" @click="row.t.guards.splice(gi, 1)">
                                                            <i class="bi bi-trash"></i>
                                                        </button>
                                                    </div>
                                                    <select class="form-select form-select-sm"
                                                        @change="addGuard(row.t, $event)">
                                                        <option value="">-- add a guard --</option>
                                                        <option v-for="g in registered.guards" :key="g" :value="g">
                                                            {{ g }}
                                                        </option>
                                                    </select>
                                                </div>
                                                <div class="col-md-4">
                                                    <label class="form-label small mb-1">
                                                        Checks &mdash; must pass, or the request is refused
                                                    </label>
                                                    <WorkflowStepsEditor v-model="row.t.checks"
                                                        :options="registered.checks" noun="check" />
                                                </div>
                                                <div class="col-md-4">
                                                    <label class="form-label small mb-1">
                                                        Effects &mdash; run after the record is saved
                                                    </label>
                                                    <WorkflowStepsEditor v-model="row.t.effects"
                                                        :options="registered.effects" noun="effect" />
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                                <tr v-if="visibleRows.length == 0">
                                    <td colspan="9" class="text-muted">No rows to show.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="sticky-bottom bg-white py-2 border-top">
                <button class="btn btn-outline-success me-2" type="button" :disabled="!hasChanges" @click="save">
                    Save Workflow <i class="bi bi-save"></i>
                </button>
                <button class="btn btn-outline-danger" type="button" :disabled="!hasChanges" @click="discardChanges">
                    Discard Changes <i class="bi bi-eraser"></i>
                </button>
            </div>
        </template>
    </div>
    <div v-else class="container-fluid">
        <div class="alert alert-danger mt-3">You are not authorized to view this page.</div>
    </div>
</template>

<script>
import WorkflowStepsEditor from "./WorkflowStepsEditor.vue";

let nextKey = 1;

function stepsToForm(steps) {
    return (steps || []).map(s => ({
        name: s.name,
        paramsText: s.params && Object.keys(s.params).length ? JSON.stringify(s.params) : ""
    }));
}

export default {
    name: "WorkflowAdmin",
    components: { WorkflowStepsEditor },
    data: function () {
        return {
            names: [],
            selectedName: "",
            registered: { guards: [], checks: [], effects: [] },
            statuses: [],
            special: {},
            permissions: [],
            // The editable definition, and the saved one it started from
            // (serialized, for change detection).
            form: null,
            savedText: "",
            expanded: {},
            statusFilter: "",
            errorsOnly: false,
            generalErrors: [],
            rowErrors: {},
            stranded: {}
        };
    },
    computed: {
        fromOptions() {
            return [
                { code: this.special.new, label: "(new record)" },
                { code: this.special.any, label: "(any status)" },
                ...this.statuses.map(s => ({ code: s.code, label: `${s.label} (${s.code})` }))
            ];
        },
        toOptions() {
            return [
                { code: this.special.same, label: "(unchanged)" },
                ...this.statuses.map(s => ({ code: s.code, label: `${s.label} (${s.code})` }))
            ];
        },
        visibleRows() {
            if (!this.form) return [];
            return this.form.transitions
                .map((t, idx) => ({ t, idx }))
                .filter(({ t, idx }) =>
                    (!this.statusFilter || t.from_status == this.statusFilter || t.to_status == this.statusFilter) &&
                    (!this.errorsOnly || this.rowErrors[idx]));
        },
        strandedList() {
            return Object.entries(this.stranded).map(([code, count]) => ({ code, count }));
        },
        hasChanges() {
            return !!this.form && JSON.stringify(this.toDefinition().definition) !== this.savedText;
        }
    },
    mounted() {
        let vm = this;
        vm.doHttp(true, "workflows", null,
            (body) => { vm.names = body; },
            (err) => vm.setStatusMessage(err));
    },
    methods: {
        selectWorkflow(ev) {
            const name = ev.target.value;
            if (this.hasChanges && !confirm("Discard unsaved changes to this workflow?")) {
                ev.target.value = this.selectedName;
                return;
            }
            this.selectedName = name;
            this.loadWorkflow(name);
        },
        loadWorkflow(name) {
            let vm = this;
            vm.doHttp(true, "workflow/" + encodeURIComponent(name), null,
                (body) => {
                    vm.registered = body.registered;
                    vm.statuses = body.statuses;
                    vm.special = body.special_statuses;
                    vm.permissions = body.permissions;
                    vm.applyWorkflow(body.workflow);
                },
                (err) => vm.setStatusMessage(err));
        },
        applyWorkflow(wf) {
            this.form = {
                name: wf.name,
                status_vocab: wf.status_vocab,
                match_on: wf.match_on,
                locked_message: wf.locked_message,
                denied_message: wf.denied_message,
                pre_checks: stepsToForm(wf.pre_checks),
                checks: stepsToForm(wf.checks),
                transitions: wf.transitions.map(t => ({
                    _key: nextKey++,
                    priority: t.priority,
                    from_status: t.from_status,
                    to_status: t.to_status,
                    action: t.action || "",
                    label: t.label,
                    permission: t.permission,
                    guards: [...t.guards],
                    checks: stepsToForm(t.checks),
                    effects: stepsToForm(t.effects),
                    is_active: t.is_active
                }))
            };
            this.savedText = JSON.stringify(this.toDefinition().definition);
            this.expanded = {};
            this.statusFilter = "";
            this.errorsOnly = false;
            this.clearErrors();
        },
        clearErrors() {
            this.generalErrors = [];
            this.rowErrors = {};
            this.stranded = {};
        },
        // The form as save_workflow() takes it, plus the problems that can
        // be caught before sending it (the server re-checks everything).
        // Unparseable parameters are sent as their raw text, which only
        // matters for change detection: a definition with problems is
        // never sent.
        toDefinition() {
            const problems = [];
            const stepsOut = (steps, row, what) => steps.map(s => {
                const out = { name: s.name };
                if (!s.name) problems.push({ row, message: `A ${what} has no name.` });
                const text = (s.paramsText || "").trim();
                if (text) {
                    let params = null;
                    try {
                        params = JSON.parse(text);
                    } catch {
                        params = null;
                    }
                    if (params === null || typeof params != "object" || Array.isArray(params)) {
                        problems.push({ row, message: `${what} '${s.name}': parameters must be a JSON object.` });
                        out.params = text;
                    } else if (Object.keys(params).length) {
                        out.params = params;
                    }
                }
                return out;
            });
            const f = this.form;
            const seen = new Set();
            const transitions = f.transitions.map((t, idx) => {
                const where = `Row ${idx + 1}`;
                if (!Number.isInteger(t.priority)) {
                    problems.push({ row: idx, message: `${where}: priority must be a whole number.` });
                } else if (seen.has(t.priority)) {
                    problems.push({ row: idx, message: `${where}: duplicate priority ${t.priority}.` });
                }
                seen.add(t.priority);
                if (!t.permission) problems.push({ row: idx, message: `${where}: a permission is required.` });
                if (f.match_on == "action" && !t.action) {
                    problems.push({ row: idx, message: `${where}: an action is required.` });
                }
                return {
                    priority: t.priority,
                    from_status: t.from_status,
                    to_status: t.to_status,
                    action: t.action || null,
                    label: t.label || "",
                    permission: t.permission,
                    guards: [...t.guards],
                    checks: stepsOut(t.checks, idx, "check"),
                    effects: stepsOut(t.effects, idx, "effect"),
                    is_active: !!t.is_active
                };
            });
            return {
                definition: {
                    name: f.name,
                    status_vocab: f.status_vocab,
                    match_on: f.match_on,
                    locked_message: f.locked_message,
                    denied_message: f.denied_message,
                    pre_checks: stepsOut(f.pre_checks, null, "pre-check"),
                    checks: stepsOut(f.checks, null, "check"),
                    transitions
                },
                problems
            };
        },
        showProblems(problems, stranded) {
            this.clearErrors();
            const rows = {};
            for (const p of problems) {
                if (p.row === null || p.row === undefined) {
                    this.generalErrors.push(p.message);
                } else {
                    (rows[p.row] = rows[p.row] || []).push(p.message);
                }
            }
            this.rowErrors = rows;
            this.stranded = stranded || {};
        },
        // Server errors point at rows by position, so once rows are added
        // or removed they no longer line up and are dropped.
        rowsChanged() {
            if (Object.keys(this.rowErrors).length) {
                this.rowErrors = {};
                this.errorsOnly = false;
                this.setStatusMessage("Rows changed; save again to re-check them.");
            }
        },
        nextPriority() {
            const ps = this.form.transitions.map(t => t.priority).filter(Number.isInteger);
            return ps.length ? Math.max(...ps) + 10 : 100;
        },
        addRow() {
            this.form.transitions.push({
                _key: nextKey++,
                priority: this.nextPriority(),
                from_status: this.statuses.length ? this.statuses[0].code : this.special.any,
                to_status: this.special.same,
                action: "",
                label: "",
                permission: "",
                guards: [],
                checks: [],
                effects: [],
                is_active: true
            });
            this.statusFilter = "";
            this.rowsChanged();
        },
        duplicateRow(idx) {
            const copy = JSON.parse(JSON.stringify(this.form.transitions[idx]));
            copy._key = nextKey++;
            copy.priority = this.nextPriority();
            this.form.transitions.splice(idx + 1, 0, copy);
            this.rowsChanged();
        },
        removeRow(idx) {
            const t = this.form.transitions[idx];
            if (!confirm(`Remove the row ${t.priority} (${t.from_status} -> ${t.to_status})?`)) return;
            this.form.transitions.splice(idx, 1);
            this.rowsChanged();
        },
        toggleExpanded(t) {
            this.expanded[t._key] = !this.expanded[t._key];
        },
        addGuard(t, ev) {
            const name = ev.target.value;
            ev.target.value = "";
            if (name && !t.guards.some(g => g.replace(/^!/, "") == name)) t.guards.push(name);
        },
        negateGuard(t, gi, negate) {
            const bare = t.guards[gi].replace(/^!/, "");
            t.guards[gi] = negate ? "!" + bare : bare;
        },
        statusLabel(code) {
            const s = this.statuses.find(x => x.code == code);
            return s ? `${s.label} (${code})` : code;
        },
        save() {
            let vm = this;
            const { definition, problems } = vm.toDefinition();
            if (problems.length) {
                vm.showProblems(problems);
                vm.setStatusMessage("Please fix the highlighted errors before saving.");
                return;
            }
            if (!confirm(`Save the '${definition.name}' workflow? It takes effect immediately.`)) return;
            vm.doHttp(false, "workflow_save", definition,
                (body) => {
                    vm.setStatusMessage("Saved successfully!");
                    vm.applyWorkflow(body);
                },
                (err) => {
                    if (err && typeof err == "object") {
                        vm.showProblems(err.errors || [], err.stranded);
                        vm.setStatusMessage("The workflow was not saved; see the highlighted errors.");
                    } else {
                        vm.setStatusMessage(err);
                    }
                });
        },
        discardChanges() {
            if (!confirm("Discard all unsaved changes?")) return;
            this.loadWorkflow(this.selectedName);
        }
    }
};
</script>

<style scoped>
/* GenerateSemesterGrade.vue and BulkDownloadGradeSheet.vue style every
   table in the app through an unscoped <style> (a left margin that pushes
   this table's last column off-screen, and cell borders); undone here. */
table {
    margin: 0;
}

table td {
    border-right: none;
}
</style>
