<!--
Component for course enrollment details.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Course Enrollment Details | {{studentName}}</p>
    <div class="row mb-2">
      <div class="col">
        <label for="crs_code">Course</label>
        <div class="border p-1">
          {{courseName}}
        </div>
      </div>
      <div class="col">
        <label for="coe_type">Enrollment Type</label>
        <select class="form-select" id="coe_type" v-model="coe.enrol_type">
          <option v-for="x in SD.EnrolTypes" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
        </select>
      </div>
      <div class="col">
        <label for="coe_status">Status</label>
        <select class="form-select" id="coe_status" v-model="coe.enrol_status" :disabled="isStudent">
          <option v-for="x in SD.EnrolStatuses" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
        </select>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col">
        <label for="coe_grade">Grade</label>
        <select class="form-select" id="coe_grade" v-model="coe.grade" :disabled="isStudent">
          <option v-for="x in SD.CourseGrades" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
        </select>
      </div>
      <div class="col">
        <label for="coe_score">Current Score</label>
        <input
          type="number"
          min="0"
          max="100"
          class="form-control"
          id="coe_score"
          :disabled="isStudent"
          v-model="coe.current_score"
        />
      </div>
      <div class="col">
        <label for="coe_remarks">Remarks</label>
        <textarea rows="2" class="form-control" id="coe_remarks" v-model="coe.remarks" :disabled="isStudent"></textarea>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col">
        <div class="mt-4">
          <button class="btn btn-outline-success me-2" @click="save" type="button">
            Save
            <i class="bi bi-save"></i>
          </button>
          <button class="btn btn-outline-danger" @click="reset" type="button">
            Clear
            <i class="bi bi-eraser"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseEnrollmentDetails",
  data: function() {
    return {
      coe: {
        enrol_status: "IPEN",
        course_offering: {course: {}},
        student: this.isStudent ? this.currentUser : undefined
      }
    };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called: id=" + this.$route.params.id);
      return this.$route.params.id > 0;
    },
    studentName() {
      if(this.coe.student) {
        return this.coe.student.first_name + " " + 
              this.coe.student.last_name + " (" +
              this.coe.student.person.org_id + ")";
      } else {
        return "--"
      }
    },
    courseName() {
      let x = this.coe.course_offering.course;
      return x.title + " :: " + x.code + " (" +x.ltp + ")";
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log(
      "CourseEnrollmentDetails.beforeRouteUpdate: to=" +
        to.path +
        ". from=" +
        from.path
    );
    if (from.path.startsWith(to.path)) {
      this.reset();
    } else if (to.params.id) {
      this.load();
    }
    next();
  },
  created: function() {
    console.log("Creating course enrollment details.");
    // Alias 'this' for accessing in promises
    let vm = this;
    vm.courses = [];
    if (vm.isEdit) {
      vm.load();
    } else {
      vm.reset();
    }
  },
  methods: {
    load() {
      console.log("Loading course enrollment details.");
      let vm = this;
      let cid = vm.coe.id || vm.$route.params.id;
      vm.$http
        .get("coe_view/" + cid)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.coe = res.data.body;
            vm.oldStatus = vm.coe.status;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error: " + error);
        });
    },
    save() {
      let vm = this;
      //TODO: Check status and role before allowing save
      if (!confirm("Confirm save?")) {
        vm.setStatusMessage("User canceled save!");
        return;
      }
      console.log("Saving course enrollment details.");
      vm.$http
        .post("coe_save", vm.coe)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.coe = res.data.body;
            if (!vm.isEdit) {
              let v = `${vm.$route.path}/${vm.coe.id}`;
              console.log("Loading COE view: " + v);
              vm.$router.push({ path: v });
            } else {
              vm.setStatusMessage("Saved successfully!");
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
      this.coe = { enrol_status: "IPEN", course_offering: {course:{}}, 
                  student: this.isStudent ? this.currentUser : undefined };
      console.log("Clearing course enrollment details: "+JSON.stringify(this.coe));
    }
  }
};
</script>
