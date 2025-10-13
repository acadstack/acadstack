<template>
  <div class="container-fluid">
    <span class="sec-hdr">Generate Course Enrolments </span>
    <div class="row mb-2">
      <div class="col">
        <label for="dept">Dept.</label>
        <select id="dept" class="form-select" v-model.trim="search_crit.dept_name">
          <option
            v-for="cs in SD.Departments"
            v-bind:value="cs.id"
            :key="cs.id"
          >
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col">
        <label for="ent_yr">Entry Year</label>
        <input
          id="ent_yr"
          class="form-control"
          type="number"
          min="2010"
          max="2099"
          v-model.trim="search_crit.entry_year"
          placeholder="YYYY (e.g., 2019)"
        />
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
          <div class="col-md-2">Session</div>
          <div class="col-md-2">Entry No.</div>
          <div class="col-md-2">Name</div>
          <div class="col">Dept</div>
          <div class="col">Course</div>
          <div class="col">Enrol type</div>
          <div class="col-md-2" v-if="!isStudent">
              <a class="btn btn-outline-success" :href="`download_course_enrolments/${search_crit.dept_name}/${search_crit.entry_year}/${search_crit.acad_session}`">Download CSV</a>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="enrolments.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in enrolments" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">{{s.acad_session}}</div>
          <div class="col">
            <a :href="'#/std.detail/'+s.user_id">{{s.entry_no}}</a>
          </div>
          <div class="col-md-2">{{ s.first_name }} {{s.last_name}}</div>
          <div class="col">{{labelFor(SD.Departments, s.dept_name)}}</div>
          <div class="col">{{s.title}} ({{s.code}})</div>
          <div class="col">{{labelFor(SD.EnrolTypes, s.enrol_type)}}</div>
          
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "GenerateCourseEnrolments",
  components: {
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      search_crit: {
        report_name: "GenerateCourseEnrolments",
        dept_name: "-",
        entry_year: "-",
        acad_session: "-",
      },
      enrolments: [],
  };
  },
  mounted: function() {
    if(this.$route.name=='course.enrolments') {
      if (sessionStorage.GenerateCourseEnrolments) {
        let dd = JSON.parse(sessionStorage.GenerateCourseEnrolments);
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
        .post("course.enrolments", vm.search_crit)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.enrolments = res.data.body.data;
            if(vm.$router.currentRoute.name=='course.enrolments') {
              let dd = {enrolments: vm.enrolments, search_crit: vm.search_crit};
              sessionStorage.GenerateCourseEnrolments = JSON.stringify(dd);
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
      sessionStorage.GenerateCourseEnrolments = undefined;
      this.search_crit = {
        report_name: "GenerateCourseEnrolments",
        dept_name: "-",
        entry_year: "-",
        acad_session: "-"        
        };
      this.enrolments = [];
    },
  },
};
</script>
