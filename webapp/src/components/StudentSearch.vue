<template>
  <div class="container-fluid">
    <p class="h6">Find Students</p>
    <form @submit.prevent="find">
      <div class="row mb-2">
        <div class="col-md-2">
          <div>
            <label for="st_org_id">Roll No.</label>
            <input type="text" class="form-control" id="st_org_id" v-model="student.org_id"/>
          </div>
          <div v-if="isPlacement">
            <label for="st_email">Session</label>
            <input type="text" class="form-control" id="st_year" v-model="student.acad_session"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="st_firstnm">First Name</label>
            <input type="text" class="form-control" id="st_firstnm" v-model="student.first_name"/>
          </div>
           <div v-if="isPlacement" class="col">
          <div>
            <label for="st_email">Year</label>
            <input type="text" class="form-control" id="st_year" v-model="student.year_of_entry"/>
          </div>
        </div>
        </div>
        <div class="col">
          <div>
            <label for="st_lastnm">Last Name</label>
            <input type="text" class="form-control" id="st_lastnm" v-model="student.last_name"/>
          </div>
        </div>
        <div class="col">
          <label for="deg">Degree</label>
          <select id="deg" class="form-select" v-model.trim="student.degree">
            <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
              {{ cs.value }}
            </option>
          </select>
        </div>
        <div class="col">
          <div>
            <label for="st_email">Email</label>
            <input type="email" class="form-control" id="st_email" v-model="student.email"/>
          </div>
        </div>
       
         <div v-if="isPlacement" class="col">
          <div>
            <label for="st_email">Department</label>
             <select id="dept" class="form-select" v-model.trim="student.dept_name">
            <option v-for="cs in SD.Departments" v-bind:value="cs.id" :key="cs.id">
              {{ cs.value }}
            </option>
          </select>
          </div>
           <div v-if="isPlacement" class="col">
        </div>
        </div>
        <div class="col-md-2">
          <div class="mt-4">
             <a v-if="isPlacement" style="margin-left:10px; margin-right:10px" class="btn btn-outline-success" :href="`download_students_list/${student.degree}/${student.year_of_entry}/${student.dept_name}/${student.acad_session}`">Download</a>
            <button class="btn btn-outline-success me-2" type="submit"><i class="bi bi-search"></i></button>
            <button class="btn btn-outline-danger" @click="reset" type="reset"><i class="bi bi-eraser"></i></button>
          </div>
        </div>
      </div>
    </form>
    
    <div class="card">
      <div class="card-header">Results</div>
     
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col">Name</div>
          <div class="col">Roll No.</div>
          <div class="col">Dept.</div>
          <div class="col">Degree</div>
        </div>
        <p v-if="results.length == 0">Nothing to show yet!</p>
        <div class="row row-striped mb-2" v-for="(r, i) in results" :key="r.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col"><a :href="'#/user.detail/'+r.id">{{r.first_name}} {{r.last_name}}</a></div>
          <div class="col">{{r.org_id}}</div>
          <div class="col">{{labelFor(SD.Departments, r.dept_name)}}</div>
          <div class="col">{{labelFor(SD.Degrees, r.degree)}}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import _ from "lodash";
export default {
  name: "StudentSearch",

  data: function() {
    return { results: [], student: {} };
  },
  mounted: function() {
    console.log("Mounted StudentSearch");
    if (sessionStorage.student_search_crit){
      this.student = JSON.parse(sessionStorage.student_search_crit);
    }
    if (sessionStorage.student_search_res) {
      this.results = JSON.parse(sessionStorage.student_search_res);
    }
  },
  methods: {
    find() {
      let vm = this;
      if (_.isEmpty(vm.student) ||
          (
            _.isEmpty(vm.student.org_id) &&
            _.isEmpty(vm.student.email) &&
            _.isEmpty(vm.student.first_name) &&
            _.isEmpty(vm.student.last_name) &&
            _.isEmpty(vm.student.degree) 
          )
        ) {
        vm.setStatusMessage("Please specify at least one search condition!");
        return;
      }
      sessionStorage.student_search_crit = JSON.stringify(vm.student);
      vm.results = [];
      vm.$http
        .post("students_find", vm.student)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.results = res.data.body;
            sessionStorage.student_search_res = JSON.stringify(vm.results);
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when searching students.");
        });
    },
    reset() {
      this.results = [];
      this.student = {};
      sessionStorage.student_search_res = undefined;
      sessionStorage.student_search_crit = undefined;
    }
  }
};
</script>
