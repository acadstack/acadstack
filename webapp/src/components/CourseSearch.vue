<!--
Component for searching the existing courses.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h6>Find Existing Courses</h6>
    <form @submit.prevent="find(false)" v-if="this.$route.name=='cour.find'">
      <div class="row mb-2">
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
        <div class="col-md-2">
          <div>
            <label for="crs_ltp">L-T-P</label>
            <div class="input-group">
              <input type="text" class="form-control" id="cr_ltp" v-model.trim="ltpsc.ltp"/>
            </div>
          </div>
        </div>
        <div class="col-md-2">
          <div>
            <label for="crs_status">Status</label>
            <select class="form-select" id="crs_status" v-model.trim="course.status">
              <option
                v-for="cs in SD.CourseStatuses"
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
    </form>

    <div class="card">
      <div class="card-header">
        Results
        <span class="float-end">
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
      </div>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col">Course</div>
          <div class="col-md-2">Status</div>
          <div class="col-md-1" v-if="actions">
            <div class="dropdown me-2">
              <button type="button" class="btn btn-primary dropdown-toggle"
                data-bs-toggle="dropdown" aria-expanded="false">
                Action
              </button>
              <div class="dropdown-menu">
                <a class="dropdown-item" @click.prevent="onAction(act)"
                  v-for="act in actions" :key="act">{{act.label}}</a>
              </div>
            </div>
          </div>
        </div>
        <p v-if="results.courses.length == 0">Nothing to show yet!</p>
        <div class="row row-striped mt-4" v-for="(r, i) in results.courses" :key="r.id">
          <div class="col-md-1">{{(results.pg_no - 1) * results.pg_size + i + 1}}</div>
          <div class="col">
            <a :href="'#/cour.detail/'+r.id">{{r.code + " :: " + r.title + " :: "+ r.ltp}}</a>
          </div>
          <div class="col-md-2">{{labelFor(SD.CourseStatuses, r.status)}}</div>
          <div class="col-md-1" v-if="actions">
            <input class="form-check-input" :value="r.id" type="checkbox" v-model="markedItems" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
export default {
  name: "CourseSearch",
  setup() {
    return { v$: useVuelidate() }
  },
  data: function() {
    return {
      course: { pg_no: 1 },
      ltpsc:{
        ltp:"",
        sc:""
      },
      results: { courses: [], has_next: false },
      markedItems: [],
      /**
       * Defines the allowed actions to each role. The key is
       * role and value is the action label.
       */
      actionsMap: {
        // "FAC": [{label: "Offer"}]
      }
    };
  },
  computed: {
    actions() {
      return this.actionsMap[this.userRole];
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log("CourseSearch.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  created: function() {
    console.log("Creating CourseSearch");
    // Alias 'this' for accessing in promises
    // var vm = this;
  },
  mounted: function() {
    console.log(`Current route: ${this.$route.name}`)
    if(this.$route.name=='cour.find'){
      if (sessionStorage.couCourse) {
        this.course = JSON.parse(sessionStorage.couCourse);
      }
      if (sessionStorage.myCourS) {
        this.results = JSON.parse(sessionStorage.myCourS);
      } else {
        this.results = { courses: [], has_next: false };
      }
    }
    else{
      this.find(false);
    }
  },
  methods: {
    deleteMarked() {
      let vm = this;
      if (
        confirm("Deleted all selected " + vm.markedItems.length + " items?")
      ) {
        let vm = this;
        vm.$http
          .post("course_delete", {ids: vm.markedItems})
          .then(function(res) {
            if (res.data.status == "OK") {
              vm.markedItems = [];
              vm.find(false); // Refresh results from server
            } else {
              vm.setStatusMessage(res.data.body);
            }
          })
          .catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when contacting the server.");
          });
      } else {
        vm.markedItems = [];
      }
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
      if (!is_paging) vm.course.pg_no = 1;
      sessionStorage.couCourse = JSON.stringify(vm.course);
      if(this.$route.name=='cour.find'){
        vm.v$.$touch()
        if (vm.v$.$invalid) {
          return;
        }
      }
      else{
        var user = vm.currentUser;
        vm.course.author = user.id;
        vm.results.courses = [];
      }
      vm.results.courses = [];
      vm.$http
        .post("cour_find", vm.course)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.results = res.data.body;
            if(vm.$router.currentRoute.name=='cour.find'){
              sessionStorage.myCourS = JSON.stringify(vm.results);
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
      sessionStorage.myCourS = undefined;
      sessionStorage.couCourse = undefined;
    },
    onAction(act) {
      let vm = this;
      vm.setStatusMessage("TODO: Action to be performed: "+act);
    }
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
