<!--
Roles and the permissions granted to each.
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">Roles and permissions</div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-3">
            <div class="list-group mb-3">
              <a href="#" class="list-group-item list-group-item-action" v-for="r in roles" :key="r.code"
                :class="{ active: r.code == role.code && !isNew }" @click.prevent="select(r)">
                {{ r.label }} <small>({{ r.code }})</small>
              </a>
            </div>
            <button type="button" class="btn btn-outline-primary" @click="newRole">New role</button>
          </div>
          <div class="col">
            <div class="row mb-2">
              <div class="col-md-3">
                <label for="roleCode">Code</label>
                <input id="roleCode" type="text" class="form-control" maxlength="4" :disabled="!isNew"
                  v-model.trim="role.code" />
              </div>
              <div class="col-md-5">
                <label for="roleLabel">Label</label>
                <input id="roleLabel" type="text" class="form-control" v-model.trim="role.label" />
              </div>
              <div class="col-md-4 pt-4">
                <button type="button" class="btn btn-outline-success" @click="save">
                  Save <i class="bi bi-save"></i>
                </button>
              </div>
            </div>
            <div class="form-check" v-for="p in permissions" :key="p.code">
              <input class="form-check-input" type="checkbox" :id="'p_' + p.code" :value="p.code"
                v-model="role.permissions" />
              <label class="form-check-label" :for="'p_' + p.code">
                <b>{{ p.code }}</b>
                <small class="text-muted ms-2">{{ p.description }}</small>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "RolePermissions",
  data: function () {
    return {
      roles: [],
      permissions: [],
      grants: {},
      isNew: false,
      role: { code: "", label: "", permissions: [] },
    };
  },
  mounted: function () {
    this.load();
  },
  methods: {
    apply(body) {
      this.roles = body.roles;
      this.permissions = body.permissions;
      this.grants = body.grants;
      const current = this.roles.find(r => r.code == this.role.code);
      this.select(current || this.roles[0]);
    },
    load() {
      return this.doHttp(true, "perms", null, this.apply, this.setStatusMessage);
    },
    select(r) {
      this.isNew = false;
      this.role = { code: r.code, label: r.label, permissions: [...(this.grants[r.code] || [])] };
    },
    newRole() {
      this.isNew = true;
      this.role = { code: "", label: "", permissions: [] };
    },
    async save() {
      const r = this.role;
      await this.doHttp(false, "perms_save", { role: r.code, label: r.label, permissions: r.permissions },
        async (body) => {
          this.apply(body);
          this.setStatusMessage("Saved.");
          // UserRoles in the static data lists the roles.
          await this.doHttp(true, "get_static_data", null, this.setStaticData, this.setStatusMessage);
        }, this.setStatusMessage);
    },
  },
};
</script>
