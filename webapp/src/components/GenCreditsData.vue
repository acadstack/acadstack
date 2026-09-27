<!--
Component for triggering the generation of students credits related
data in an academic session.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h5>Generate Students' Credits Data</h5>
    <div class="row mb-2">
        <div class="col-md-8">
            <acad-session v-bind:acad_session="acad_session" 
                  v-on:update:acad_session='acad_session=$event'/>
        </div>
        <div class="col-md-4">
            <div class="mt-2">
                <button class="btn btn-outline-success me-2" @click="submit_request" type="submit">
                    <i class="bi bi-search"></i>
                </button>
                <button class="btn btn-outline-danger" @click="reset" type="reset">
                    <i class="bi bi-eraser"></i>
                </button>
            </div>
        </div>
    </div>
    <p>
        {{results.message}}
    </p>
    <div v-if="results.job_key != ''">
        <button class="btn btn-outline-primary mb-2" @click="check_status">Check Status</button>
        <div v-if="job_status.status != undefined">
            <p>
                Status: {{job_status.status}}<br/>
                Status message: {{job_status.result}}
            </p>
        </div>
    </div>
  </div>
  
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "GenCreditsData",
  components: {
    "AcadSession": AcadSession
  },
  data: function(){
      return{
          acad_session:"",
          results: {job_key: "", message: ""},
          job_status: {}
      }
  },
  methods: {
    submit_request(){
        let vm = this;
        vm.job_status = {}
        vm.$http
        .get("gen_students_credits/"+vm.acad_session)
        .then(function(res) {
                vm.results = res.data.body;
            }
        ).catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when submitting job.");
        });
    },
    check_status(){
        let vm = this;
        vm.job_status = {};
        vm.$http
        .get("job_status/"+vm.results.job_key)
        .then(function(res) {
                vm.job_status = res.data.body;
            }
        ).catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when checking job status.");
        });
    },
    reset(){
        this.acad_session = "";
        this.results = {job_key: "", message: ""};
        this.job_status = {};
    }
  },
};
</script>