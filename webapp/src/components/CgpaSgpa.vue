<template>
  <div class="container-fluid">
    <span class="sec-hdr">Generation of CGPA and SGPA Report</span>
    <div class="row mb-2">
       <div class="col">
        <acad-session v-bind:acad_session="search_crit.acad_session"
                label="Academic Session"
                v-on:update:acad_session='search_crit.acad_session=$event'/>
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
          <div class="col-md-1">S#</div>
          <div class="col-md-1">Entry Number</div>
          <div class="col-md-1">Name</div>
          <div class="col">Dept</div>
          <div class="col">CGPA</div>
          <div class="col">SGPA</div>
          <div class="col">Cred Earned</div>
          <div class="col">Cred Registered</div>
          <div class="col">Commulative earned Total</div>
          <div class="col" v-if="!isStudent">
              <a class="btn btn-outline-success" :href="`download_cgpa_sgpa/${search_crit.acad_session}`">Download CSV</a>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="enrolments.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in enrolments" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-1">{{s.roll_no}}</div>
          <div class="col-md-2">{{s.first_name + "" + s.last_name}}</div>
          <div class="col">{{labelFor(SD.Departments, s.dept_name)}}</div>
         <div class="col-md-1">{{s.cgpa}}</div>
         <div class="col-md-1">{{s.sgpa}}</div>
         <div class="col">{{s.cred_earned}}</div>
          <div class="col">{{s.cred_registered}}</div>
          <div class="col">{{s.cred_earned_total}}</div>
          
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "CgpaSgpa",
  components: {
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      search_crit: {
        report_name: "GenerateCgpaSgpa",
        acad_session: "",
      },
      enrolments: [],
  };
  },
  mounted: function() {
    if(this.$route.name=='cgpa.sgpa') {
      if (sessionStorage.CgpaSgpa) {
        let dd = JSON.parse(sessionStorage.CgpaSgpa);
        this.enrolments = dd.enrolments;
        this.search_crit = dd.search_crit;
      } else {
        this.reset();
      }
    } else {
      this.reset();
    }
  },
  methods: {
    search() {
      let vm = this;
      console.log("Searching Enrolments");
      vm.$http
        .post("cgpa_sgpa", vm.search_crit)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.enrolments = res.data.body.data;
            if(vm.$router.currentRoute.name=='cgpa.sgpa') {
              let dd = {enrolments: vm.enrolments, search_crit: vm.search_crit};
              sessionStorage.CgpaSgpa = JSON.stringify(dd);
            }
            vm.setStatusMessage("Found "+vm.enrolments.length+" records");
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      sessionStorage.CgpaSgpa = undefined;
      this.search_crit = {
        report_name: "GenerateCgpaSgpa",
        acad_session: "",        
        };
      this.enrolments = [];
    },
  },
};
</script>
