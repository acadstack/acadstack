<!--
Component for Creating Course Instructor's Feedback Form.
-->
<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h4>Course Instructor Feedback</h4>
      </div>
      <div class="card-body">
        <div>
          <b>Please note the follwing before submitting:</b>
          <ul>
            <li>All fields marked with a '*' are mandatory.</li>
            <li>Feedback for one course instructor can be submitted only once.</li>
            <li>When there are more than one instructors teaching a course, please choose only those instructors (one at a time) whose classes your attended.</li>
            <li>ALL feedback is anonymous.</li>
          </ul>
          <hr/>
        </div>
        <div class="row align-items-center mb-2">
          <div class="col-md-2">
            <label for="fb_type">* Feedback type</label>
            <select class="form-select" id="fb_type" v-model="fb_form_type"
            @change="getForm">
              <option value="">--Select--</option>
              <option value="MID_SEM_FB">Mid-sem</option>
              <option value="END_SEM_FB">End-sem</option>
            </select>
          </div>
          <div class="col-md-10">
            <label for="coe_type">* Select the course instructor</label>
            <select class="form-select" id="coe_type" v-model="enrol_instr"
              @change="resetAnswers">
              <option
                v-for="x in enrolments"
                v-bind:value="x"
                :key="x.enrolment_id"
              >
                {{ x.label }}
              </option>
            </select>
          </div>
        </div>
        <div v-if="enrolments.length > 0">
          <p v-if="Object.keys(form).length == 0">Please select a form type!</p>
          <div v-else class="card">
            <form id="theform" ref="theForm">
              <div class="card-body">
                <div class="row mb-2" v-for="(x, i) in form.form_questions" :key="x.id">
                  <div class="col">
                    <div class="row mb-2">
                      <div class="col"><span v-if="!x.is_optional">*</span>{{ i + 1 }}: {{x.question}}</div>
                    </div>
                    <div class="row mb-2" v-if="x.is_text">
                      <textarea rows="2" v-model.trim="x.answer"></textarea>
                    </div>
                    <ul v-else>
                      <li v-for="(y, j) in x.ans_options.split(',')" :key="i+'-'+j">
                        {{y}}
                        <input :name="i+'_'+j" :id="i+'-'+j" v-if="x.is_multianswer" type="checkbox"
                          :value="y" v-model="x.answer"/>
                        <input :name="i" :id="i+'_'+j" v-else type="radio" :value="y"
                          v-model="x.answer"/>
                      </li>
                    </ul>
                  </div>
                </div>
                <div class="row mt-2">
                  <div class="col">
                    <button type="button" class="btn btn-outline-primary" @click="save">Submit</button>
                  </div>
                  <div class="col">
                    <button type="reset" class="btn btn-outline-danger" @click="clear">Clear</button>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseInstructorFeedback",
  data: function () {
    return {
      fb_form_type: "",
      enrol_instr: {},
      enrolments: [],
      form: {},
      feedback: {}
    };
  },
  created: function () {
    console.log("Created CourseInstructorFeedback");
  },
  methods: {
    getEnrolments() {
      let vm = this;
      console.log("Getting enrolments.")
      return vm.$http
        .get(`student_enrolments_for_fb/${vm.form.form_type}`)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.enrolments = res.data.body;
            if (vm.enrolments.length == 0) {
              vm.setStatusMessage("You do not seem to have any pending feedback!");
            }
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    resetAnswers() {
      console.log("Resetting all answers.");
      if (this.$refs.theForm != undefined) {
        this.$refs.theForm.reset();
      }
    },
    getForm() {
      let vm = this;
      if (vm.fb_form_type == "") {
        vm.form = {};
        return;
      }
      console.log("Fetching currently open feedback form.")
      return vm.$http
        .get(`get_active_feedback_form/${vm.fb_form_type}`)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.form = res.data.body;
            vm.resetAnswers();
            vm.getEnrolments();
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    save() {
      let vm = this;
      let missing_answers = vm.form.form_questions.some(q => !q.is_optional && q.answer == "");
      if (missing_answers) {
        vm.setStatusMessage("Please answer all required questions!");
        return;
      } else if (!vm.enrol_instr || !vm.enrol_instr.course_instructor_id) {
        vm.setStatusMessage("Please select an instructor!");
        return;
      }
      if (!confirm("Confirm feedback submission?")) {
        return;
      }
      let reqData = {
        enrolment_id: vm.enrol_instr.enrolment_id,
        ci_id: vm.enrol_instr.course_instructor_id,
        form: vm.form
        }
      console.log(JSON.stringify(reqData));
      vm.$http
        .post("save_course_instructor_feedback", reqData)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.setStatusMessage(res.data.body);
            vm.clear();
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    async clear() {
      let vm = this;
      vm.fb_form_type = "";
      vm.form = {};
      vm.enrol_instr = {};
    },
  },
};
</script>
