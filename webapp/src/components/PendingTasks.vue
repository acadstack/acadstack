<!--
Component for searching the existing courses.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Pending Tasks </p>
    <div class="clearfix">
      <div class="float-start">
        <ul class="nav nav-tabs">
          <li class="nav-item" v-if="courseStage == 'author'">
            <a class="nav-link" :class="{active: tab === 'enrollments'}" 
              @click="tab='enrollments'">Enrollments (for instructor)</a>
          </li>
          <li class="nav-item" v-if="['hod', 'author'].includes(courseStage)">
            <a class="nav-link" :class="{active: tab === 'ba-enrollments'}" 
              @click="tab='ba-enrollments'">Enrollments (for advisor)</a>
          </li>
          <li class="nav-item" v-if="courseStage">
            <a class="nav-link" :class="{active: tab === 'created'}" 
              @click="tab='created'">New Courses Created</a>
          </li>
          <li class="nav-item" v-if="['hod', 'author'].includes(courseStage)">
            <a
              class="nav-link"
              :class="{active: tab === 'offered'}"
              @click="tab='offered'"
            >Offered Courses</a>
          </li>
        </ul>
      </div>
    </div>
    <div v-if="tab=='created' && courseStage">
      <div class="card">
        <div class="card-header">
          Results
          <span class="float-end">
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="course_create.pg_no > 1"
              @click="prev_pg_create"
            >
              Prev
            </button>
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="results_create.has_next"
              @click="next_pg_create"
            >
              Next
            </button>
          </span>
        </div>
        <div class="card-body">
          <div class="row hdr-row border-bottom border-info">
            <div class="col-md-1">S#</div>
            <div class="col">Course</div>
            <div class="col-md-2">Status</div>
          </div>
          <p v-if="results_create.courses.length == 0">Nothing to show yet!</p>
          <div
            class="row row-striped mt-4"
            v-for="(r, i) in results_create.courses"
            :key="r.id"
          >
            <div class="col-md-1">
              {{ (results_create.pg_no - 1) * results_create.pg_size + i + 1 }}
            </div>
            <div class="col">
              <a :href="'#/cour.detail/' + r.id">{{
                r.code + " :: " + r.title + " :: " + r.ltp
              }}</a>
            </div>
            <div class="col-md-2">
              {{ labelFor(SD.CourseStatuses, r.status) }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="tab=='offered' && ['hod', 'author'].includes(courseStage)">
      <div class="card">
        <div class="card-header">
          Results
          <span class="float-end">
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="course_offered.pg_no > 1"
              @click="prev_pg_offered"
            >
              Prev
            </button>
            <button
              class="btn btn-outline-info btn-sm me-4"
              v-if="results_offered.has_next"
              @click="next_pg_offered"
            >
              Next
            </button>
          </span>
        </div>
        <div class="card-body">
          <div class="row hdr-row border-bottom border-info">
            <div class="col-md-1">S#</div>
            <div class="col">Course</div>
            <div class="col-md-2">Status</div>
          </div>
          <p v-if="results_offered.courses.length == 0">Nothing to show yet!</p>
          <div
            class="row row-striped mt-4"
            v-for="(r, i) in results_offered.courses"
            :key="r.id"
          >
            <div class="col-md-1">
              {{ (results_offered.pg_no - 1) * results_offered.pg_size + i + 1 }}
            </div>
            <div class="col">
              <a :href="'#/co.detail/' + r.id">{{
                r.course.code + " :: " + r.course.title + " :: " + r.course.ltp
              }}</a>
            </div>
            <div class="col-md-2">
              {{ labelFor(SD.OfferingStatuses, r.status) }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="tab=='enrollments'">
      <EnrolledStudents v-if="loadedEnrolments"
        v-bind:enrollments="results_enrollment" 
        v-on:update-enrollments="onChangeEnrollments"/>
      <div v-else>Nothing in enrolments!</div>
    </div>
    <div v-if="tab=='ba-enrollments'">
      <EnrolledStudents v-if="loadedEnrolments"
        v-bind:enrollments="results_ba_enrollment" 
        v-on:update-enrollments="onChangeEnrollments"/>
      <div v-else>Nothing in enrolments for advisor!</div>
    </div>
  </div>
</template>

<script>
import EnrolledStudents from "./EnrolledStudents.vue";
export default {
  name: "PendingTasks",
  components: {
      EnrolledStudents: EnrolledStudents
  },
  data: function() {
    return {
      loadedEnrolments: false,
      tab: "enrollments",
      course_create: { pg_no: 1 },
      results_create: { courses: [], has_next: false },
      course_offered: { pg_no: 1 },
      results_offered: { courses: [], has_next: false },
      newenrolled:{
        status:"",
        ids:[]
      },
      results_enrollment: [],
      results_ba_enrollment: []
    };
  },
  async created() {
    console.log("Creating PendingTasks");
    await this.load()
  },
  methods: {
    async next_pg_create() {
      this.course_create.pg_no += 1;
      await this.load_create();
    },
    async prev_pg_create() {
      this.course_create.pg_no -= 1;
      await this.load_create();
    },
    async next_pg_offered() {
      this.course_offered.pg_no += 1;
      await this.load_offered();
    },
    async prev_pg_offered() {
      this.course_offered.pg_no -= 1;
      await this.load_offered();
    },
    async onChangeEnrollments() {
      await this.load_enrol();
      this.setStatusMessage("Updated enrollments!");
    },
    async load(){
      let vm = this;
      if(vm.courseStage == 'hod'){
        vm.course_create.status=["HAP","CAR"];
        vm.course_create.dept = vm.currentUser.dept;
        vm.course_offered.status="P";
        vm.course_offered.dept = vm.currentUser.dept;
        await Promise.all(
          [vm.load_create(), vm.load_offered(), vm.load_enrol()]
        );
      }
      else if(vm.courseStage == 'dean'){
        vm.course_create.status="CAP"
        await vm.load_create();
      }
      else if(vm.courseStage == 'author'){
        vm.course_create.status=["DRA","HAR"];
        vm.course_create.author = vm.currentUser.id;
        vm.course_offered.status="P";
        vm.course_offered.instructor_id = vm.currentUser.id;
        await Promise.all(
          [vm.load_create(), vm.load_offered(), vm.load_enrol()]
        );
      } else {
        console.debug("No course approval step for the user.");
      }
    },
    async load_create() {
      let vm = this;
      vm.results_create.courses = [];
      try {
        let res = await vm.$http.post("cour_find", vm.course_create);
        if (res.data.status == "OK") {
          vm.results_create = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      }
    },
    async load_offered() {
      let vm = this;
      vm.results_offered.courses = [];
      try {
        let res = await vm.$http.post("co_find", vm.course_offered);
        if (res.data.status == "OK") {
          vm.results_offered = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      }
    },
    async load_enrol(){
      console.log("Loading enrollments for the CO.");
      let vm = this;
      if(vm.courseStage == 'author'){
        try {
          let res = await vm.$http.get(`get_instructor_courses_enrol`);
          if (res.data.status == "OK") {
            vm.results_enrollment = res.data.body.instructor_enrol;
            vm.results_ba_enrollment = res.data.body.advisor_enrol;
            vm.loadedEnrolments = true;
            console.debug("Loaded enrollments as faculty.")
          } else {
            vm.setStatusMessage(res.data.body);
          }
        } catch(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        }
      } else if(vm.courseStage == 'hod') {
        try {
          let res = await vm.$http.get(`get_advisor_courses_enrol`);
          if (res.data.status == "OK") {
            vm.results_ba_enrollment = res.data.body;
            vm.loadedEnrolments = true;
            console.debug("Loaded enrollments as HoD.")
          } else {
            vm.setStatusMessage(res.data.body);
          }
        } catch(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        }
      } else {
        console.log("!!! Not loading enrolments!!");
      }
    },
    reset(){
      this.loadedEnrolments = false;
      this.results_enrollment = [];
    }
  },
};
</script>
