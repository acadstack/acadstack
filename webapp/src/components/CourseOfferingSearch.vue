<!--
Component for searching offered courses.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h6>Offered Courses</h6>
    <form @submit.prevent="find(false)" v-if="isCOSearch">
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="st_dept">Offering Department</label>
            <select class="form-select" id="st_dept" v-model="course.dept">
              <option
                v-for="cs in SD.Departments"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
        </div>
        <div class="col-md-1">
          <div>
            <label for="crs_cd">Code</label>
            <input type="text" class="form-control" id="crs_cd" v-model.trim="course.code" />
          </div>
          <div v-if="!v$.course.code.validcode && v$.course.code.$dirty" class="text-danger">Invalid code</div>
        </div>
        <div class="col">
          <div>
            <label for="crs_tt">Title</label>
            <input type="text" class="form-control" id="crs_tt" v-model.trim="course.title" />
          </div>
        </div>
        <div class="col">
          <div>
            <acad-session v-bind:acad_session="course.acad_session"
                label="Acad session"
                v-on:update:acad_session='onAcadSessionChange'/>
          </div>
        </div>
        <div class="col-md-2">
          <div>
            <label for="crs_ltp">L-T-P</label>
            <div class="input-group">
              <input type="text" class="form-control" id="cr_ltp" v-model.trim="ltpsc.ltp"/>
            </div>
          </div>
        </div>
        <div class="col-md-1">
          <div>
            <label for="crs_ins">Instructor</label>
            <input type="text" class="form-control" id="crs_ins" v-model.trim="course.instructor" />
          </div>
        </div>
        
        <div class="col-md-1">
          <div>
            <label for="crs_status">Status</label>
            <select class="form-select" id="crs_status" v-model.trim="course.status">
              <option
                v-for="cs in SD.OfferingStatuses"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
        </div>
        <div class="col-md-2">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit">
              <i class="bi bi-search"></i>
            </button>
            <button class="btn btn-outline-danger" @click="reset" type="reset">
              <i class="bi bi-eraser"></i>
            </button>
          </div>
        </div>
      </div>
      <small class=" text-muted">
        If you do not find the desired results, please try specifying fewer criteria to widen the search results. All non-empty search fields are used <b>together</b> when searching.
      </small>
    </form>

    <div class="card">
      <div class="card-header">
        <span class="float-start">Results</span>
        <span class="float-end">
          <span class="btn-group">
            <div v-if="showActions" class="dropdown me-2">
              <button type="button" class="btn btn-primary dropdown-toggle" 
              data-bs-toggle="dropdown" aria-expanded="false" 
              :disabled="markedItems == undefined || markedItems.length == 0" >
                Action
              </button>
              <div class="dropdown-menu">
                <a class="dropdown-item" @click.prevent="onAction(act)"
                  v-for="act in actions" :key="act.id">{{act.label}}</a>
              </div>
            </div>
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="course.pg_no > 1"
              @click="prev_pg"
            >Prev</button>
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="results.has_next"
              @click="next_pg"
            >Next</button>
          </span>
        </span>
      </div>
      <div class="card-body">
        <p v-if="results.courses.length == 0">Nothing to show yet!</p>
        <div v-else class="row row-cols-1 row-cols-md-3 no-gutters">
          <div class="col p-2 border border-success" 
            v-bind:class="{ 'bg-secondary text-muted': 'C' == r.status }"
            v-for="(r, i) in results.courses" :key="r.id">
              <span class="me-2 float-start" v-if="showActions">
                <input :value="r.id" type="checkbox" 
                  :disabled="!canMarkCourse(r)" v-model="markedItems" />
              </span>
              <b>{{(results.pg_no - 1) * results.pg_size + i + 1}}) </b>
              <a :href="'#/co.detail/'+r.id">{{course_name(r)}}</a><br/>
              <span class="label-sm">Credits</span> {{r.course.ltp.substring(r.course.ltp.lastIndexOf("-")+1)}}.
              <span class="label-sm">Status</span> {{labelFor(SD.OfferingStatuses, r.status)}}.
              <span class="label-sm">Session</span> {{r.acad_session}}.
              <span class="label-sm">Enrolment</span> {{r.EnrollmentsCount}} in Sec.-{{r.section}}.
              <span class="label-sm">Offered by</span> Dept. of {{labelFor(SD.Departments, r.dept_name)}}. 
              <span class="label-sm">Slot</span> {{labelFor(SD.CourseSlots, r.slot)}}. 
              <span class="label-sm">Instructor(s)</span> {{r.instructors}}. 
              <br/>
              <span v-if="isAcad||isDean">
                <b>Feedback</b>
                <ul>
                  <li v-for="ci in r.instructors_info" :key="ci.id">
                    {{ci.name}} :: 
                    [<a :href="`#/view.insfb/${r.id}/${ci.id}/MID_SEM_FB`">Mid-sem feedback</a>]
                    &nbsp;&nbsp;&nbsp;
                    [<a :href="`#/view.insfb/${r.id}/${ci.id}/END_SEM_FB`">End-sem feedback</a>]
                  </li>
                </ul>
              </span>
              <span v-if="!isCOSearch">
                [<a :href="`#/view.insfb/${r.id}/${currentUser.id}/MID_SEM_FB`">Mid-sem feedback</a>]
                &nbsp;&nbsp;&nbsp;
                [<a :href="`#/view.insfb/${r.id}/${currentUser.id}/END_SEM_FB`">End-sem feedback</a>]
              </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import AcadSession from "./AcadSession.vue";
export default {
  name: "CourseOfferingSearch",
  components: {
    "AcadSession": AcadSession
  },
  setup() {
    return { v$: useVuelidate() }
  },
  data: function() {
    return {
      ltpsc:{
        ltp:"",
        sc:""
      },
      course: { pg_no: 1 },
      results: { courses: [], has_next: false },
      markedItems: [],
      user:{},
      passed_courses: {codes:[]},
      /**
       * Defines the allowed actions to each role. The key is
       * role and value is the action label.
       */
      actionsMap: {
        "STU": [{label: "Credit", id: "C"}, 
          {label: "Credit for Minor", id: "CM"},
          {label: "Credit for Concent.", id: "CC"}, 
          {label: "Audit", id: "A"}]
      }
    };
  },
  computed: {
    showActions() {
      return this.actions && this.results.courses.length > 0;
    },
    actions() {
      return this.actionsMap[this.userRole];
    },
    isCOSearch() {
      return this.$route.name=='co.find';
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log("CourseOfferingSearch.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  created: function() {
    console.log("Creating CourseOfferingSearch");
    // Alias 'this' for accessing in promises
    var vm = this;
    if (vm.isStudent) {
      console.log("Current user is student.");
      vm.$http
          .get("get_passed_courses/" + vm.currentUser.id)
          .then(function(res) {
            if (res.data.status == "OK") {
              vm.passed_courses = res.data.body;
            } else {
              vm.setStatusMessage(res.data.body);
            }
          })
          .catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error: " + error);
          });
    } else {
      console.log("Current user is NOT a student.");
    }
  },
  mounted: function() {
    
    console.log(`Current route: ${this.$route.name}`)
    if(this.isCOSearch)
    {
      if (sessionStorage.coCourse) {
        this.course = JSON.parse(sessionStorage.coCourse);
      }
      if (sessionStorage.myCoffS) {
        this.results = JSON.parse(sessionStorage.myCoffS);
      } else {
        this.results = { courses: [], has_next: false };
      }
    }
    else{
      this.results = { courses: [], has_next: false };
      this.find(false)
    }
  },
  methods: {
    onAcadSessionChange(acs) {
        this.course.acad_session = acs;
    },
    course_name(r) {
      return r.course.code + " | " + r.course.title + " | "+ r.course.ltp
    },
    next_pg() {
      this.course.pg_no += 1;
      this.find(true);
    },
    prev_pg() {
      this.course.pg_no -= 1;
      this.find(true);
    },
    find(is_paging) {
      let vm = this;
      if (!is_paging) {
        vm.course.pg_no = 1;
        vm.results = { courses: [], has_next: false };
      }
      sessionStorage.coCourse = JSON.stringify(vm.course);
      if(this.isCOSearch)
      {
        vm.v$.$touch()
        if (vm.v$.$invalid) {
          return;
        }
      }
      else{
        var user = this.currentUser;
        vm.course.instructor_id = user.id;
      }
      vm.results.courses = [];
      vm.$http
        .post("co_find", vm.course)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.results = res.data.body;
            if(vm.isCOSearch)
            {
              sessionStorage.myCoffS = JSON.stringify(vm.results);
            }
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
      this.results = { courses: [], has_next: false };
      this.course = { pg_no: 1 };
      this.markedItems = [];
      sessionStorage.myCoffS = undefined;
      sessionStorage.coCourse = undefined;
    },
    enrollCourse(req_data) {
      let vm = this;
      vm.$http
        .post("enroll_in_courses", req_data)
        .then(function(res) {
          vm.setStatusMessage(res.data.body);
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    onAction(act) {
      let vm = this;
      let req = {"user_id": vm.currentUser.id, 
        "co_ids": vm.markedItems, "enrol_type": act.id};
      vm.enrollCourse(req);
    },
    canMarkCourse(r) {
      let vm = this;
      // let acs1 = vm.SD.AcademicSessions[1]["id"];
      // let acs2 = vm.SD.AcademicSessions[2]["id"];
      let flag = false;
      if (vm.passed_courses.codes.indexOf(r.course.code) != -1) {
        flag = false;
      } else if (["E", "R"].includes(r.status)) {
        flag = true;
      }
      console.debug("Flag: "+flag);
      return flag;
    },
  },
  validations:{
    course:{
      code:{
        validcode(){
          if("code" in this.course ){
            var checkcode = new RegExp("^[A-Z]?[A-Z]?[0-9]?[0-9]?[0-9]?$", "i"); 
            if (!checkcode.test(this.course.code)){
                return false;
            }
            return true;
          }
          return true;
        }
      }
    }
  }
};
</script>
