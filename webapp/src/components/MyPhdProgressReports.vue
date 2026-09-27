<!--
Component for PhD progress reports

@author Balwinder Sodhi

-->
<template>
  <div class="container-fluid">
    <div class="row border-bottom border-info pb-2">
      <div class="col-md-6">
        <span class="float-start h4">Progress reports</span>
      </div>
      <div v-if="!isStudent" class="col-md-6 float-end">
        <my-dc-students v-on:student-selected="onStudentSelect" label="For student:" />
      </div>
    </div>
    <div class="mt-2">
      <div class="card mb-2" v-for="(r, idx) in reports" :key="r">
        <div class="card-header">
          <span class="me-2"><b>{{idx+1}}. </b></span>
          <span class="me-2"><b>DC member:</b> {{r.member}}</span>
          <span class="me-2"><b>Status: </b> {{labelFor(SD.PPRStatuses, r.status)}} <b>As on</b> {{r.upd_ts}}</span>
          <span class="me-2"><b>Academic session: </b> {{r.acad_session}}</span>
          <span :class="{'badge bg-danger': !r.is_satisfactory, 'badge bg-success': r.is_satisfactory}">{{r.is_satisfactory ? "Satisfactory" : "Unsatisfactory"}}</span>
          <span class="ms-2" v-if="!isStudent">[<a :href="'#/ppr/'+r.id">Edit</a>]</span>
        </div>
        <div class="card-body">
          <p class="card-text">{{r.note}}</p>
        </div>
      </div>
      <p class="text-center mt-2" v-if="reports.length == 0" >Nothing to show yet!</p>
    </div>
  </div>
</template>

<script>
import MyDcStudents from "./MyDcStudents.vue";
export default {
  name: "MyPhdProgressReports",
  components: {
    MyDcStudents: MyDcStudents
  },
  data: function () {
    return {
      reports: []
    };
  },
  computed: {
    actions() {
      return this.actionsMap[this.userRole];
    }
  },
  async mounted() {
    console.log("Mounted MyPhdProgressReports");
    if (this.isStudent) {
      await this.loadStudentReports(this.currentUser.id)
    }
    this.viewOnly = false;
  },
  methods: {
    async onStudentSelect(c) {
      console.log("Selected student: " + JSON.stringify(c));
      if (c != undefined && c > 0) {
        await this.loadStudentReports(c)
      }
    },
    async loadStudentReports(stdId) {
      console.debug("Loading reports for student: "+stdId);
      let vm = this;
      await vm.doHttp(true, `student_pprs/${stdId}`, null,
          (body)=>{vm.reports = body;}, vm.setStatusMessage);
    }
  },
};
</script>
