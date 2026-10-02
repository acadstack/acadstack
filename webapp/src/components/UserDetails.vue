<!--
Component for user details.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="h5 card-header">
        <span>{{user.first_name}} {{user.last_name}} 
          <span v-if="isStudent"> ({{user.person.org_id}}) </span>
          | {{tab}}</span>
        <span class="float-end" v-if="(isStudent || isInstructor) && user.id != undefined">
          <button class="btn btn-outline-primary me-2" 
          v-bind:class="{ 'text-decoration-underline fst-italic': tab=='Profile' }"
          @click="tab='Profile'">Profile</button>
          <button class="btn btn-outline-primary me-2" 
          v-bind:class="{ 'text-decoration-underline fst-italic': tab=='Academics' }"
          @click="tab='Academics'">Academics</button>
          <button class="btn btn-outline-primary"
          @click="tab='Documents'" v-if="!viewOnly">Documents</button>
        </span>
      </div>
      <div class="card-body">
        <form v-show="tab=='Profile'" @submit.prevent="save">
          <div class="row mb-2">
            <div class="col">
              <div>
                <label for="loginid">Login ID</label>
                <input type="text" class="form-control" id="loginid" v-model="user.login_id" 
                :disabled="viewOnly"/>
              </div>
            </div>
            <div class="col">
              <div>
                <label for="st_role">Role</label>
                <select class="form-select" id="st_role" v-model="user.role" :disabled="viewOnly">
                  <option v-for="x in SD.UserRoles" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
                </select>
              </div>
            </div>
            <div class="col">
              <div>
                <label for="orgid">Org. ID</label>
                <input type="text" class="form-control" id="orgid" v-model="user.person.org_id" :disabled="viewOnly"/>
              </div>
            </div>
            <div class="col">
              <div>
                <label for="st_yoe">Year-of-entry</label>
                <input type="text" placeholder="YYYY" 
                  class="form-control" id="st_yoe" 
                  pattern="\d{4}" :disabled="viewOnly"
                  v-model="user.person.year_of_entry" />
              </div>
            </div>

          </div>
          <div class="row mb-2">
            <div class="col-md-3">
              <div>
                <label for="st_email">Email</label>
                <input type="email" class="form-control" id="st_email" v-model="user.email" 
                :disabled="viewOnly"/>
              </div>
            </div>
            <div class="col-md-3">
              <div>
                <label for="st_firstnm">First Name</label>
                <input type="text" class="form-control" id="st_firstnm" v-model="user.first_name" 
                :disabled="viewOnly"/>
              </div>
            </div>
            <div class="col-md-3">
              <div>
                <label for="st_lastnm">Last Name</label>
                <input type="text" class="form-control" id="st_lastnm" v-model="user.last_name" 
                :disabled="viewOnly"/>
              </div>
            </div>
            <div class="col-md-3">
              <div>
                <label class="form-check-label" for="st_locked">Locked?</label>
                <input type="checkbox" class="form-check-input" id="st_locked" v-model="user.is_locked" 
                :disabled="viewOnly"/>
              </div>
            </div>
          </div>
          <div class="row mb-2">
            <div class="col">
              <div>
                <!-- <label for="st_gender me-2">Gender: </label> -->
                <div class="form-check form-check-inline">
                  <input
                    type="radio"
                    id="gr_m"
                    class="form-check-input"
                    value="M"
                    v-model="user.person.gender"
                    :disabled="viewOnly"
                  />
                  <label class="form-check-label" for="gr_m">Male</label>
                </div>
                <div class="form-check form-check-inline">
                  <input
                    type="radio"
                    id="gr_f"
                    class="form-check-input"
                    value="F"
                    v-model="user.person.gender"
                    :disabled="viewOnly"
                  />
                  <label class="form-check-label" for="gr_f">Female</label>
                </div>
                <div class="form-check form-check-inline">
                  <input
                    type="radio"
                    id="gr_u"
                    class="form-check-input"
                    value="U"
                    v-model="user.person.gender"
                    :disabled="viewOnly"
                  />
                  <label class="form-check-label" for="gr_u">Unspecified</label>
                </div>
              </div>
            </div>
            <div class="col">
              <div>
                <label for="st_cat">Category</label>
                <select class="form-select" id="st_cat" v-model="user.person.category"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.PersonCategories"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
              </div>
            </div>
            <div class="col">
              <div>
                <label for="st_dept">Department</label>
                <select class="form-select" id="st_dept" v-model="user.person.dept_name"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.Departments"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
              </div>
            </div>
            <div class="col" v-if="isStudent" >
              <div>
                <label for="st_deg">Degree</label>
                <select class="form-select" id="st_deg" v-model="user.person.degree" :disabled="viewOnly">
                  <option v-for="x in SD.Degrees" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
                </select>
              </div>
            </div>
            <div class="col" v-if="isBatchAdvisor" >
              <div>
                <label for="st_batch">Advisor For Batch</label>
                <div class="input-group">
                  <select class="form-select" id="ba_deg" v-model="user.for_degree" :disabled="viewOnly">
                    <option v-for="x in SD.Degrees" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
                  </select>
                  <input id="st_batch" type="text" class="form-control" :disabled="viewOnly"
                    placeholder="Year (YYYY)" v-model="user.batch" />
                </div>
              </div>
            </div>
          </div>
          <div class="row mb-2">
            <div class="col-md-3" v-if="isStudent">
              <div>
                <label for="st_status">Student Current Status</label>
                <select class="form-select" id="st_status" v-model="user.person.current_status"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.StudentStatus"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
              </div>
            </div>           
            <div class="col" v-if="isStudent">
              <div>
                <label for="st_degtype">Type of Degree</label>
                <select class="form-select" id="st_degtype" v-model="user.person.deg_type"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.DegreeType"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
              </div>
            </div>
             <div class="col" v-if="isStudent">
              <div>
                <label for="st_degspec">Minor/Concentration Specialization</label>
                <select class="form-select" id="st_degspec" v-model="user.person.deg_type_spec"
                :disabled="viewOnly">
                  <option
                    v-for="cs in SD.MinorConcSpecialization"
                    v-bind:value="cs.id"
                    :key="cs.id"
                  >{{ cs.value }}</option>
                </select>
              </div>
            </div>
          </div>
            <div class="row mb-2">
              <div class="col" v-if="!viewOnly">
                <FileUploader
                v-on:fu-file-selected="photo_selected"/>
              </div>
              <div class="col">
                <div v-if="photo_new != undefined">
                  New:
                  <img v-bind:src="photo_new" class="img-thumbnail" style="width: 250px;"/>
                </div>
                <div v-if="user.known_faces && user.known_faces.length > 0">
                  <img :src="'get_image/'+user.known_faces[0].photo" class="img-thumbnail" style="width: 250px;"/>
                </div>
              </div>
          </div>
          <div class="row mb-2" v-if="!viewOnly">
            <div class="col">
              <div class="mt-4">
                <button class="btn btn-outline-success me-2" type="submit">
                  Save
                  <i class="bi bi-save"></i>
                </button>
                <button class="btn btn-outline-danger" @click="reset" type="reset">
                  Clear
                  <i class="bi bi-eraser"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="row mb-2" v-if="hasPermission('users.edit:any') && user.id != undefined">
            <div class="col">
              <button class="btn btn-outline-warning" type="button" @click="genResetKey">
                Generate Password Reset Key
                <i class="bi bi-key"></i>
              </button>
              <div class="alert alert-info mt-2" v-if="resetKeyInfo">
                <div>Reset key for <strong>{{resetKeyInfo.login_id}}</strong> (valid 30 minutes):</div>
                <input type="text" class="form-control mt-1" style="max-width: 200px; font-family: monospace;"
                  :value="resetKeyInfo.key_code" readonly @focus="$event.target.select()">
                <div class="mt-1">
                  Click the key above to select it, then copy it. Share it with the user;
                  they can enter it on the Password Reset screen along with their login ID
                  and email to set a new password.
                </div>
              </div>
            </div>
          </div>
        </form>
        <div v-if="user.id != undefined">
          <div v-show="tab=='Academics' && user.id">
            <StudentAcademics  v-if="enrollments_loaded" 
            v-on:reload-student-info="enrollments_loaded=false; load_student_academics()"
            v-bind:enrollments="student_enrollments" 
            v-bind:acad_sessions="acad_sessions"
            v-bind:user_id="user.id" />
            <!-- <StudentAcademics v-if="user.role=='STU'" v-bind:user_id="user.id" /> -->
            <InstructorTeaching v-if="isInstructor" v-bind:user_id="user.id"/>
          </div>
          <div v-show="tab=='Documents' && user.id" v-if="!viewOnly">
            <StudentDocuments v-if="isStudent" v-bind:student_id="user.id" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import StudentAcademics from "./StudentAcademics.vue";
import InstructorTeaching from "./InstructorTeaching.vue";
import StudentDocuments from "./StudentDocuments.vue";
import FileUploader from "./FileUploader.vue";
export default {
  name: "UserDetails",
  components: {
    "InstructorTeaching": InstructorTeaching,
    "StudentAcademics": StudentAcademics,
    "StudentDocuments": StudentDocuments,
    "FileUploader": FileUploader
  },
  data: function() {
    return { 
      tab: "Profile",
      photo_new: undefined,
      user: { person: { known_faces: [] } } ,
      student_enrollments: {},
      acad_sessions: [],
      resetKeyInfo: null
    };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called");
      return this.$route.params.id > 0;
    },
    canSave() {
      return this.hasPermission('users.edit:any') ||
        (this.hasPermission('users.edit:own') && this.user.id == this.currentUser.id);
    },
    isBatchAdvisor() {
      return this.user.batch !== undefined;
    },
    // The kinds of person the user's role counts as, e.g. ["student"].
    roster() {
      let role = (this.SD.UserRoles || []).find((r) => r.id == this.user.role);
      return role ? role.roster : [];
    },
    isStudent() {
      return this.roster.includes("student");
    },
    isInstructor() {
      return this.roster.includes("instructor");
    }
  },
  async beforeRouteUpdate(to, from, next) {
    console.log("UserDetails.beforeRouteUpdate");
    if (from.path.startsWith(to.path)) {
      this.reset();
    } else if (to.params.id) {
      await this.load();
    }
    next();
  },
  async created() {
    console.log("Creating User Details");
    let vm = this;
    if (vm.isEdit) {
      await vm.load();
    } else {
      vm.reset();
    }
    vm.viewOnly = !vm.canSave;
  },
  methods: {
    async load_student_academics() {
      let vm=this;
      await vm.doHttp(true, `get_student_academics/${vm.user.id}`,
        null, (b)=>{
          vm.student_enrollments = b.enrollments;
          vm.acad_sessions = b.acad_sessions;
          vm.enrollments_loaded = true;
          console.log("Loaded student enrollments: "+
            JSON.stringify(vm.student_enrollments));
        }, vm.setStatusMessage)
    },
    async load() {
      // Alias 'this' for accessing in promises
      let vm = this;
      let uid = vm.$route.params.id;
      console.log("Loading user details. id=" + uid);
      // Fetch data from an API
      await vm.doHttp(true, "user/" + uid, null,
          (b)=>{
            vm.user = b
          }, vm.setStatusMessage)
      
      if (vm.user.person == null) {
        vm.user.person = {};
      }
      if (vm.isStudent) {
        await vm.load_student_academics();
      }
    },
    async save() {
      let vm = this;
      if (!vm.canSave) {
        vm.setStatusMessage("You are not allowed to make changes!");
        return;
      }
      if (!confirm("Confirm save?")) {
        vm.setStatusMessage("User canceled save!");
        return;
      }
      if (vm.photo_new != undefined) {
        vm.user.photo_new = vm.photo_new;
      }
      console.log("Saving user details.");
      await vm.doHttp(false, "user_save", vm.user,
        (b)=>{
          vm.user = b;
          vm.setStatusMessage("Saved successfully!");
          vm.photo_new = undefined;
          console.log("Saved the user details!")
        }, vm.setStatusMessage)
    },
    reset() {
      this.user = { person: { known_faces: [] } };
      this.photo_new = undefined;
      this.enrollments_loaded = false;
      this.resetKeyInfo = null;
      console.log("Clearing user details.");
    },
    async genResetKey() {
      let vm = this;
      if (!confirm(`Generate a password reset key for ${vm.user.login_id}?`)) {
        vm.setStatusMessage("User canceled.");
        return;
      }
      await vm.doHttp(false, "admin_gen_prk", { id: vm.user.id },
        (b) => {
          vm.resetKeyInfo = b;
          vm.setStatusMessage("Reset key generated.");
        }, vm.setStatusMessage);
    },
    photo_selected(file) {
      console.log("Adding image.");
      let reader = new FileReader();
      let vm = this;
      reader.onload = function(e) {
        vm.photo_new = e.target.result;
        console.log("Image read.");
      };
      reader.readAsDataURL(file);
    },
    // removeImage: function(e) {
    //   console.log("Removing image: " + e);
    //   let kf = this.user.known_faces;
    //   var filtered = kf.filter(function(obj) { return obj != e; });
    //   this.user.known_faces = filtered;
    // }
  }
};
</script>
