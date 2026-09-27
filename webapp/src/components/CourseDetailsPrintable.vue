<!--
Component for showing printable details of a course.
 
@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Course Details</p>
      <div>
        <CourseMain v-bind:course="course" v-bind:ltpsc="ltpsc" 
        v-bind:error="v$" v-bind:print="true"/>
        <CourseModules v-bind:course="course"
         v-bind:print="true" v-bind:error="v$"/>
        <CourseTLP v-bind:course="course" v-bind:error="v$"
        v-bind:print="true"/>
        <CourseTKP v-bind:tkp="course.tkp" v-bind:error="v$"/>
        <CourseTGAP v-bind:tgap="course.tgap" v-bind:error="v$"/>
        <WorkflowNotes v-if="!isStudent" v-bind:ent_name="'course'"
        v-bind:print="true" v-bind:ent_key="course.id" />
      </div>
  </div>
</template>

<script>
import useVuelidate from '@vuelidate/core'
import { required } from '@vuelidate/validators'

import CourseTKP from "./CourseTKP.vue"
import CourseTGAP from "./CourseTGAP.vue"
import CourseMain from "./CourseMain.vue"
import CourseTLP from "./CourseTLP.vue"
import CourseModules from "./CourseModules.vue"
import WorkflowNotes from "./WorkflowNotes.vue";

export default {
  setup () {
    return { v$: useVuelidate() }
  },
  name: "CourseDetailsPrintable",
  components: {
    "CourseTKP": CourseTKP,
    "CourseTGAP": CourseTGAP,
    "CourseMain": CourseMain,
    "CourseTLP": CourseTLP,
    "CourseModules": CourseModules,
    "WorkflowNotes": WorkflowNotes
  },

  data: function() {
    return {
      ltpsc:{
        ltp:"",
        sc:""
      },
      course: {
              tkp:[], tgap:[], modules:{},
              learning:{}, evaluation: {}
              }
    };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("CourseDetailsPrintable.beforeRouteUpdate: to="+to.path+". from="+from.path);
    if (to.params.id) {
      this.course.id = to.params.id
      this.load();
    }
    next();
  },
  created: function() {
    console.log("Creating Course Details Printable");
    this.load();
  },
  methods: {
    load() {
      console.log("Loading course details.");
      let vm = this;
      let cid = vm.course.id || vm.$route.params.id
      vm.$http.get('cour/'+cid)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.course = res.data.body;
          var ltp = vm.course.ltp.split("-");
          vm.ltpsc.ltp = ltp[0]+'-'+ltp[1]+'-'+ltp[2];
          vm.ltpsc.sc = ltp[3]+'-'+ltp[4];
          vm.oldStatus = vm.course.status;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error: "+error);
      });
    }
  },
  validations() { 
    return {
      course: { 
          code: { required },
          evaluation: {}, teaching: {}, modules: {},
          title:{}, learning:{}, ref_material: {}, 
          tkp: {}, tgap: {} 
        } 
      }
  }
};
</script>
