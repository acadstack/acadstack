<!--
Component for assigning advisors to students.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Manage batch advisors</p>
    <form @submit.prevent="findStudents">
      <div class="row mb-2">
        <div class="col-md-2">
          <label for="entryYr">Entry Year</label>
          <input id="entryYr" type="number" class="form-control"
            v-model="crit.year_of_entry" />
        </div>
        <div class="col-md-3">
          <label for="dept">Dept.</label>
          <select class="form-select" id="dept" v-model="crit.dept_name">
            <option value="">-- Any --</option>
            <option v-for="cs in SD.Departments" v-bind:value="cs.id"
              :key="cs.id">{{ cs.value }}</option>
          </select>
        </div>
        <div class="col-md-3">
          <label for="degree">Degree</label>
          <select id="degree" class="form-select" v-model="crit.degree">
            <option value="">-- Any --</option>
            <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
              {{ cs.value }}
            </option>
          </select>
        </div>
        <div class="col">
          <label for="stuName">Student name</label>
          <input id="stuName" type="text" class="form-control" v-model.trim="crit.name" />
        </div>
      </div>
      <div class="row mb-2">
        <div class="col-md-5">
          <label for="rollNos">Roll nos.</label>
          <textarea id="rollNos" class="form-control" rows="2" v-model="crit.roll_nos"
            placeholder="Separated by commas or spaces. A partial roll no. matches all that start with it."></textarea>
        </div>
        <div class="col-md-4">
          <label>Current advisor</label>
          <vue-bootstrap-typeahead :key="'f' + resetKey"
            placeholder="Type part of name"
            :data="filterAdvisors"
            :serializer="advisorLabel"
            @mta-item-selected="(c) => crit.advisor_id = c.user_id"
            @mta-input-changed="(q) => debouncedQuery(q, 'filterAdvisors')"
            />
          <div class="form-check mt-1">
            <input id="unassigned" type="checkbox" class="form-check-input" v-model="crit.unassigned" />
            <label for="unassigned" class="form-check-label">Only students without an advisor</label>
          </div>
        </div>
        <div class="col">
          <button type="submit" class="btn btn-outline-primary mt-4 me-2">Find</button>
          <button type="button" class="btn btn-outline-danger mt-4" @click="reset">Clear</button>
        </div>
      </div>
    </form>

    <div class="card" v-if="searched">
      <div class="card-header">
        <div class="row">
          <div class="col-md-3 mt-2">
            <b>{{ students.length }} students, {{ selected.length }} selected</b>
          </div>
          <div class="col-md-4">
            <vue-bootstrap-typeahead :key="'a' + resetKey"
              placeholder="Faculty to assign. Type part of name."
              :data="advisors"
              :serializer="advisorLabel"
              @mta-item-selected="(c) => advisor = c"
              @mta-input-changed="(q) => debouncedQuery(q, 'advisors')"
              />
          </div>
          <div class="col">
            <button class="btn btn-outline-primary me-2" @click="assign(advisor.user_id)"
              :disabled="!advisor.user_id || selected.length === 0">Assign to selected</button>
            <button class="btn btn-outline-danger" @click="assign(null)"
              :disabled="selected.length === 0">Remove advisor of selected</button>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="students.length === 0">No students found.</p>
        <table class="table table-sm table-striped" v-else>
          <thead>
            <tr>
              <th><input type="checkbox" class="form-check-input" title="Select all"
                :checked="selected.length === students.length" @change="selectAll($event.target.checked)" /></th>
              <th>Roll No.</th>
              <th>Name</th>
              <th>Dept.</th>
              <th>Degree</th>
              <th>Entry Year</th>
              <th>Advisor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in students" :key="s.id">
              <td><input type="checkbox" class="form-check-input" :value="s.id" v-model="selected" /></td>
              <td>{{ s.org_id }}</td>
              <td>{{ s.first_name }} {{ s.last_name }}</td>
              <td>{{ labelFor(SD.Departments, s.dept_name) }}</td>
              <td>{{ labelFor(SD.Degrees, s.degree) }}</td>
              <td>{{ s.year_of_entry }}</td>
              <td>{{ s.advisor_name || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import _ from "lodash";

function emptyCrit() {
  return {year_of_entry: "", dept_name: "", degree: "", name: "",
          roll_nos: "", advisor_id: null, unassigned: false};
}

export default {
  name: "ManageBatchAdvisors",
  components: {
    VueBootstrapTypeahead: VueBootstrapTypeahead
  },
  data: function () {
    return {
      crit: emptyCrit(),
      students: [],
      selected: [],
      searched: false,
      advisors: [],
      filterAdvisors: [],
      advisor: {},
      resetKey: 0
    };
  },
  methods: {
    advisorLabel(s) {
      return `${s.first_name} ${s.last_name} (${s.dept_name})`;
    },
    debouncedQuery: _.debounce(async function(query, target) {
      let vm = this;
      if (_.isEmpty(query) || query.length < 3) {
        // Typing over a picked advisor drops the filter
        if (target === "filterAdvisors") vm.crit.advisor_id = null;
        return;
      }
      await vm.doHttp(true, `instructor_lookup/${query}`, null,
        (b)=>{vm[target] = b}, vm.setStatusMessage)
    }, 400),
    selectAll(checked) {
      this.selected = checked ? this.students.map(s => s.id) : [];
    },
    async findStudents() {
      let vm = this;
      await vm.doHttp(false, "find_advisor", vm.crit,
        (b)=>{
          vm.students = b;
          vm.selected = [];
          vm.searched = true;
        }, vm.setStatusMessage)
    },
    async assign(userId) {
      let vm = this;
      if (!confirm("Confirm action?")) {
        vm.setStatusMessage("User canceled action!");
        return;
      }
      await vm.doHttp(false, "assign_advisor",
        {student_ids: vm.selected, user_id: userId},
        async (msg)=>{
          // Show the outcome in the list
          await vm.findStudents();
          vm.setStatusMessage(msg);
        }, vm.setStatusMessage)
    },
    reset() {
      this.crit = emptyCrit();
      this.students = [];
      this.selected = [];
      this.searched = false;
      this.advisor = {};
      this.resetKey++;
    },
  },
};
</script>
