<!--
Component for Doctoral committee

@author Balwinder Sodhi

-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">
        <div class="row mb-2">
          <div class="col-md-4">
            <span class="float-start">Doctoral committee for student:</span>
          </div>
          <div class="col">
            <PersonLookupField class="float-start" personRole="STU" :person="doc_comm.student" 
                v-if="loaded||!isEdit" v-on:personSelected="onStudentSelect" 
                :isView="doc_comm.student.user_id > 0"
                :disabled="viewOnly"
                placeholder="Lookup by Roll No."/>
          </div>
          <div class="col-md-3" v-if="!(isStudent || viewOnly)">
            <div class="dropdown me-2 float-end">
              <button
                type="button"
                class="btn btn-primary dropdown-toggle"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                Action
              </button>
              <div class="dropdown-menu">
                <a
                  class="dropdown-item"
                  @click.prevent="onAction(act)"
                  v-for="act in actions"
                  :key="act"
                  >{{ act.label }}</a
                >
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="row mb-2">
          <div class="col-md-2">
            <label for="fromDt">From:</label>
            <input
              id="fromDt" :disabled="viewOnly"
              class="form-control"
              type="date"
              v-model="doc_comm.effective_from"
            />
          </div>
          <div class="col-md-2">
            <label for="toDt">To:</label>
            <input
              id="toDt" :disabled="viewOnly"
              class="form-control"
              type="date"
              v-model="doc_comm.effective_to"
            />
          </div>
          <div class="col-md-3">
            <label for="status">Status:</label>
            <span class="form-control">{{labelFor(SD.DcStatuses, doc_comm.status)}}</span>
          </div>
          <div class="col-md-5">
            <label for="rem">Remarks:</label>
            <textarea
              id="rem" :disabled="viewOnly"
              class="form-control"
              v-model="doc_comm.remarks"
            />
          </div>
        </div>
        <div class="mt-2 mb-2">
          <span class="fw-bolder me-2">DC Members</span>
          <span class="float-end" v-if="!viewOnly">
            <button
                type="button"
                @click="addMember(false)"
                :disabled="viewOnly"
                class="btn btn-sm btn-outline-primary me-2"
              >
              Add Member
            </button>
            <button
                type="button"
                @click="addMember(true)"
                :disabled="viewOnly"
                class="btn btn-sm btn-outline-primary"
              >
              Add External Member
            </button>
          </span>
        </div>
        <div class="row bg-secondary fw-bold mb-2">
          <div class="col-md-3">Role</div>
          <div class="col-md-4">Name</div>
          <div class="col-md-3">Expertise area</div>
          <div class="col-md-2">Delete</div>
        </div>
        <p v-if="doc_comm.members.length == 0">No DC members added yet!</p>
        <div class="row mb-2" v-for="r in doc_comm.members" :key="r.id">
          <div class="col-md-3">
            <select
              class="form-select"
              v-model.trim="r.role"
              :disabled="viewOnly"
              @change.prevent="roleExists"
            >
              <option v-for="cs in SD.DcRoles" v-bind:value="cs.id" :key="cs.id">
                {{ cs.value }}
              </option>
            </select>
          </div>
          <div class="col-md-4">
            <PersonLookupField personRole="FAC" :person="r"
              v-on:personSelected="onMemberSelect($event, r.id)"
              :disabled="viewOnly" :isView="r.id > 0" 
              v-if="!r.is_external" placeholder="Lookup by name"/>
            <div class="input-group" v-else>
              <span class="input-group-text">Name and contact</span>
              <input type="text" aria-label="Name" class="form-control" 
                v-model="r.ext_name" placeholder="Name" :disabled="viewOnly">
              <input type="text" aria-label="Contact" class="form-control" 
                v-model="r.ext_contact" placeholder="Contact info" :disabled="viewOnly">
            </div>
          </div>
          <div class="col-md-3">
            <input
              :disabled="viewOnly"
              type="text"
              class="form-control"
              v-model="r.expertise"
            />
          </div>
          <div class="col-md-2">
            <input
              :disabled="viewOnly"
              type="checkbox"
              class="form-check-input"
              v-model="r.is_deleted"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PersonLookupField from "./PersonLookupField.vue";

export default {
  name: "DcDetails",
  components: {
    PersonLookupField: PersonLookupField
  },
  data: function () {
    return {
      loaded: false,
      doc_comm: this.initDc(),
      /**
       * Status-changing moves the user may make on this DC, from the
       * server's "dc" workflow table (see api_service/domain/dc.py).
       */
      actions: [],
    };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called: stu_id=" + this.$route.params.stu_id);
      return this.$route.params.stu_id > 0;
    },
  },
  async created() {
    console.log("Creating DcFormulation");
    let vm = this;
    if (vm.isEdit) {
      await vm.load();
    } else {
      vm.reset();
      await vm.markViewOnly();
    }
  },
  methods: {
    initDc() {
      return {
        student: {},
        members: [],
        status: "DRA",
        effective_from: "",
        effective_to: "",
        remarks: "",
      };
    },
    roleExists() {
      let vm = this;
      let uniq = {}
      for (let i = 0; i < vm.doc_comm.members.length; i++) {
        const x = vm.doc_comm.members[i];
        let item = uniq[`${x.role}-${x.id}-${x.is_external}`];
        if (item == undefined) {
          item = 0;
        }
        if (++item > 1) {
          vm.setStatusMessage("Cannot have same DC member in two roles!")
          return
        }
      }
    },
    async markViewOnly() {
      // The DC is editable when the workflow offers this user any move
      // from its current status, including saving it where it is.
      let vm = this;
      await vm.doHttp(true, `workflow_actions/dc/${vm.doc_comm.id || 0}`, null,
        (b)=>{
          vm.actions = b.filter((a) => a.changes_status);
          vm.viewOnly = vm.isEdit && b.length == 0;
          console.log("ViewOnly=" + vm.viewOnly);
        }, vm.setStatusMessage);
    },
    onMemberSelect(c, id) {
      console.log("Added DC member: " + JSON.stringify(c));
      let m = this.doc_comm.members.find((el) => el.id == id);
      if (m != undefined) {
        Object.assign(m, c);
      } else {
        console.error("Member not found!")
      }
    },
    onStudentSelect(c) {
      console.log("Selected student: " + JSON.stringify(c));
      this.doc_comm.student = c;
    },
    isDcValid() {
      // TODO:
      return true;
    },
    async load() {
      let vm = this;
      vm.loaded = false;
      let stu_id = vm.$route.params.stu_id;
      await vm.doHttp(true, `dc_view/${stu_id}`, null,
        (b)=>{
          vm.doc_comm = b; vm.loaded = true;
          vm.markViewOnly();
        }, vm.setStatusMessage);
    },
    async save() {
      let vm = this;
      //TODO: Check status and role before allowing save
      if (!vm.isDcValid()) {
        vm.setStatusMessage("Please supply valid DC details.");
      } else {
        if (!confirm("Confirm save?")) {
          return;
        }
        console.log("Saving DC details.");
        await vm.doHttp(false, "dc_save", vm.doc_comm,
          (b)=>{
            vm.doc_comm = b;
            if (!vm.isEdit){
              const v = `${vm.$route.path}/${vm.doc_comm.id}`;
              vm.$router.push({ path: v });
            }
            vm.setStatusMessage("DC saved successfully!");
            vm.markViewOnly();
          }, vm.setStatusMessage);
      }
    },
    reset() {
      this.initDc();
      console.log("Clearing DC details .");
    },
    onAction(act) {
      let vm = this;
      console.log("Changing DC status to: " + act.to_status);
      vm.doc_comm.status = act.to_status;
      vm.save();
    },
    addMember(isExternal) {
      let vm = this;
      if (vm.doc_comm.members == undefined) vm.doc_comm.members = [];
      vm.doc_comm.members.push({ id: -vm.doc_comm.members.length, 
      role: "", is_external: isExternal });
    },
  },
};
</script>
