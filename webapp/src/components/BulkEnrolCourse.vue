<!--
Component for searching offered courses.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h6>Bulk Enrol Students in a Course</h6>
    <form @submit.prevent="enrol_students()">
      <div class="row mb-2">
        <div class="col-md-4">
          <label for="stu_org_id">Entry number</label>
          <input
              id="stu_org_id"
              type="text"
              class="form-control"
              v-model.trim="entry_no_pattern"
              minlength="6"
              maxlength="15"
              required
              pattern="^\d{4}[A-Za-z]{2,4}\d{0,4}"
              placeholder="At least first 6 characters of entry no."
            />
        </div>
        <div class="col">
          <label for="crs_tt">Course to enrol</label>
          <vue-bootstrap-typeahead
            placeholder="Course name or code. Type atleast 3 characters."
            :data="courses"
            :serializer="(s) => get_course_label(s)"
            @mta-item-selected="onCourseSelect"
            @mta-input-changed="debouncedQuery"
          />
        </div>
        <div class="col-md-2">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit" :disabled="!(course_id > 0)">
              Enrol
            </button>
            <button class="btn btn-outline-danger" @click="reset" type="reset">
              Clear
            </button>
          </div>
        </div>
      </div>
    </form>
    <div class="card">
      <div class="card-header">
        <b>Students to enrol</b>
        <span class="float-end" v-if="selectedCourse.length > 0">Selected course: {{selectedCourse}}</span>
      </div>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col">Name</div>
          <div class="col-md-2">Entry No.</div>
          <div class="col-md-4">Department</div>
        </div>
        <p v-if="students.length == 0">Nothing to show yet!</p>
        <div
          class="row row-striped mt-4"
          v-for="(r, i) in students"
          :key="r.id"
        >
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col">{{ r.first_name +" "+r.last_name }}</div>
          <div class="col-md-2">{{ r.org_id }}</div>
          <div class="col-md-4">{{ labelFor(SD.Departments, r.dept_name) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import _ from "lodash";

export default {
  name: "BulkEnrolCourse",
  components: {
    VueBootstrapTypeahead: VueBootstrapTypeahead,
  },

  data: function () {
    return {
      entry_no_pattern: "",
      course_id: "",
      selectedCourse: "",
      students: [],
      courses: [],
    };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("BulkEnrolCourse.beforeRouteUpdate");
    next();
  },
  watch: {
    "entry_no_pattern": _.debounce(function (entryNoPattern) {
      this.lookupStudents(entryNoPattern);
    }, 600),
  },

  created: function () {
    console.log("Creating BulkEnrolCourse");
  },
  methods: {
    debouncedQuery: _.debounce(async function(inp) {
      await this.lookupCourse(inp)
    }, 400),

    onCourseSelect(c) {
      this.course_id = c.id;
      this.selectedCourse = this.get_course_label(c)
      console.log("Selected course: " + JSON.stringify(c));
    },

    async lookupCourse(query) {
      let vm = this;
      if (_.isEmpty(query) || query.length < 3) {
        console.log("Min. 3 charaters needed. Ignored.");
        return;
      }
      await vm.doHttp(true, `co_lookup/${query}`, null,
          (b)=>{
            vm.courses = b;
            console.log("Courses looked up: " + JSON.stringify(vm.courses));
          }, vm.setStatusMessage)
    },
    lookupStudents(enp) {
      let vm = this;
      if (_.isEmpty(enp) || enp.length < 5) {
        console.log("Min. 5 charaters needed. Ignored.");
        return;
      }
      vm.$http
        .get(`student_lookup/${enp}`)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.students = res.data.body;
            console.log("Students looked up: " + JSON.stringify(vm.students));
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error: " + error);
        });
    },
    enrol_students() {
      if (!confirm("Confirm bulk enrollment?")) return;
      let vm = this;
      vm.$http
        .get(`co_bulkenrol/${vm.entry_no_pattern}/${vm.course_id}`)
        .then(function (res) {
          vm.setStatusMessage(res.data.body);
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      this.entry_no_pattern = "";
      this.course_id = "";
      this.courses = [];
      this.students = [];
      this.selectedCourse = ""
    },
  },
};
</script>
