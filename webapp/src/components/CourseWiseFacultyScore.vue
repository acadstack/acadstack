<!--
Component for Creating  Course-wise faculty scores.
-->
<template>
  <div class="container-fluid">
      <span class="sec-hdr">  Course wise faculty scores for the question: </span>
    <div class="row mb-2">
        <div class="col">
                <label for="frm_typ">Form Type</label>
                <select class="form-select" id="frm_typ" 
                    v-model.trim="form.form_type">
                    <option
                        v-for="cs in SD.FormTypes"
                        v-bind:value="cs.id"
                        :key="cs.id"
                    >{{ cs.value }}</option>
                    </select>
            </div>
      <div class="col">
        <div>
          <acad-session v-bind:acad_session="form.acad_session"
                label="Academic Session"
                v-on:update:acad_session='form.acad_session=$event'/>
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
                <div class="col-md-2">Instructor Name</div>
                <div class="col-md-1">Acad Session</div>    
                <div class="col-md-1">Course Code</div>
                <div class="col-md-2">Department Name</div>
                <div class="col-md-1">Faculty Score</div>
                <div class="col-md-1">Total Votes</div>
                 <div class="col-md-2" v-if="!isStudent">
                     <a class="btn btn-outline-success" :href="`download_course_wise_faculty_score/${form.form_type}/${form.acad_session}`">Download CSV</a>
                </div>
                </div>
            </div>
        <div class="card-body">
            <p v-if="coursewisefacscore.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(s, i) in coursewisefacscore" :key="s.id">
            <div class="col-1">{{ i + 1 }}</div>
            <div class="col-md-2">{{s.first_name}} {{s.last_name}}</div>
            <div class="col-md-1">{{s.acad_session}}</div>
            <div class="col-md-1">{{s.course_code}}</div>  
            <div class="col-md-2">{{labelFor(SD.Departments, s.dept_name)}}</div>  
            <div class="col-md-1">{{s.faculty_score}}</div>
            <div class="col-md-1">{{s.total_votes}}</div>
           
            </div>
        </div>
    </div>
      </div> 
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "CourseWiseFacultyScore",
  components: {
    "AcadSession": AcadSession
  },
  data: function () {
    return {
      form: {
            form_type: "" ,
            acad_session: "",
            },
          coursewisefacscore:[],        
    };
  },
  methods: {    
       search() {
            let vm = this;
            console.log("Searching Course wise Faculty Score");
            vm.$http
                .post("coursewise.facultyscore", vm.form)
                .then(function(res) {
                if (res.data.status == "OK") {
                    vm.coursewisefacscore = res.data.body.data;
                    if(vm.$router.currentRoute.name=='coursewise.facultyscore') {
                    let dd = {coursewisefacscore: vm.coursewisefacscore, form: vm.form};
                    sessionStorage.GenerateCourseEnrolments = JSON.stringify(dd);
                    }
                    vm.setStatusMessage("Found "+vm.coursewisefacscore.length+" records");
                } else {
                    vm.setStatusMessage(res.data.body);
                }
                })
                .catch(function(error) {
                console.log(error);
                vm.setStatusMessage("Error occurred when contacting the server.");
                });
            },
    getForms() {
            let vm = this;
            return vm.$http
                .get("get_feedback_forms")
                .then(function (res) {
                if (res.data.status == "OK") {
                    vm.feedback_forms = res.data.body;
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
      this.form = { 
            form_type: "",
            acad_session: ""
         };
        this.coursewisefacscore = [];
    },
  },
};
</script>

