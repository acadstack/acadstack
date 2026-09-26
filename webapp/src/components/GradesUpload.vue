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
                  :href="`download_enrollments_for_grades/${formData.course_offering}`">
                  Download Enrolled Students List
                </a>
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
            <div class="card-body">
              <div class="row hdr-row border-bottom border-success">
                <div class="col-md-2">Row#</div>
                <div class="col-md-3">Col. #1</div>
                <div class="col-md-2">Col. #2</div>
                <div class="col-md-3">Col. #3</div>
                <div class="col-md-2">Col. #4</div>
              </div>
              <p v-if="result.length == 0">Nothing to show yet!</p>
              <div class="row row-striped" v-for="(r, idx) in result" :key="idx"
                :class="{ 'text-danger': !is_valid_grade(r.grade) && idx > 0 }">
                <div class="col-md-2">{{idx+1}}</div>
                <div class="col-md-3">{{r.first_name}}</div>
                <div class="col-md-2">{{r.last_name}}</div>
                <div class="col-md-3">{{r.roll_no}}</div>
                <div class="col-md-2">{{r.grade}}</div>
              </div>
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
      result: []
    };
  },
  methods: {
    is_valid_grade(gr) {
      let vg = this.SD.CourseGrades.map(g => g.id).filter(id => id);
      return !_.isEmpty(gr) && vg.includes(gr.toUpperCase().trim());
    },
    fileUploaded(resBody) {
      this.setStatusMessage(resBody);
    },
    onCourseSelect(c) {
      this.formData.course_offering = c.id;
      console.log("Selected course: " + JSON.stringify(c));
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
          if (!_.isEmpty(row)) {
            let cols = row.split(",");
            data.push({ 
              first_name: cols[0], last_name: cols[1],
              roll_no: cols[2], grade: cols[3] });
          }
        });
        vm.result = data;
      };
      reader.readAsText(file);
    }
  }
};
</script>
