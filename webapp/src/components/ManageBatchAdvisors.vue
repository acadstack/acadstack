<!--
Component for managing batch advisors.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Manage batch advisors</p>
    <div class="row mb-2">
      <div class="col">
        <div>
          <label for="entryYr">Entry Year</label>
          <input id="entryYr" type="number" class="form-control" min="2012"
            max="2099" v-model="search_crit.for_entry_year"
            required
          />
        </div>
      </div>
      <div class="col">
        <div>
          <label for="dept">Dept.</label>
          <select class="form-select" id="dept" required
                v-model="search_crit.dept_name">
            <option v-for="cs in SD.Departments" v-bind:value="cs.id"
              :key="cs.id">{{ cs.value }}</option>
          </select>
        </div>
      </div>
      <div class="col">
        <div>
          <label for="degree">Degree</label>
          <select id="degree" class="form-select" required 
            v-model.trim="search_crit.for_degree">
              <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
                {{ cs.value }}
              </option>
          </select>
        </div>
      </div>
      <div class="col-md-3">
        <button class="btn btn-outline-primary mt-2 me-2" @click="findAdvisor">Find</button>
        <button class="btn btn-outline-danger mt-2" @click="reset">Clear</button>
      </div>
    </div>
    <div class="row mb-2" v-if="searched">
      <div class="col-md-6">
        {{advisorInfo}}
      </div>
      <div class="col-md-4">
        <vue-bootstrap-typeahead
          placeholder="Find faculty to assign. Type part of name."
          :data="advisors"
          :serializer="s => (s.first_name + ' ' +s.last_name + ' ('+ s.dept_name+')')"
          @mta-item-selected="onUserSelect"
          @mta-input-changed="debouncedQuery"
          />
      </div>
      <div class="col">
        <button :disabled="!lookedup" class="btn btn-outline-primary" @click="assignAdvisor">Assign</button>
      </div>
    </div>
    
  </div>
</template>

<script>
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import _ from "lodash";

export default {
  name: "ManageBatchAdvisors",
  components: {
    VueBootstrapTypeahead: VueBootstrapTypeahead
  },
  data: function () {
    return {
      search_crit: {for_entry_year: "", dept_name: "", 
                    for_degree: "", user_id: "0"},
      advisors: [],
      searched: false,
      advisor: {},
      lookedup: false
    };
  },
  created: function() {
    console.log("Creating ManageBatchAdvisors");
    this.reset();
  },
  computed: {
    advisorInfo() {
      let vm = this;
      if (vm.advisor.user_id < 0) {
        return vm.advisor.message;
      } else {
        return `Assigned: ${vm.advisor.first_name} ${vm.advisor.last_name} of ${vm.labelFor(vm.SD.Departments, vm.advisor.dept_name)}`
      }
    }
  },
  methods: {
    onUserSelect(c) {
      console.log("Selected user: " + JSON.stringify(c));
      this.advisor = c;
      this.lookedup = true;
    },
    debouncedQuery: _.debounce(async function(inp) {
      await this.lookupUser(inp)
    }, 400),
    async lookupUser(query) {
      let vm = this;
      console.log("Looking up user: "+query);
      if (_.isEmpty(query) || query.length < 3) {
        console.log("Min. 3 charaters needed. Ignored.");
        return;
      }
      await vm.doHttp(true, `instructor_lookup/${query}`, null,
        (b)=>{vm.advisors = b}, vm.setStatusMessage)
    },
    async assignAdvisor() {
      let vm = this;
      if (!confirm("Confirm action?")) {
        vm.setStatusMessage("User canceled action!");
        return;
      }
      vm.search_crit["user_id"] = vm.advisor.user_id;
      await vm.doHttp(false, "assign_advisor", vm.search_crit,
        ()=>{vm.reset()}, vm.setStatusMessage)      
    },
    async findAdvisor() {
      let vm = this;
      if(vm.search_crit.for_entry_year === '' || vm.search_crit.dept_name === ''  || vm.search_crit.for_degree === '') {
        vm.setStatusMessage("Please specify all search fields!");
        return
      }
      vm.doHttp(false, "find_advisor", vm.search_crit,
        (b)=>{
          vm.advisor = b;
          vm.searched = true;
        }, vm.setStatusMessage)
    },
    reset() {
      this.search_crit = {for_entry_year: "", dept_name: "", 
                          for_degree: "", user_id: "0"};
      this.advisors = [];
      this.advisor = {};
      this.searched = false;
      this.lookedup = false;
    },
  },
};
</script>
