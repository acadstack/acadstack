<!--
Component for Doctoral committee

@author Balwinder Sodhi

-->
<template>
  <div class="container-fluid">
    <h4>Search Doctoral Committee</h4>
    <div class="row mb-2">
      <div class="col-md-3">
        <label for="dcs">DC Status</label>
        <select id="dcs"
          class="form-select"
          v-model.trim="sc.status"
        >
          <option v-for="cs in SD.DcStatuses" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col">
        <label for="dept">Dept.</label>
        <select id="dept" class="form-select" v-model.trim="sc.dept_name">
          <option
            v-for="cs in SD.Departments"
            v-bind:value="cs.id"
            :key="cs.id"
          >
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col-md-2">
        <label for="ent_yr">Entry Year</label>
        <input
          id="ent_yr"
          class="form-control"
          type="number"
          min="2010"
          max="2099"
          v-model.trim="sc.entry_year"
          placeholder="YYYY (e.g., 2019)"
        />
      </div>
    </div>
    <div class="row mb-2">
      <div class="col-md-3">
        <div>
          <label for="crs_code">Student:</label>
          <PersonLookupField personRole="STU" 
          v-on:personSelected="onStudentSelect"
          placeholder="Lookup by Roll No." :reset="resetStdLookup"/>
        </div>
      </div>
      <div class="col-md-3">
        <div>
          <label for="mem">Member</label>
          <PersonLookupField personRole="FAC" 
          v-on:personSelected="onMemberSelect"
          placeholder="Lookup by name" :reset="resetMemLookup"/>
        </div>
      </div>
      <div class="col-md-3">
        <label for="mrole">Member Role</label>
        <select class="form-select" v-model.trim="sc.member_role">
          <option v-for="cs in SD.DcRoles" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col-md-3">
        <span class="float-end mt-2">
          <button type="button" class="btn btn-outline-primary me-2" @click="search">Find</button>
          <button type="button" class="btn btn-outline-danger" @click="reset">Clear</button>
        </span>
      </div>
    </div>

    <div class="card mb-4 mt-2">
      <div class="card-header">DCs found</div>
      <div class="card-body">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-5">Committe</div>
          <div class="col-md-2">Period</div>
          <div class="col-md-2">Status</div>
          <div class="col-md-2">Remarks</div>
        </div>
        <p v-if="dcs.length == 0">No DC found yet!</p>
        <div class="row mb-2" v-for="(r, idx) in dcs" :key="r.id">
          <div class="col-md-1">{{ idx + 1 }}</div>
          <div class="col-md-5">
            Student:<a :href="'#/user.detail/'+r.student.user_id">
            {{ r.student.first_name }} {{ r.student.last_name
            }} ({{ r.student.org_id
            }}).</a> <br />
            Members:
            <ol>
              <li v-for="m in r.members" :key="m.id">
                <span v-if="m.is_external">
                  {{m.ext_name}}, {{m.ext_contact}}
                  <span class="badge rounded-pill bg-danger">
                   External {{ labelFor(SD.DcRoles, m.role) }}</span>
                </span>
                <span v-else>
                {{ m.first_name }} {{ m.last_name }},
                {{ labelFor(SD.Departments, m.dept_name) }} 
                <span class="badge rounded-pill" 
                  :class="{'bg-warning':m.role=='ME','bg-success':['SU','CO'].includes(m.role), 'bg-primary':m.role=='CP'}">
                  {{ labelFor(SD.DcRoles, m.role) }}</span>
                </span>
              </li>
            </ol>
          </div>
          <div class="col-md-2">
            {{ r.effective_from }} to {{ r.effective_to }}
          </div>
          <div class="col-md-2">
            <a :href="'#/dc.form/'+r.id">
            {{ labelFor(SD.DcStatuses, r.status) }}</a>
          </div>
          <div class="col-md-2">
            {{ r.remarks }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PersonLookupField from "./PersonLookupField.vue";

export default {
  name: "DcSearch",
  components: {
    PersonLookupField: PersonLookupField
  },
  data: function () {
    return {
      resetStdLookup: false,
      resetMemLookup: false,
      sc: {},
      dcs: [],
    };
  },
  async created() {
    console.log("Creating DcSearch");
  },
  async mounted() {
    if (sessionStorage.dcSrchRes != undefined) {
      this.dcs = JSON.parse(sessionStorage.dcSrchRes);
    }
    if (sessionStorage.dcSrchCrit != undefined) {
      this.sc = JSON.parse(sessionStorage.dcSrchCrit);
    }
  },
  methods: {
    showDc(stu_id) {
      this.$router.push({ name: 'dc.form', params: { stu_id } })
    },
    onStudentSelect(c) {
      this.sc.student_id = c.user_id;
      this.studentLookupQry = "";
    },
    onMemberSelect(c) {
      this.sc.member_id = c.user_id;
      this.memberLookupQry = "";
    },
    async search() {
      let vm = this;
      if (vm.sc == {}) {
        vm.setStatusMessage("Please supply valid search criteria.");
      } else {
        await vm.doHttp(false, "dc_find", vm.sc,
          (b)=>{
            vm.dcs = b;
            sessionStorage.dcSrchRes = JSON.stringify(vm.dcs);
            sessionStorage.dcSrchCrit = JSON.stringify(vm.sc);
          }, vm.setStatusMessage);
      }
    },
    reset() {
      this.sc = {};
      this.dcs = [];
      this.resetStdLookup = !this.resetStdLookup;
      this.resetMemLookup = !this.resetMemLookup;
      sessionStorage.dcSrchRes = undefined;
      sessionStorage.dcSrchCrit = undefined;
    },
  },
};
</script>
