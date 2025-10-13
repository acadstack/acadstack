<!--
Component for main tab of the course details.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div class="card">
      <div class="card-body">
        <div class="row mb-2">
          <div class="col-sd-12 col-md-3">
            <label for="crs_code">Code</label>
            <input type="text" class="form-control" id="crs_code" v-model.trim="course.code" :disabled="viewOnly"/>
            <div v-if="!error.course.code.required && error.course.code.$dirty" class="text-danger">Enter code</div>
            <div v-else-if="!error.course.code.validcode && error.course.code.$dirty" class="text-danger">Invalid code</div>
          </div>
          <div class="col-sd-12 col-md-3">
            <label for="crs_title">Title</label>
            <input type="text" class="form-control" id="crs_title" v-model.trim="course.title" :disabled="viewOnly"/>
            <div v-if="error.course.title.$error && error.course.title.$dirty" class="text-danger">Enter title</div>
          </div>
          <div class="col-sd-12 col-md-3">
            <label for="crs_ltp">L-T-P</label>
            <div class="input-group">
              <input required type="text" class="form-control" id="crs_ltp" v-model.trim="ltpsc.ltp" :disabled="viewOnly" v-on:input="calcCredits"/>
              <div>
                <span v-if="ltpsc.sc" class="input-group-text">{{ltpsc.sc}}</span> 
                <span v-else class="input-group-text">s-c</span>
              </div>
            </div>
          </div>
        </div>
        <div class="row mb-2">
          <div class="col-sd-12 col-md-3">
            <label for="crs_status">Status</label>
            <select disabled="disabled" class="form-select" id="crs_status" v-model.trim="course.status">
              <option
                v-for="cs in SD.CourseStatuses"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
          <div class="col-sd-12 col-md-3">
            <label for="crs_freq">Frequency</label>
            <select class="form-select" id="crs_freq" v-model.trim="course.freq" :disabled="viewOnly">
              <option
                v-for="cs in SD.CourseFreqs"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
          <div class="col-sd-12 col-md-3">
            <label for="crs_lab">Has Lab</label>
            <input type="checkbox" class="form-check-input" id="crs_lab" v-model.trim="course.has_lab" :disabled="viewOnly"/>
          </div>
          <div class="col-sd-12 col-md-3">
            <label for="crs_vfac">Needs Visiting Fac.</label>
            <input
              type="checkbox"
              class="form-check-input"
              id="crs_vfac"
              v-model.trim="course.req_visiting_fac" :disabled="viewOnly"
            />
          </div>
        </div>
        <div class="row mb-2">
          <div class="col-sd-12 col-md-4">
            <label for="crs_pre">Prereqs</label>
            <input type="text" class="form-control" id="crs_pre" 
            v-model.trim="course.prereqs" :disabled="viewOnly"/>
          </div>
          <div class="col-sd-12 col-md-4">
              <label for="crs_sup">Supersedes</label>
              <input
                type="text"
                class="form-control"
                id="crs_sup"
                v-model.trim="course.course_supersedes"
                :disabled="viewOnly"
              />
          </div>
          <div class="col-sd-12 col-md-4">
            <label for="crs_ovr">Overlaps</label>
            <input
                type="text"
                class="form-control"
                id="crs_ovr"
                v-model.trim="course.course_overlaps"
                :disabled="viewOnly"
              />
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">Learning and Evaluation</div>
      <div class="card-body">
        <div class="row hdr-row">
          <div class="col">Planned learning experience (% hours)</div>
          <div class="col">Course Evaluation Plan (% weight)</div>
        </div>
        <div class="row mb-2">
          <div class="col">
            <div v-if="error.course.learning.$error && error.course.learning.$dirty" class="text-danger">Sum of Planned learning experience should be 100.</div>
            <div class="row mb-2" v-for="(w, i) in learning_items" :key="i">
              <label class="col-sm-7 col-form-label" v-bind:for="'ll'+i">
                {{w.label}}
              </label>
              <div class="col-sm-3">
                <input class="form-control" type="number" min="0" max="100" 
                v-model.trim="course.learning[w.id]" v-bind:id="'ll'+i" :disabled="viewOnly"/>
              </div>
            </div>
          </div>
          <div class="col">
            <div v-if="!error.course.evaluation.itemvalid && error.course.evaluation.$dirty" class="text-danger">Item under Course Evaluation Plan should not be more than 35.</div>
            <div v-else-if="!error.course.evaluation.ishun && error.course.evaluation.$dirty" class="text-danger">Sum of course evalution should be 100.</div>
            <div class="row mb-2" v-for="(w, i) in eval_items" :key="i">
              <label class="col-sm-7 col-form-label" v-bind:for="'ei'+i">
                {{w.label}}
              </label>
              <div class="col-sm-3">
                <input class="form-control" type="number" min="0" max="40" 
                v-model.trim="course.evaluation[w.id]" v-bind:id="'ei'+i" :disabled="viewOnly"/>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseMain",
  props: ["course","error","ltpsc"],
  data: function() {
        return {
      // TODO: Put these as static data
      eval_items :[
        {id:"hwa", label: "Homework/Assignments"},
        {id:"qui", label: "Quizzes"},
        {id:"mle", label: "Mid-sem Lab Exam/Report/Viva"},
        {id:"mse", label: "Mid-Sem Written Exam"},
        {id:"ele", label: "End-sem Lab Exam/Report/Viva"},
        {id:"ese", label: "End-Sem Written Exam"},
        {id:"hop", label: "Hands-on Project"},
        {id:"rsp", label: "Research Project"},
        {id:"pre", label: "Presentation"},
        {id:"oth", label: "Others"}
      ],
      learning_items : [
        {id:"bla", label: "Black Board"},
        {id:"pro", label: "Project-based Learning"},
        {id:"ppt", label: "Slides/PPT"},
        {id:"dra", label: "Drawing Board"},
        {id:"des", label: "Desktop Computer"},
        {id:"lab", label: "Laboratory Equipments"},
        {id:"ind", label: "Industrial Visits"},
        {id:"gue", label: "Guest Lectures"}
      ]
    };
  },
  created: function() {
    let vm = this;
    console.log("Creating CourseMain: "+JSON.stringify(vm.course));
    vm.viewOnly = vm.isStudent;
    if (vm.course.evaluation == undefined) {
      vm.$set(vm.course, "evaluation", {});
      for (let k of vm.eval_items) {
        vm.course.evaluation[k.id] = "0";
      }
      console.log("evaluation set to: "+JSON.stringify(vm.course.evaluation));
    }
    if (vm.course.learning == undefined) {
      vm.$set(vm.course, "learning", {});
      for (let k of vm.learning_items) {
        vm.course.learning[k.id] = "0";
      }
      console.log("learning set to: "+JSON.stringify(vm.course.learning));
    }
  },
  methods: {
    _tryParseNum(n) {
      try {
        const re = RegExp("^[-+]?\\d+[./]?\\d*$", "i");
        if (re.test(n)) {
          let x = eval(n);
          return Number.isInteger(x) ? x : x.toFixed(2);
        } else {
          console.error(`Cannot parse ${n} as number.`);
          return n;
        }
      } catch (err) {
        console.error(`Cannot parse ${n} as number. ${err}`);
        return 0;
      }
    },

    calcCredits(){
      var vm = this;
      let ltp = vm.ltpsc.ltp.split("-");
      let L = vm._tryParseNum(ltp[0]);
      let T = vm._tryParseNum(ltp[1]);
      let P = vm._tryParseNum(ltp[2]);
      let S = 2*L - T + P/2;
      S = S.toFixed(2);
      let C = L + P/2;
      C = C.toFixed(2);
      vm.course.ltp = `${L}-${T}-${P}-${S}-${C}`;
      vm.ltpsc.sc = `${S}-${C}`;
    }
  }
};
</script>

