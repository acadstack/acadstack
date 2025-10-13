<template>
  <div class="container-fluid">
    <span class="sec-hdr">Student Strength Degree/Course Wise</span>
    <div class="row mb-2">
       <div class="col">
        <label for="crs_cd">Course Code</label>
        <input
          id="crs_cd" class="form-control" type="text" v-model.trim="search_crit.course_code" />
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
          <div class="col-md-2">Course Code/Title</div>
          <div class="col-md-1">L-T-P-S-C</div>
          <div class="col-md-2">Offering Department</div>
          <div class="col-md-1">Academic Session</div>
          <div class="col-md-2">Offered For</div>
          <div class="col-md-1">Student Strength</div>
          <div class="col-md-2" v-if="!isStudent">
              <a class="btn btn-outline-success" :href="`download_degree_wise_students/${search_crit.course_code}/${search_crit.acad_session}`">Download CSV</a>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="stustrength.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in stustrength" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">{{s.title}} ({{s.code}})</div>
          <div class="col-md-1">{{s.ltp}}</div>
          <div class="col-md-2">{{labelFor(SD.Departments, s.offering_department)}}</div>
          <div class="col-md-1">{{ s.acad_session}}</div>
          <div class="col-md-2">{{labelFor(SD.Degrees, s.degree)}}</div>
          <div class="col-md-1">{{s.no_of_students}} </div>
          
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "StudentStrength",
  components: {
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      search_crit: {
        report_name: "StudentStrength",
        course_code: "-",
        acad_session: "",
      },
      stustrength: [],
  };
  },
  mounted: function() {
    if(this.$route.name=='    ') {
      if (sessionStorage.GenerateCoursestustrength) {
        let dd = JSON.parse(sessionStorage.GenerateCoursestustrength);
        this.stustrength = dd.stustrength;
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
      console.log("Searching stustrength");
      vm.$http
        .post("stu.strength", vm.search_crit)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.stustrength = res.data.body.data;
            if(vm.$router.currentRoute.name=='stu.strength') {
              let dd = {stustrength: vm.stustrength, search_crit: vm.search_crit};
              sessionStorage.GenerateCoursestustrength = JSON.stringify(dd);
            }
            vm.setStatusMessage("Found "+vm.stustrength.length+" records");
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
      sessionStorage.GenerateCoursestustrength = undefined;
      this.search_crit = {
        report_name: "GenerateCoursestustrength",
        course_code: "-",
        acad_session: ""        
        };
      this.stustrength = [];
    },
  },
};
</script>
