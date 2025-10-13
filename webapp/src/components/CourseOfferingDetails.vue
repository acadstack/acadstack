<!--
Component for course offering details.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Course Offering Details</p>
    <nav>
      <ul class="nav nav-tabs" role="tablist">
        <li class="nav-item" role="presentation">
          <a class="nav-link" :class="{active: tab === 'main'}" @click="tab='main'">Main</a>
        </li>
        <li class="nav-item" role="presentation">
          <a
            class="nav-link"
            :class="{active: tab === 'enrollments', disabled: !coffer.id}"
            @click="tab='enrollments'"
          >Enrollments</a>
        </li>
        <li class="nav-item" role="presentation">
          <a class="nav-link" :class="{active: tab === 'stats', disabled: !coffer.id}" @click="tab='stats'">Stats</a>
        </li>
        <li class="nav-item" v-if="!isStudent" role="presentation">
          <a class="nav-link" :class="{active: tab === 'notes'}" @click="tab='notes'">Notes</a>
        </li>
      </ul>
    </nav>
    <div class="tab-content">
      <div v-if="tab=='main'">
        <div class="row mb-2">
          <div class="col-md-8">
            <div class="row mb-2">
              <div class="col">
                <label for="crs_code">Course</label>
                <div class="input-group" v-show="showLookup && !viewOnly || coffer.course.title==undefined">
                  <vue-bootstrap-typeahead
                    placeholder="Title or code. Type atleast 3 characters."
                    :data="courses"
                    :serializer="getCourseLabel"
                    @mta-item-selected="onCourseSelect"
                    @mta-input-changed="debouncedQuery"
                    aria-describedby="btn-addon2"
                  />
                  <button
                      class="btn btn-outline-danger"
                      type="button"
                      id="btn-addon2"
                      @click="showLookup=false"
                    >Cancel</button>
                </div>
                <div class="input-group" v-show="!showLookup && coffer.course.title!=undefined">
                  <!-- <input
                    type="text"
                    class="form-control"
                    v-model.trim="coffer.course.title"
                    aria-describedby="btn-addon1"
                    disabled
                  /> -->
                  <div class="form-control" aria-describedby="btn-addon1">{{getCourseLabel(coffer.course)}}</div>
                  <button
                      class="btn btn-outline-primary"
                      :disabled="viewOnly"
                      type="button"
                      id="btn-addon1"
                      @click="showLookup=true"
                    >Lookup</button>
                </div>
                <div v-if="!v$.coffer.course.title.required && v$.coffer.course.title.$dirty" class="text-danger">Select the course</div>
              </div>
              <div class="col">
                <div>
                  <label for="st_dept">Offering Department</label>
                  <select class="form-select" id="st_dept" 
                    v-model="coffer.dept_name" :disabled="viewOnly">
                    <option
                      v-for="cs in SD.Departments"
                      v-bind:value="cs.id"
                      :key="cs.id"
                    >{{ cs.value }}</option>
                  </select>
                  <div v-if="!v$.coffer.dept_name.required && v$.coffer.dept_name.$dirty" class="text-danger">Select the dept.</div>
                </div>
              </div>
            </div>
            <div class="row mb-2">
              <div class="col">
                <label for="crs_status">Course Status</label>
                <select
                  class="form-select"
                  id="crs_status"
                  v-model.trim="coffer.status"
                  :disabled="true"
                >
                  <option
                    v-for="x in SD.OfferingStatuses"
                    v-bind:value="x.id"
                    :key="x.id"
                  >{{ x.value }}</option>
                </select>
                <div v-if="!v$.coffer.status.required && v$.coffer.status.$dirty" class="text-danger">Select status</div>
              </div>
              <div class="col">
                <label for="crs_sect">Section</label>
                <select
                  class="form-select"
                  id="crs_sect" required
                  v-model.trim="coffer.section"
                  :disabled="viewOnly"
                >
                   <option value="A">A</option>
                   <option value="B">B</option>
                   <option value="C">C</option>
                   <option value="D">D</option>
                   <option value="E">E</option>
                   <option value="F">F</option>
                   <option value="G">G</option>
                </select>
                <div v-if="!v$.coffer.section.required && v$.coffer.section.$dirty" class="text-danger">Select section</div>
              </div>
            </div>
            <div class="row mb-2">
              <div class="col">
                <span v-if="loaded">
                  <acad-session :acad_session="coffer.acad_session" 
                    :isEdit="isEdit" :disabled="viewOnly"
                    label="Academic Session"
                    v-on:update:acad_session='setAcadSession'/>
                  <div v-if="!v$.coffer.acad_session.required" class="text-danger">Enter session</div>
                  <div v-else-if="!v$.coffer.acad_session.validsession && v$.coffer.acad_session.$dirty" class="text-danger">Invalid session</div>
                </span>
              </div>
              <div class="col">
                <label for="crs_slot">Slot</label>
                <select
                  class="form-select"
                  id="crs_slot"
                  v-model.trim="coffer.slot"
                  :disabled="viewOnly"
                >
                  <option
                    v-for="x in SD.CourseSlots"
                    v-bind:value="x.id"
                    :key="x.id"
                  >{{ x.value }}</option>
                </select>
                <div v-if="!v$.coffer.slot.required && v$.coffer.slot.$dirty" class="text-danger">Select the slot</div>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="row" v-if="!viewOnly">
              <div class="col">
                <vue-bootstrap-typeahead
                      placeholder="Lookup instructor by name"
                      :data="instructors"
                      :serializer="s => (s.first_name + ' ' +s.last_name + ' ('+ s.dept_name+')')"
                      @mta-item-selected="onInstructorSelect"
                      @mta-input-changed="debouncedILQuery"
                    />
              </div>
            </div>
            <div class="row fw-bold bg-success p-2 text-dark bg-opacity-25">
              <div class="col-md-2">S#</div>
              <div class="col">Instructor</div>
              <div class="col-md-3">Is Coord.</div>
              <div class="col-md-2">Delete</div>
            </div>
            <div class="row" v-for="(ins, idx) in coffer.instructors" :key="ins.instructor">
              <div class="col-md-2">{{idx+1}}</div>
              <div class="col">{{ins.first_name + " " + ins.last_name}}</div>
              <div class="col-md-3">
                <input
                      class="form-check-input"
                      type="checkbox"
                      :disabled="viewOnly"
                      v-model="ins.is_coordinator"
                      @input="v$.coffer.instructors.$touch"
                    />
              </div>
              <div class="col-md-2">
                <input
                      class="form-check-input"
                      type="checkbox"
                      :disabled="viewOnly"
                      v-model="ins.is_deleted"
                    />
              </div>
            </div>
            <div v-if="!v$.coffer.instructors.isValid && v$.coffer.instructors.$dirty">
              <span class="text-danger">Please select instructor/coordinator.</span>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <span>Crediting Categorization</span>
            <span class="float-end">
              <button type="button" @click="addCourseCat" :disabled="viewOnly" class="btn btn-sm btn-outline-primary">Add</button>
            </span>
          </div>
          <div class="card-body">
            <div class="row hdr-row">
              <div class="col-md-2">Degree</div>
              <div class="col-md-3">Department</div>
              <div class="col-md-3">Category</div>
              <div class="col-md-3">For Entry Years</div>
              <div class="col-md-1">Delete</div>
            </div>
            <p v-if="coffer.course_categories.length == 0">Nothing added yet!</p>
            <div v-if="!v$.coffer.course_categories.validate" class="text-danger">All fields are required in a course category row!</div>
            <div class="row mb-2" v-for="r in coffer.course_categories" :key="r.id">
              <div class="col-md-2">
                <select class="form-select" :disabled="viewOnly"
                v-model.trim="r.degree">
                  <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
                    {{ cs.value }}
                  </option>
                </select>
              </div>
              <div class="col-md-3">
                <select class="form-select" v-model.trim="r.dept" :disabled="viewOnly">
                  <option v-for="cs in SD.Departments" v-bind:value="cs.id" :key="cs.id">
                    {{ cs.value }}
                  </option>
                </select>
              </div>
              <div class="col-md-3">
                <select :disabled="viewOnly" class="form-select" v-model.trim="r.category">
                  <option v-for="cs in SD.CourseTypes" v-bind:value="cs.id" :key="cs.id">
                    {{ cs.value }}
                  </option>
                </select>
              </div>
              <div class="col-md-3">
                <input :disabled="viewOnly" type="text" v-model.trim="r.for_entry_years"
                  placeholder="E.g. 2019,2020"/>
              </div>
              <div class="col-md-1">
                <input :disabled="viewOnly" type="checkbox" v-model="r.is_deleted"/>
              </div>
            </div>
          </div>
        </div>
        <div class="row mb-2" v-if="!viewOnly">
          <div class="col">
            <div class="btn-group mt-4">
              <div class="dropdown me-2">
                <button v-if="!isStudent && isEdit" type="button" 
                  class="btn btn-primary dropdown-toggle" data-bs-toggle="dropdown" 
                  aria-expanded="false">
                Change Status
                </button>
                <ul class="dropdown-menu">
                  <li v-for="act in actions" :key="act"><a class="dropdown-item" @click.prevent="onAction(act)">{{act.label}}</a>
                  </li>
                </ul>
              </div>
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
      <div v-if="loaded">
        <EnrolledStudents v-if="tab=='enrollments'" 
          v-bind:co_id="coffer.id"
          v-on:update-enrollments="loadEnrollments"
          v-bind:enrollments="coffer.enrollments"/>
      </div>
      <div v-else>Loading enrollments...</div>
      <div v-if="tab=='stats' && coffer.id">
        <p v-if="statsNotAvailable">
          Stats are not available!
        </p>
        <div class="row mb-2" v-else>
          <div class="col">
            <h5>Grades Distribution</h5>
            <p v-if="chartdataGrades.labels.length == 0">No grades data available yet!</p>
            <IChart chart-id="costCh3" chart-type="bar" chart-title="Grades awarded"
            :dataLabels="chartdataGrades.labels" :datasets="chartdataGrades.datasets" ></IChart>
          </div>
          <div class="col">
            <h5>Attendance Trend</h5>
            <p v-if="chartdataAtt.labels.length == 0">No attendance data available yet!</p>
            <IChart chart-id="attCh" chart-type="bar" chart-title="Attendance"
            :dataLabels="chartdataAtt.labels" :datasets="chartdataAtt.datasets" ></IChart>
          </div>
        </div>
      </div>
      <WorkflowNotes v-if="tab=='notes' && !isStudent" v-bind:ent_name="'offer'" v-bind:ent_key="coffer.id" />
    </div>
  </div>
</template>

<script>
import useVuelidate from '@vuelidate/core'
import { required } from '@vuelidate/validators'
import EnrolledStudents from "./EnrolledStudents.vue";
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import WorkflowNotes from "./WorkflowNotes.vue";
import AcadSession from "./AcadSession.vue";
import _ from "lodash";
import IChart from './IChart.vue';

export default {
  setup () {
    return { v$: useVuelidate() }
  },
  name: "CourseOfferingDetails",
  components: {
    VueBootstrapTypeahead: VueBootstrapTypeahead,
    EnrolledStudents: EnrolledStudents,
    WorkflowNotes :WorkflowNotes,
    AcadSession: AcadSession,
    IChart: IChart
  },
  data: function() {
    return {
      loaded: false,
      isOtherAcadSession: false,
      tab: "main",
      coffer: {
        acad_session: "",
        dept_name: "",
        course: {},
        status:"P",
        enrollments: [],
        instructors: [],
        course_categories: []
      },
      /**
       * Defines the allowed actions to each role. The key is
       * role and value is the action label and the status of
       * course that will be set when action is performed.
       */
      actionsMap: {
        "HOD": [{label: "Enrolling", status: "E"}, 
                {label: "Return to Faculty", status: "D"}],
        "DEA": [{label: "Enrolling", status: "E"},
                {label: "Running", status: "R"}, 
                {label: "Return to Dept.", status: "D"},
                {label: "Cancel", status: "C"}],
        "FAC": [{label: "Propose", status: "P"},
                {label: "Cancel", status: "C"}],
        "ACA": [{label: "Enrolling", status: "E"},
                {label: "Running", status: "R"}, 
                {label: "Return to Dept.", status: "D"},
                {label: "Cancel", status: "C"}],
      },
      instructors: [],
      courses: [],
      showLookup: false,
      chartdataGrades: {
        labels: [],
        datasets: [
          {
            label: "# of Students",
            data: [],
            backgroundColor: [],
            borderColor: [],
            borderWidth: 1
          }
        ]
      },
      chartdataAtt: {
        labels: [],
        datasets: [
          {
            label: "# of Students",
            data: [],
            backgroundColor: [],
            borderColor: [],
            borderWidth: 1
          }
        ]
      },
      chart_options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: {display: false},
        scales: {
          yAxes: [{
            scaleLabel: {
              display: true,
              labelString: 'Responses in %'
            },
            ticks: {
                beginAtZero: true
            }
          }]
        }
      }
    };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called: id=" + this.$route.params.id);
      return this.$route.params.id > 0;
    },
    actions() {
      return this.actionsMap[this.userRole];
    },
    nextAcadSessions() {
      return this.SD.AcademicSessions.map(x => x["value"]+" is "+x["id"]).join(", ");
    }
  },
  async beforeRouteUpdate(to, from, next) {
    console.log(
      "CourseOfferingDetails.beforeRouteUpdate: to=" +
        to.path +
        ". from=" +
        from.path
    );
    if (from.path.startsWith(to.path)) {
      this.reset();
    } else if (to.params.id) {
      await this.load();
    }
    next();
  },
  async created() {
    console.log("Creating Course Offering Details");
    // Alias 'this' for accessing in promises
    let vm = this;
    vm.courses = [];
    if (vm.isEdit) {
      await Promise.all(
          [vm.load(), vm.loadStats(), vm.loadEnrollments()]
        );
    } else {
      vm.reset();
    }
    vm.markViewOnly();
    vm.loaded = true;
  },
  methods: {
    async loadEnrollments() {
      console.log("Loading enrollments for the CO.");
      let vm = this;
      vm.loaded = false;
      let cid = vm.coffer.id || vm.$route.params.id;
      vm.user = this.currentUser;
      await vm.doHttp(true, `get_course_enrollments/${cid}`, null,
        (b)=>{vm.coffer.enrollments = b}, vm.setStatusMessage)
    },
    setAcadSession(acd) {
      this.coffer.acad_session=acd;
      this.v$.coffer.acad_session.$touch;
    },
    markViewOnly() {
      let vm = this;
      if (!vm.isEdit) {
        vm.viewOnly = false;
      } else if (vm.isStudent) {
        vm.viewOnly = true;
      } else if (vm.isAcad || vm.isDean) {
        vm.viewOnly = false;
      } else if (vm.coffer.status == 'F') {
        vm.viewOnly = true;
      } else if (vm.isFaculty && !vm.iAmCoordinator()) {
        vm.viewOnly = true;
      } else {
        vm.viewOnly = false;
      }
      console.log("ViewOnly="+vm.viewOnly);
    },
    async loadStats() {
      console.log(">>>> Loading the stats");
      let vm = this;
      let cid = vm.coffer.id || vm.$route.params.id;
      try {
        let res = await vm.$http.get("fetch_stats/" + cid);        
        if (res.data.status == "OK") {
          // Data and labels for grades chart
          vm.chartdataGrades.labels = res.data.body.grades;
          vm.chartdataGrades.datasets[0].data = res.data.body.data;
          
          // Data and labels for attendance chart
          vm.chartdataAtt.labels = res.data.body.Weeks;
          vm.chartdataAtt.datasets[0].data = res.data.body.data_att;
          
          vm.oldStatus = vm.coffer.status;
        } else {
          vm.statsNotAvailable = true;
        }
      } catch(error) {
          console.log(error);
          vm.setStatusMessage("Error: " + error);
      }
    },
    removeInstructor(ins) {
      ins.is_deleted = true;
    },
    onCourseSelect(c) {
      this.coffer.course = c;
      this.showLookup = false;
    },
    debouncedQuery: _.debounce(async function(inp) {
      await this.lookupCourse(inp)
    }, 400),
    async lookupCourse(query) {
      let vm = this;
      if (_.isEmpty(query) || query.length < 3) {
        console.log("Min. 3 charaters needed. Ignored.");
        return;
      }
      await vm.doHttp(true, `course_lookup/${query}`, null,
          (b)=>{vm.courses = b}, vm.setStatusMessage)
    },
    onInstructorSelect(c) {
      console.log("Selected instructor: " + JSON.stringify(c));
      let ins = { instructor: c.user_id, is_coordinator: false };
      Object.assign(ins, c);
      this.coffer.instructors.push(ins);
      console.log("Instructors: " + JSON.stringify(this.coffer.instructors));
    },
    debouncedILQuery: _.debounce(async function(inp) {
      await this.lookupInstructor(inp)
    }, 400),
    async lookupInstructor(query) {
      let vm = this;
      if (_.isEmpty(query) || query.length < 3) {
        console.log("Min. 3 charaters needed. Ignored.");
        return;
      }
      await vm.doHttp(true, `instructor_lookup/${query}`, null,
          (b)=>{vm.instructors = b}, vm.setStatusMessage)
    },
    iAmCoordinator() {
      const uid = this.currentUser.id;
      const instr = this.coffer.instructors || [];
      console.log("uid="+uid+". instr="+JSON.stringify(instr));
      const obj = instr.find(x => x.is_coordinator && x.user_id == uid);
      console.log("Found obj="+JSON.stringify(obj));
      return obj != undefined;
    },
    countCoordinator() {
      let noc = 0;
      for (var inst in this.coffer.instructors){
        if(this.coffer.instructors[inst].is_coordinator){
          noc += 1;
        }
      }
      return noc
    },
    async load() {
      console.log("Loading course offering details.");
      let vm = this;
      let cid = vm.coffer.id || vm.$route.params.id;
      try {
        let res = await vm.$http.get("co_view/" + cid);
        if (res.data.status == "OK") {
          vm.coffer = res.data.body;
          vm.oldStatus = vm.coffer.status;
        } else {
          vm.setStatusMessage(res.data.body);
        }
        vm.markViewOnly();
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error: " + error);
      }
    },
    async save() {
      let vm = this;
      //TODO: Check status and role before allowing save
      console.log('submit!');
      vm.v$.coffer.$touch();
      if (vm.v$.coffer.$invalid) {
        vm.setStatusMessage("Please correct the inputs first!");
        return;
      }
      else if (vm.coffer.course_categories.length == 0){
          vm.setStatusMessage("Please inputs atleast one Crediting Categorization details.");
      }
      else {
        if (!confirm("Confirm save?")) {
          vm.setStatusMessage("User canceled save!");
          return;
        }
        console.log("Saving course offering details.");
        try {
          let res = await vm.$http.post("co_save", vm.coffer);
          if (res.data.status == "OK") {
            vm.coffer = res.data.body;
            if (!vm.isEdit) {
              let v = `${vm.$route.path}/${vm.coffer.id}`;
              console.log("Loading CO view: " + v);
              vm.$router.push({ path: v });
            } else {
              vm.setStatusMessage("Saved successfully!");
            }
          } else {
            vm.setStatusMessage(res.data.body);
          }
        } catch(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        }
      }
    },
    reset() {
      this.coffer = { loaded: false, course: {},status:"P", 
          enrollments: [], acad_session: "",
          instructors: [], course_categories: [] };
      console.log("Clearing course offering details.");
    },
    getDate(){
      let date = new Date().toJSON().slice(0,10).replace(/-/g,'/');
      return date
    },
    async onAction(act) {
        let vm = this;
        console.log("Changing course offering status to: "+act.status);
        vm.coffer.status = act.status;
        await vm.save();
    },
    addCourseCat() {
      let vm = this;
      if (vm.coffer.course_categories == undefined) vm.coffer.course_categories = [];
      vm.coffer.course_categories.push({dept:"", degree:"", category:""});
    },
    getCourseLabel(s) {
      return s.code + ' :: ' +s.title + '(' + s.ltp + ')';
    }
  },
  validations() {
    const vm = this;
    return {
      coffer:{
        course:{
          title:{required},
        },
        section : {required},
        dept_name : {required},
        status:{required},
        slot:{required},
        acad_session: {
          required,
          validsession() {
            return vm.acadSessionRegExp.test(vm.coffer.acad_session);
          }
        },
        instructors:{
          isValid(){
            const a = vm.coffer.instructors.length
            const b = vm.countCoordinator()
            const xx = (b == 1 && a > 0)
            console.log(`Instructor validation: a=${a}, b=${b}, xx=${xx}`)
            return xx
          }
        },
        course_categories:{
          validate(){
            let valid = true;
            if (vm.coffer.course_categories != undefined) {
              vm.coffer.course_categories.forEach(cc => {
                // {dept:"", degree:"", category:""}
                if (cc.dept == undefined || cc.dept.length == 0) {
                  valid=false;
                }
                if (cc.degree == undefined || cc.degree.length == 0) {
                  valid=false;
                }
                if (cc.category == undefined || cc.category.length == 0) {
                  valid=false;
                }
                if (cc.for_entry_years == undefined || cc.for_entry_years.length == 0) {
                  valid=false;
                }
              });
            }
            return valid;
          }
        }
      }
    }
  }
};
</script>
