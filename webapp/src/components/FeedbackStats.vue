<!--
Component for Creating Feedback Form.
-->
<template>
  <div class="container-fluid">
      <span class="sec-hdr">Generate Feedback Stats: </span>
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
                <div class="col-md-1">Stud. Enrolled</div>
                <div class="col-md-1">Stud. Voted</div>
                <div class="col-md-1">Perc. Voting</div>
                <div class="col-md-2">Course Name</div>
                <div class="col-md-1">L-T-P-S-C</div>
                <div class="col-md-1">Offering Department</div>
                <div class="col-md-1">Acad Session</div>
                <div class="col-md-2">instructor Name</div>
                 <div class="col-md-1" v-if="!isStudent">
                     <a class="btn btn-outline-success" :href="`download_feedback_stats/${form.form_type}/${form.acad_session}`">Download CSV</a>
                </div>
                </div>
            </div>
        <div class="card-body">
            <p v-if="feedbackstats.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(s, i) in feedbackstats" :key="s.id">
            <div class="col-1">{{ i + 1 }}</div>
            <div class="col-md-1">{{s.students_enrolled}}</div>
            <div class="col-md-1">{{s.no_of_students_voted}}</div>
            <div class="col-md-1">{{s.pct_students_voted}}</div>
            <div class="col-md-2">{{s.title}} ({{s.code}})</div>
            <div class="col-md-1">{{s.ltp}}</div>
            <div class="col-md-1">{{labelFor(SD.Departments, s.offering_department)}}</div>
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
  name: "FeedbackStats",
  components: {
    "AcadSession": AcadSession
  },
  data: function () {
    return {
      form: {
            form_type: "" ,
            acad_session: "",
           },
          feedbackstats:[],        
    };
  },
  methods: {    
       search() {
            let vm = this;
            console.log("Searching Feedback Stats");
            vm.$http
                .post("feedback.stats", vm.form)
                .then(function(res) {
                if (res.data.status == "OK") {
                    vm.feedbackstats = res.data.body.data;
                    if(vm.$router.currentRoute.name=='feedback.stats') {
                    let dd = {feedbackstats: vm.feedbackstats, form: vm.form};
                    sessionStorage.GenerateCourseEnrolments = JSON.stringify(dd);
                    }
                    vm.setStatusMessage("Found "+vm.feedbackstats.length+" records");
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
        this.feedbackstats = [];
    },
  },
};
</script>

