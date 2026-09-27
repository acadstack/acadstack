<!--
Component for showing the enrolled student in a course.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div v-if="enrollments == undefined || enrollments.length == 0">Nothing to show yet!</div>
    <div v-else class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-1">S#</div>
          <div class="col">Roll No.</div>
          <div class="col">Name</div>
          <div class="col-md-2">Course Title/Code</div>
          <div class="col">Proposed Enrol. Req.</div>
          <div class="col">Status</div>
          <div class="col">Acad Session</div>
          <div class="col">Attnd.</div>
          <div class="col">
              <input class="form-check-input" type="checkbox" id="filterCb" v-model="showEnrolled">
              <label class="form-check-label" for="filterCb">Show only Enrolled</label>
          </div>
          <div class="col" v-if="!isStudent">
            <div class="btn-group">
              <div class="dropdown">
                <button
                  type="button"
                  class="btn btn-danger dropdown-toggle"
                  data-bs-toggle="dropdown"
                  aria-expanded="false"
                >Action</button>
                <div class="dropdown-menu">
                  <a class="dropdown-item" v-if="tochange.length > 0" @click ="Action('approve')">Approve Add/Drop</a>
                  <a class="dropdown-item" v-if="tochange.length > 0" @click ="Action('reject')">Reject Add/Drop</a>
                  <a class="dropdown-item" :href="`download_course_enrollments/${co_id}`">Download Students List</a>
                  <a class="dropdown-item" :href="`download_enrollments_for_grades/${co_id}`">Download Grades</a>
                </div>
              </div>
              <input class="ms-2 form-check-input" type="checkbox" v-model="all_marked" @change="toggleAll"/>
            </div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="row row-striped" v-for="(s, i) in filterEnrolments(enrollments)" :key="s.id">
          <div class="col-1">{{i+1}}</div>
          <div class="col">
            <span v-if="!isStudent">
              <a :href="'#/std.detail/'+s.user_id">{{s.org_id}}</a>
            </span>
            <span v-else>{{s.org_id}}</span>
          </div>
          <div class="col">{{s.student}}</div>
          <div class="col-md-2">
              {{ s.course}}
            </div>
          <div class="col">{{labelFor(SD.EnrolTypes, s.enrol_type)}}</div>
          <div class="col">
            <span v-if="isAcad">
              <a :href="'#/coe.detail/'+s.id">{{labelFor(SD.EnrolStatuses, s.enrol_status)}}</a>
            </span>
            <span v-else>{{labelFor(SD.EnrolStatuses, s.enrol_status)}}</span>
            </div>
          <div class="col">{{s.acad_session}}</div>
          <div class="col">
            <span v-if="s.attendance">
              <a v-if="!isStudent" :href="`#/att.detail/${s.id}`">{{s.attendance}}%</a>
              <span v-else>{{s.attendance}}%</span>
            </span>
            <span v-else>--</span>
          </div>
          <div class="col" v-if="!isStudent">
            <input type="checkbox" class="form-check-input"
            v-model="tochange" :value="s.id"
            :disabled="!(isAcad || isFaculty || isHod)" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "EnrolledStudents",
  props: ["co_id", "enrollments", "mode"],
  data: function() {
    return { 
        user:{},
        newenrolled:{
          co_id:0,
          status:"",
          ids:[]
        },
        tochange:[],
        all_marked: false,
        showEnrolled: false
      };
  },
  created: function() {
    console.log("Creating Course Enrollments");
  },
  methods: {
    toggleAll() {
      let vm = this;
      vm.tochange = [];
      if (vm.all_marked) {
        console.debug("Toggle ON all items")
        for(var x in vm.enrollments) {
          vm.tochange.push(vm.enrollments[x].id)
        }
      } else {
        console.debug("Toggle OFF all items")
      }
    },
    async save(){
      
      if (!confirm("Confirm save?")) {
        vm.setStatusMessage("User canceled save!");
        return;
      }
      var vm = this;
      if(vm.tochange.length == 0){
        vm.setStatusMessage("Select student to enrol!");
        return;
      }
      vm.newenrolled.ids = vm.tochange;
      vm.newenrolled.co_id = vm.co_id;
      await vm.$http.post('change_enroll_status', vm.newenrolled)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.reset();
          vm.$emit('update-enrollments', true);
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    },
    reset(){
      this.tochange = [];
      this.all_marked = false;
      this.newenrolled={
        status:"",
        ids:[]
      };
    },
    Action(act){
      var vm = this;
      if (vm.isStudent) return;
      vm.newenrolled.status=act;
      vm.save();
    },
    filterEnrolments(enrolList) {
      let vm = this;
      return enrolList.filter(function (item) {
        if (vm.showEnrolled) {
          return item.enrol_status == 'ENRO';
        } else {
          return true;
        }
      });
    }
  }
};
</script>
