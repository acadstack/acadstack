<!--
Component for student details.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Student Details</p>
    <form>
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="st_firstnm">First Name</label>
            <input type="text" class="form-control" id="st_firstnm" v-model="student.first_name" :disabled="viewOnly"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="st_lastnm">Last Name</label>
            <input type="text" class="form-control" id="st_lastnm" v-model="student.last_name" 
            :disabled="viewOnly"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="st_rollno">Roll No.</label>
            <input type="text" class="form-control" id="st_rollno" v-model="student.person.org_id" :disabled="viewOnly" />
          </div>
        </div>
        <div class="col">
          <div>
            <label for="st_deg">Degree</label>
            <div class="input-group">
              <select class="form-select" id="st_deg" v-model="student.person.degree" :disabled="viewOnly">
                <option v-for="x in SD.Degrees" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="st_email">Email</label>
            <input type="email" class="form-control" id="st_email" v-model="student.email" :disabled="viewOnly"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="st_dept">Department</label>
            <select class="form-select" id="st_dept" v-model="student.person.dept_name" :disabled="viewOnly">
              <option
                v-for="cs in SD.Departments"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
        </div>
        <div class="col">
            <div>
              <label for="st_yoe">Year-of-entry</label>
              <input type="text" placeholder="YYYY" 
                class="form-control" id="st_yoe" 
                pattern="\d{4}" :disabled="viewOnly" 
                v-model="student.person.year_of_entry" />
            </div>
        </div>
         <div class="col">
            <div>
              <label for="st_cat">Category</label>
              <select class="form-select" id="st_cat" v-model="student.person.category"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.PersonCategories"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
            </div>
        </div>       
      </div>

       <div class="row mb-2">
         <div class="col">
            <div>
              <label for="st_cat">Minor/Concentration Specialization</label>
              <select class="form-select" id="st_cat" v-model="student.person.deg_type_spec"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.MinorConcSpecialization"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
            </div>
        </div>
        <div class="col">
           <div>
            <label for="st_deg">Degree Type</label>
            <div class="input-group">
              <select class="form-select" id="st_deg" v-model="student.person.degree" :disabled="viewOnly">
                <option v-for="x in SD.Degrees" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
              </select>
            </div>
          </div>
          </div>      
        <div class="col">
            <div>
              <label for="st_cat">Current Status</label>
              <select class="form-select" id="st_cat" v-model="student.person.current_status"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.StudentStatus"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
            </div>
        </div>
      </div>
    </form>
    <div class="card" v-if="!isNew">
      <div class="card-header">
        <button class="btn btn-outline-primary me-2"
        v-bind:class="{ 'text-decoration-underline fst-italic': tab=='acads' }"
        @click="tab='acads'">Academics</button>
        <button class="btn btn-outline-primary"
        v-bind:class="{ 'text-decoration-underline fst-italic': tab=='docs' }"
        @click="tab='docs'">Documents</button>
      </div>
      <div class="card-body">
        <div v-show="tab=='acads'">
          <h6>Academics</h6>
          <StudentAcademics  v-if="loaded" 
            v-on:reload-student-info="loaded=false; load()"
            v-bind:enrollments="student.enrollments" 
            v-bind:acad_sessions="student.acad_sessions" 
            v-bind:user_id="student.id" />
          <div class="text-center" v-else>Loading student academics...</div>
        </div>
        <StudentDocuments v-show="tab=='docs'" 
          v-bind:student_id="student.id" />
      </div>
    </div>
  </div>
</template>

<script>
import StudentAcademics from "./StudentAcademics.vue";
import StudentDocuments from "./StudentDocuments.vue";

export default {
  name: "StudentDetails",
  components: {
    "StudentAcademics": StudentAcademics,
    "StudentDocuments": StudentDocuments
  },

  data: function() {
    return { tab: 'acads', student: {person: {}, enrollments: {}, acad_sessions: []} };
  },
  computed: {
    isNew() {
      let objid = this.$route.params.id;
      console.log("isNew() called. id="+objid);
      return objid == undefined || objid < 1;
    }
  },
  // beforeRouteUpdate(to, from, next) {
  //   console.log(`StudentDetails.beforeRouteUpdate. from=${from}, to=${to}`);
  //   if (from.path.startsWith(to.path)) {
  //     this.reset();
  //   } else if (to.params.id) {
  //     this.student.id = to.params.id;
  //     this.load();
  //   }
  //   next();
  // },
  created: function() {
    console.log("Creating Student Details");
    let vm = this;
    // Only academic section can edit student details
    vm.viewOnly = !vm.isAcad;
    if (!vm.isNew) {
      vm.student.id = vm.$route.params.id;
      vm.load();
    } else if (vm.isStudent) {
      let v = `${vm.$route.path}/${vm.currentUser.id}`;
      console.log("Loading view: "+v);
      vm.$router.push({ path: v });
    } else {
      vm.reset();
    }
  },
  methods: {
    load() {
      let vm = this;
      console.log("Loading student details: "+vm.student.id);
      if (vm.student.id) {
        vm.$http
          .get(`get_student_academics/${vm.student.id}`)
          .then(function(res) {
            if (res.data.status == "OK") {
              vm.student = res.data.body;
              vm.loaded = true;
              console.log("Got student details: "+JSON.stringify(vm.student));
            } else {
              vm.setStatusMessage(res.data.body);
            }
          })
          .catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when contacting the server.");
          });
      } else {
        console.log("User ID is not supplied!");
      }
    },
    reset() {
      this.student = {person: {}, enrollments:{}, acad_sessions: []};
      this.loaded = false;
      console.log("Clearing student details.");
    }
  }
};
</script>
