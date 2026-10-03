<!--
Component for uploading grades of a course.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Upload Course Grades</p>
    <acad-session label="For academic session"
      v-bind:acad_session="acad_session"
      v-on:update:acad_session='acad_session=$event'/>
    <p v-if="!acad_session">Please select an academic session to proceed</p>
    <p v-else-if="!isGradeSubOpen(acad_session)" 
      class="text-dark alert alert-warning text-center">
      <b>Grade uploading for {{acad_session}} is not open at this time.
      Please contact the academic section for further details.</b>
    </p>
    <div v-else>
      <div class="row mb-2">
        <div class="col">
          <form @submit.prevent="save">
            <div class="row mb-2">
              <div class="col">
                <vue-bootstrap-typeahead
                  placeholder="Course name or code. Type atleast 3 characters."
                  :data="courses"
                  :serializer="s => get_course_label(s)"
                  @mta-item-selected="onCourseSelect"
                  @mta-input-changed="debouncedQuery"
                />
              </div>
              <div class="col-md-4">
                <a class="btn btn-outline-primary"
                  :class="{disabled: (formData.course_offering == undefined)}"
                  :href="`download_enrollments_for_grades/${formData.course_offering}?components=${selected.join(',')}`">
                  Download Enrolled Students List
                </a>
              </div>
            </div>
            <div class="row mb-2" v-if="formData.course_offering">
              <div class="col">
                <span class="me-2">Scores (0-100) of evaluation components in the file:</span>
                <span v-if="!componentsSaved">None defined yet. Set them in the
                  <b>Main</b> tab of <b>Course Offering Details</b>.</span>
                <div v-else class="form-check form-check-inline" v-for="c in components" :key="c.code">
                  <input class="form-check-input" type="checkbox" :id="'ec-'+c.code"
                    :value="c.code" v-model="selected"/>
                  <label class="form-check-label" :for="'ec-'+c.code">{{c.label}} ({{c.code}})</label>
                </div>
              </div>
            </div>
            <div class="row mb-2">
              <div class="col mt-1">
                <FileUploader destination="grades_upload"
                file_key="grades_file"
                save_button_label="Submit Grades"
                v-bind:upload_form_data="formData"
                v-on:fu-file-reset="reset"
                v-on:fu-file-selected="file_selected"
                v-on:fu-file-uploaded="fileUploaded"
                />
              </div>
            </div>
          </form>
          <div class="card mt-2">
            <div class="card-header">GENERAL INSTRUCTIONS</div>
            <div class="card-body">
              <ul>
                <li>Please upload grades in CSV format only (CSV file can be downloaded 
                  from the grade submission page on AcadStack portal)</li>
                <li>The downloaded CSV file contains the list of enrolled students.</li>
                <li>The CSV file has the Header (i.e., first) row as: 
                  <b>FIRST_NAME, LAST_NAME, ROLL_NO, GRADE</b></li>
                <li>To upload scores of evaluation components too, tick the components
                  before downloading the list: it then has a column per component, named
                  by its code. Write each score scaled to 0-100; a blank cell keeps the
                  stored score.</li>
                <li>Write your grades in the downloaded CSV file and upload in Grade 
                  submission page on AcadStack portal.</li>
                <li>A preview of the uploaded grades is shown on the right side for 
                  quick reference and verification.</li>
                <li>Once grades are verified from the preview screen, for submitting 
                  the grades click on <b>Submit Grades</b> button.</li>
                <li>After submission the grades can be downloaded from the <b>Download 
                  Grades</b> menu item, which is on the right side of the 
                  <b>Enrolments</b> tab in <b>Course Offering Details</b> screen.</li>
              </ul>
              <b class="text-danger">!!! Additional Instructions Specific to This Session</b>
              <iframe width="500" height="400" src="https://docs.google.com/document/d/e/2PACX-1vS8TGuOQnMlNSijox2rN8SSIWtIPdIv3l-I2kLqE5V2Rv4bvb9GLsvWP99enxdbExFPIPiHVqEiIpoC/pub?embedded=true"></iframe>
            </div>
          </div>
        </div>
        <div class="col">
          <div class="card">
            <div class="card-header">Contents of the selected file are shown below. 
              Please check before submitting.
              Columns of the first row MUST be <b>FIRST_NAME, LAST_NAME, ROLL_NO, GRADE</b>
              <p>Red rows indicate invalid grade.</p>
            </div>
            <div class="card-body table-responsive">
              <p v-if="result.length == 0">Nothing to show yet!</p>
              <table v-else class="table table-sm table-striped">
                <thead>
                  <tr>
                    <th>Row#</th>
                    <th v-for="(h, i) in result[0]" :key="i">{{h}}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, idx) in result.slice(1)" :key="idx"
                    :class="{ 'text-danger': !is_valid_grade(r[3]) }">
                    <td>{{idx+2}}</td>
                    <td v-for="(v, i) in r" :key="i"
                      :class="{ 'text-danger fw-bold': scoreCols.includes(i) && !is_valid_score(v) }">{{v}}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import AcadSession from "./AcadSession.vue";
import _ from "lodash";

export default {
  name: "GradesUpload",
  components: {
    "VueBootstrapTypeahead": VueBootstrapTypeahead,
    "FileUploader": FileUploader,
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      acad_session: "",
      courses: [],
      formData: {},
      result: [],
      components: [],
      componentsSaved: false,
      selected: []
    };
  },
  computed: {
    // Indexes of the selected components' columns in the file's header row
    scoreCols() {
      const hdr = (this.result[0] || []).map(h => h.trim().toUpperCase());
      return this.selected.map(c => hdr.indexOf(c)).filter(i => i >= 0);
    }
  },
  watch: {
    selected(codes) {
      this.formData.components = codes.join(",");
    }
  },
  methods: {
    is_valid_score(v) {
      const s = (v || "").trim();
      return s === "" || (!isNaN(s) && Number(s) >= 0 && Number(s) <= 100);
    },
    is_valid_grade(gr) {
      // The grades of the configured grading schemes (the first entry is "-Select-")
      return !_.isEmpty(gr) &&
        this.SD.CourseGrades.some(g => g.id && g.id === gr.toUpperCase().trim());
    },
    fileUploaded(resBody) {
      this.setStatusMessage(resBody);
    },
    onCourseSelect(c) {
      let vm = this;
      vm.formData.course_offering = c.id;
      vm.selected = [];
      vm.components = [];
      vm.componentsSaved = false;
      console.log("Selected course: " + JSON.stringify(c));
      vm.doHttp(true, `eval_components/${c.id}`, null,
        (b) => { vm.components = b.components; vm.componentsSaved = b.saved; },
        vm.setStatusMessage);
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
      await vm.doHttp(true, `co_lookup/${query}`, null,
        (b)=>{vm.courses = b}, vm.setStatusMessage)
    },
    
    reset() {
      this.acad_session = "";
      this.formData = {};
      this.result = [];
      this.components = [];
      this.componentsSaved = false;
      this.selected = [];
      this.courseLookupQuery = "";
      this.courses = [];
      console.log("Clearing upload.");
    },
    file_selected(file) {
      let vm = this;
      if (!file) {
        console.log("No CSV file selected.");
        return;
      }
      const reader = new FileReader();
      reader.onload = function(evt) {
        let data = [];
        let rr = evt.target.result.split("\n");
        rr.forEach(row => {
          if (!_.isEmpty(row.trim())) {
            data.push(row.replace("\r", "").split(","));
          }
        });
        vm.result = data;
      };
      reader.readAsText(file);
    }
  }
};
</script>
