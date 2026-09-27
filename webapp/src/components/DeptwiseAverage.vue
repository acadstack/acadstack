<!--
Component for Creating Dept wise average .
-->
<template>
  <div class="container-fluid">
      <span class="sec-hdr"> Dept wise average scores for the questions: </span>
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
                <div class="col-md-2">Dept Name</div>
                <div class="col-md-1">Acad Session</div>
                <div class="col-md-4">Question</div>
                <div class="col-md-2">Avg Score</div>
                 <div class="col-md-2" v-if="!isStudent">
                     <a class="btn btn-outline-success" :href="`download_dept_wise_avg/${form.form_type}/${form.acad_session}`">Download CSV</a>
                </div>
                </div>
            </div>
        <div class="card-body">
            <p v-if="deptwiseavg.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(s, i) in deptwiseavg" :key="s.id">
            <div class="col-1">{{ i + 1 }}</div>
            <div class="col-md-2">{{labelFor(SD.Departments, s.dept_name)}}</div>
            <div class="col-md-1">{{s.acad_session}}</div>    
            <div class="col-md-4">{{s.question}}</div>
            <div class="col-md-2">{{s.avg_score}}</div>
           
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
          deptwiseavg:[],        
    };
  },
  methods: {    
       search() {
            let vm = this;
            console.log("Searching Feedback Stats");
            vm.$http
                .post("dept.wiseavg", vm.form)
                .then(function(res) {
                if (res.data.status == "OK") {
                    vm.deptwiseavg = res.data.body.data;
                    if(vm.$router.currentRoute.name=='dept.wiseavg') {
                    let dd = {deptwiseavg: vm.deptwiseavg, form: vm.form};
                    sessionStorage.GenerateCourseEnrolments = JSON.stringify(dd);
                    }
                    vm.setStatusMessage("Found "+vm.deptwiseavg.length+" records");
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
        this.deptwiseavg = [];
    },
  },
};
</script>

