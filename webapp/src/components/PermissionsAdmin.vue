<!--
Admin screen for the permission->role mapping (permissions.py): a matrix
of every declared permission against every role, grouped by the
permission's prefix (course., grades., ...). Saved through
permissions_save, i.e. permissions.save_permission_mapping(), whose
self-lockout guard refuses a save that would remove the admin's own role
from system.manage_permissions; that one cell is disabled here too.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid" v-if="hasPermission('system.manage_permissions')">
        <div class="row mb-2">
            <div class="col">
                <h4>Permissions</h4>
                <small class="text-muted">
                    Which roles may do what. Changes take effect on each user's next request; a
                    user's menu reflects them after they next log in (including yours).
                </small>
            </div>
            <div class="col-md-4">
                <input type="search" class="form-control" v-model.trim="filterText"
                    placeholder="Filter by permission name or description">
            </div>
        </div>

        <div class="card mb-3" v-for="grp in visibleGroups" :key="grp.prefix">
            <div class="card-header">
                <b>{{ grp.prefix }}.</b>
                <span class="text-muted" v-if="grp.prefix == 'nav'">
                    &mdash; menu links only: who sees a link, not who may use what it opens
                </span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0 align-middle matrix">
                        <thead>
                            <tr>
                                <th>Permission</th>
                                <th class="text-center role-col" v-for="r in roles" :key="r.code" :title="r.label">
                                    {{ r.code }}
                                </th>
                                <th class="reset-col"></th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="p in grp.permissions" :key="p.name"
                                :class="{ 'table-warning': isDirty(p) }">
                                <td>
                                    <b>{{ p.name }}</b>
                                    <span v-if="!isDefault(p)" class="badge bg-light text-dark border ms-1"
                                        :title="'Default: ' + (p.default.join(', ') || 'no roles')">
                                        changed from default
                                    </span>
                                    <div class="text-muted small">{{ p.doc }}</div>
                                </td>
                                <td class="text-center" v-for="r in roles" :key="r.code">
                                    <input class="form-check-input" type="checkbox"
                                        :checked="formValues[p.name].includes(r.code)"
                                        :disabled="isLockoutCell(p, r)"
                                        :title="isLockoutCell(p, r)
                                            ? 'You cannot remove your own role from this permission.'
                                            : r.label"
                                        @change="toggle(p, r.code, $event.target.checked)">
                                </td>
                                <td class="text-end">
                                    <button class="btn btn-sm btn-outline-secondary" type="button"
                                        :disabled="isDefault(p, formValues[p.name]) || isLockoutDefault(p)"
                                        title="Reset to the declared default" @click="resetToDefault(p)">
                                        <i class="bi bi-arrow-counterclockwise"></i>
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div v-if="loaded && visibleGroups.length == 0" class="text-muted mb-3">
            No permission matches the filter.
        </div>

        <div class="sticky-bottom bg-white py-2 border-top">
            <button class="btn btn-outline-success me-2" type="button" :disabled="!hasChanges" @click="saveAll">
                Save Changes <i class="bi bi-save"></i>
            </button>
            <button class="btn btn-outline-danger me-2" type="button" :disabled="!hasChanges"
                @click="discardChanges">
                Discard Changes <i class="bi bi-eraser"></i>
            </button>
            <span class="text-muted small" v-if="hasChanges">{{ changed.length }} permission(s) changed</span>
        </div>
    </div>
    <div v-else class="container-fluid">
        <div class="alert alert-danger mt-3">You are not authorized to view this page.</div>
    </div>
</template>

<script>
export default {
    name: "PermissionsAdmin",
    data: function () {
        return {
            loaded: false,
            roles: [],
            permissions: [],
            managePermission: null,
            actorRole: null,
            formValues: {},
            filterText: ""
        };
    },
    computed: {
        groups() {
            const byPrefix = {};
            for (const p of this.permissions) {
                if (!byPrefix[p.prefix]) byPrefix[p.prefix] = { prefix: p.prefix, permissions: [] };
                byPrefix[p.prefix].permissions.push(p);
            }
            // Menu-only permissions last: they gate links, not actions.
            return Object.values(byPrefix).sort((a, b) =>
                (a.prefix == "nav") - (b.prefix == "nav") || a.prefix.localeCompare(b.prefix));
        },
        visibleGroups() {
            const f = this.filterText.toLowerCase();
            if (!f) return this.groups;
            return this.groups
                .map(g => ({
                    prefix: g.prefix,
                    permissions: g.permissions.filter(p =>
                        p.name.toLowerCase().includes(f) || (p.doc || "").toLowerCase().includes(f))
                }))
                .filter(g => g.permissions.length > 0);
        },
        changed() {
            return this.permissions.filter(p => this.isDirty(p));
        },
        hasChanges() {
            return this.changed.length > 0;
        }
    },
    mounted() {
        this.loadMapping();
    },
    methods: {
        loadMapping() {
            let vm = this;
            vm.doHttp(true, "permissions_describe", null,
                (body) => vm.applyDescribe(body),
                (err) => vm.setStatusMessage(err));
        },
        applyDescribe(body) {
            this.roles = body.roles;
            this.permissions = body.permissions;
            this.managePermission = body.manage_permission;
            this.actorRole = body.actor_role;
            const fv = {};
            for (const p of body.permissions) fv[p.name] = [...p.roles];
            this.formValues = fv;
            this.loaded = true;
        },
        // Role lists are sets: order carries no meaning.
        sameRoles(a, b) {
            return a.length == b.length && a.every(x => b.includes(x));
        },
        isDirty(p) {
            return !this.sameRoles(this.formValues[p.name], p.roles);
        },
        isDefault(p, roles) {
            return this.sameRoles(roles || p.roles, p.default);
        },
        isLockoutCell(p, r) {
            return p.name == this.managePermission && r.code == this.actorRole &&
                this.formValues[p.name].includes(r.code);
        },
        isLockoutDefault(p) {
            return p.name == this.managePermission && !p.default.includes(this.actorRole);
        },
        toggle(p, code, checked) {
            const current = this.formValues[p.name].filter(c => c != code);
            if (checked) current.push(code);
            // Keep the role vocabulary's order, so a saved list reads the same way as the columns.
            const order = this.roles.map(r => r.code);
            this.formValues[p.name] = current.sort((a, b) => order.indexOf(a) - order.indexOf(b));
        },
        resetToDefault(p) {
            this.formValues[p.name] = [...p.default];
        },
        saveAll() {
            let vm = this;
            const changed = vm.changed;
            if (changed.length == 0) return;
            const lines = changed.map(p => `${p.name}: ${vm.formValues[p.name].join(", ") || "(no roles)"}`);
            if (!confirm(`Save ${changed.length} changed permission(s)?\n\n${lines.join("\n")}`)) return;
            const values = {};
            for (const p of changed) values[p.name] = vm.formValues[p.name];
            vm.doHttp(false, "permissions_save", { values: values },
                (body) => {
                    vm.setStatusMessage("Saved successfully!");
                    vm.applyDescribe(body);
                },
                (err) => vm.setStatusMessage(err));
        },
        discardChanges() {
            if (!confirm("Discard all unsaved changes?")) return;
            const fv = {};
            for (const p of this.permissions) fv[p.name] = [...p.roles];
            this.formValues = fv;
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

/* Fixed widths, so every group's role columns line up down the page. */
.matrix {
    table-layout: fixed;
    min-width: 50rem;
}

.matrix .role-col {
    width: 4rem;
}

.matrix .reset-col {
    width: 3.5rem;
}
</style>
