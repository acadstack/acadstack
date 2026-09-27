<!--
Component for Creating Feedback Form.
-->
<template>
  <div class="container-fluid">
      <span class="sec-hdr">Check Grade Stats: </span>
    <div class="row mb-2">
        <div class="col">
          <div>
            <label>Select</label>
            <select class="form-select" id="grades_st" v-model="grades_status.selected">
              <option selected>--select--</option>
                <option value="GS">Grades Submitted Till Date</option>
                <option value="PG">Pending Grades</option>
            </select>
          </div>
        </div>
      <div class="col">
        <div>
          <acad-session v-bind:acad_session="grades_status.acad_session"
                label="Academic Session"
                v-on:update:acad_session='grades_status.acad_session=$event'/>
        </div>
      </div>
            <div class="col">
        <button class="btn btn-outline-success me-2 mt-3"
          @click="search" type="submit">
          <i class="bi bi-search"></i>
        </button>
        <button class="btn btn-outline-danger me-2 mt-3" @click="reset" type="reset">
          <i class="bi bi-eraser"></i>
        </button>                
      </div>         
        </div>
    <div class="card">
            <div class="card-header">
                <div class="row hdr-row">
                <div class="col-1">S#</div>
                <div class="col-md-2">Course</div>
                <div class="col-md-2">Offering Department</div>
                <div class="col-md-1">Acad Session</div>
                <div class="col-md-2">Instructor Name</div>
                 <div class="col-md-2" v-if="!isStudent">
                     <a class="btn btn-outline-success" :href="`download_grade_status/${printType}/${grades_status.acad_session}`">Download CSV</a>
                </div>
                </div>
            </div>
        <div class="card-body">
            <p v-if="gradesstatus.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(s, i) in gradesstatus" :key="s.id">
            <div class="col-1">{{ i + 1 }}</div>
            <div class="col-md-2">{{s.title}} ({{s.code}})</div>
            <div class="col-md-2">{{labelFor(SD.Departments, s.dept_name)}}</div>
            <div class="col-md-1">{{s.acad_session}}</div>
            <div class="col-md-2">{{ s.first_name }} {{s.last_name}}</div>
            </div>
        </div>
    </div>
      </div> 
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "GradesStatus",
  components: {
    "AcadSession": AcadSession
  },
  data: function () {
    return {
      grades_status: {
            grades_st: "" ,
            acad_session: "",
           },
          gradesstatus:[],
    };
  },
   computed: {
    printType() {
      return this.grades_status.selected;
    }
  },
  methods: {    
       search() {
            let vm = this;
            console.log("Searching Feedback Stats");
            vm.$http
                .post("grades.status", vm.grades_status)
                .then(function(res) {
                if (res.data.status == "OK") {
                    vm.gradesstatus = res.data.body.data;
                    if(vm.$router.currentRoute.name=='grades.status') {
                    let dd = {gradesstatus: vm.gradesstatus, grades_status: vm.grades_status};
                    sessionStorage.GenerateCourseEnrolments = JSON.stringify(dd);
                    }
                    vm.setStatusMessage("Found "+vm.gradesstatus.length+" records");
                } else {
                    vm.setStatusMessage(res.data.body);
                }
                })
                .catch(function(error) {
                console.log(error);
                vm.setStatusMessage("Error occurred when contacting the server.");
                });
            },
    getgrades_statuss() {
            let vm = this;
            return vm.$http
                .get("get_feedback_grades_statuss")
                .then(function (res) {
                if (res.data.status == "OK") {
                    vm.feedback_grades_statuss = res.data.body;
                } else {
                    vm.setStatusMessage(res.data.body);
                }
                })
                .catch(function (error) {
                console.log(error);
                vm.setStatusMessage("Error occurred when contacting the server.");
                });
    },
    reset() {
      this.grades_status = { 
            grades_st: "",
            acad_session: ""
         };
        this.gradesstatus = [];
    },
  },
};
</script>

