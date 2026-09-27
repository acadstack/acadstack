<template>
  <div class="container-fluid">
    <span class="sec-hdr">Course/Department Wise Grade Distribution </span>
    <div class="row mb-2">
         <div class="col">
        <label for="deg">Degree</label>
        <select id="deg" class="form-select" v-model.trim="search_crit.degree">
          <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
        
      <div class="col">
        <div>
          <acad-session v-bind:acad_session="search_crit.acad_session"
                label="Academic Session"
                v-on:update:acad_session='search_crit.acad_session=$event'/>
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
          <div class="col-md-1">S#</div>
          <div class="col-md-2">No of Students</div>
          <div class="col">Dept</div>
          <div class="col">Course</div>
          <div class="col">Enrol type</div>
          <div class="col-md-2" v-if="!isStudent">
              <a class="btn btn-outline-success" :href="`download_grade_distribution/${search_crit.acad_session}/${search_crit.degree}`">Download CSV</a>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="enrolments.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in enrolments" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>        
          <div class="col-md-2">{{ s.no_of_students }}</div>
          <div class="col">{{labelFor(SD.Departments, s.dept_name)}}</div>
          <div class="col">{{s.grade}}</div>
          <div class="col">{{s.code}}</div>
          
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "GradeDistribution",
  components: {
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      search_crit: {
        report_name: "GenerateGradeDistribution",
        degree: "",       
        acad_session: "",
      },
      enrolments: [],
  };
  },
  mounted: function() {
    if(this.$route.name=='grade.distribution') {
      if (sessionStorage.GradeDistribution) {
        let dd = JSON.parse(sessionStorage.GradeDistribution);
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
        .post("grade_distribution", vm.search_crit)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.enrolments = res.data.body.data;
            if(vm.$router.currentRoute.name=='grade.distribution') {
              let dd = {enrolments: vm.enrolments, search_crit: vm.search_crit};
              sessionStorage.GradeDistribution = JSON.stringify(dd);
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
      sessionStorage.GradeDistribution = undefined;
      this.search_crit = {
        report_name: "GenerateGradeDistribution",
        degree: "",       
        acad_session: "",        
        };
      this.enrolments = [];
    },
  },
};
</script>
