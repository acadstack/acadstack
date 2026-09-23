<!--
Component for showing and editing the details of a course.
We show the course details under different tabs, each of which
is implemented in a separate component.
 
@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Course Details</p>
    <div v-if="notFound" class="alert alert-danger" role="alert">
      Could not find course details!
    </div>
    <form v-else>
      <div class="clearfix">
        <div class="float-start">
          <ul class="nav nav-tabs">
            <li class="nav-item">
              <a class="nav-link" v-bind:class="{'bg-danger':(v$.course.code.$error||v$.course.title.$error||v$.course.learning.$error||v$.course.evaluation.$error) , active: tab === 'main'}"   @click="tab='main'">Main</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" v-bind:class="{'bg-danger':v$.course.modules.$error, active: tab === 'mod'}" @click="tab='mod'">Modules</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" v-bind:class="{'bg-danger':(v$.course.ref_material.$error || v$.course.teaching.$error) , active: tab === 'tlp'}" @click="tab='tlp'">Teaching/Learning Plan</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" v-bind:class="{'bg-danger':v$.course.tkp.$error , active: tab === 'tkp'}" @click="tab='tkp'">TKP</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" v-bind:class="{'bg-danger':v$.course.tgap.$error , active: tab === 'tgap'}" @click="tab='tgap'">TGAP</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" :class="{active: tab === 'offerings'}" @click="tab='offerings'">Offerings</a>
            </li>
            <li class="nav-item" v-if="!isStudent">
              <a class="nav-link" :class="{active: tab === 'notes'}" @click="tab='notes'">Notes</a>
            </li>
          </ul>
        </div>
        <div class="float-end" v-if="!isStudent">
          <div class="btn-group me-2">
            <div class="dropdown">
              <button type="button" class="btn btn-primary dropdown-toggle"
                data-bs-toggle="dropdown" aria-expanded="false">
                Action
              </button>
              <div class="dropdown-menu">
                <a class="dropdown-item" @click.prevent="onAction(act)"
                  v-for="act in actions" :key="act">{{act.label}}</a>
              </div>
            </div>
            <button class="btn btn-outline-success me-2" type="button" @click="save">
              Save
              <i class="bi bi-save"></i>
            </button>
            <a class="btn btn-outline-primary" :href="'#/cour.print/'+course.id">Print</a>
          </div>
        </div>
      </div>
      <div>
        <CourseMain v-if="tab=='main'" v-bind:course="course" v-bind:ltpsc="ltpsc" v-bind:error="v$"/>
        <CourseModules v-if="tab=='mod'" v-bind:course="course" v-bind:error="v$"/>
        <CourseTLP v-if="tab=='tlp'" v-bind:course="course" v-bind:error="v$"/>
        <CourseTKP v-if="tab=='tkp'" v-bind:tkp="course.tkp" v-bind:error="v$"/>
        <CourseTGAP v-if="tab=='tgap'" v-bind:tgap="course.tgap" v-bind:error="v$"/>
        <CourseOfferings v-if="tab=='offerings'" v-bind:cid="course.id" />
        <WorkflowNotes v-if="tab=='notes' && !isStudent" v-bind:ent_name="'course'" v-bind:ent_key="course.id" />
      </div>
    </form>
  </div>
</template>

<script>
import useVuelidate from '@vuelidate/core'
import { required } from '@vuelidate/validators'
import CourseOfferings from "./CourseOfferings.vue"
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
  name: "CourseDetails",
  components: {
    "CourseOfferings": CourseOfferings,
    "CourseTKP": CourseTKP,
    "CourseTGAP": CourseTGAP,
    "CourseMain": CourseMain,
    "CourseTLP": CourseTLP,
    "CourseModules": CourseModules,
    "WorkflowNotes": WorkflowNotes
  },

  data: function() {
    return {
      notFound: false,
      tab:"main", currentTabComponent: "CourseTGAP",
      ltpsc:{
        ltp:"",
        sc:""
      },
      course: {
              tkp:[], tgap:[], modules:{}, ref_material: [],
              learning:{}, evaluation: {}, teaching: []
              },
      /**
       * Status-changing moves the user may make on this course, from the
       * server's "course" workflow table (see api_service/domain/course.py).
       */
      actions: []
    };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called: id="+this.$route.params.id)
      return this.$route.params.id > 0;
    }
  },
  async beforeRouteUpdate(to, from, next) {
    console.log("CourseDetails.beforeRouteUpdate: to="+to.path+". from="+from.path);
    if (to.params.id) {
      this.course.id = to.params.id
      await this.load();
    } else if (from.path.startsWith(to.path)) {
      this.reset();
    }
    next();
  },
  async created() {
    console.log("Creating Course Details");
    // Alias 'this' for accessing in promises
    let vm = this;
    if (vm.isEdit) {
      await vm.load();
    } else {
      vm.reset();
      await vm.loadActions();
    }
  },
  methods: {
    async load() {
      console.log("Loading course details.");
      let vm = this;
      let cid = vm.course.id || vm.$route.params.id
      try {
        let res = await vm.$http.get('cour/'+cid);
        if (res.data.status == "OK") {
          vm.course = res.data.body;
          var ltp = vm.course.ltp.split("-");
          vm.ltpsc.ltp = ltp[0]+'-'+ltp[1]+'-'+ltp[2];
          vm.ltpsc.sc = ltp[3]+'-'+ltp[4];
          vm.oldStatus = vm.course.status;
          await vm.loadActions();
        } else {
          vm.notFound = true;
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error: "+error);
        vm.notFound = true;
      }
    },
    async save() {
      let vm = this;
      vm.v$.$touch()
      if (!(vm.isAcad || vm.isDean) && vm.v$.$invalid) {
        return;
      }
      else {
        if (!confirm("Confirm save?")) {
          vm.setStatusMessage("User canceled save!");
          return;
        }
        console.log("Saving course details.");
        try {
          let res = await vm.$http.post('cour_save', vm.course);
          if (res.data.status == "OK") {
            vm.course = res.data.body;
            vm.oldStatus = vm.course.status;
            await vm.loadActions();
            if (!vm.isEdit) {
              let v = `${vm.$route.path}/${vm.course.id}`;
              console.log("Loading view: "+v);
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
      this.course = {
        tkp:[], tgap:[], modules:[],ref_material:[],
        learning:{}, evaluation: {}, teaching: []
        };
      console.log("Clearing course details.");
    },
    async loadActions() {
      let vm = this;
      await vm.doHttp(true, `workflow_actions/course/${vm.course.id || 0}`, null,
        (b)=>{ vm.actions = b.filter((a) => a.changes_status); },
        vm.setStatusMessage);
    },
    async onAction(act) {
      // Whether this user may make the move is the server's call (the
      // "course" workflow table); it only offers moves it will accept.
      let vm = this;
      vm.course.status = act.to_status;
      await vm.save();
    }
  },
  validations() {
    return {
      course:{
        code:{
          required,
          validcode(){
            var vm = this;
            if ("code" in vm.course)
            {
              var checkCode = new RegExp("^[A-Z][A-Z][1-9][0-9][0-9][A-Z]?$", "i"); 
              if (!checkCode.test(vm.course.code)){
                  return false;
              }
            }
            return true;
          }
        },
        title:{
          required
        },
        learning:{
          ishun(){
            var vm = this;
            var plannedLearning = 0;
            var count = 0;
            for (var x in vm.course.learning){
              if(vm.course.learning[x] != undefined){
                plannedLearning += parseInt(vm.course.learning[x]);
                count++;
              }
              else{
                vm.$delete(vm.course.learning,x);
              }
            }
            
            if ((vm.course.status && !( vm.course.status=='DRA' && count == 0) && plannedLearning != 100)||(count && plannedLearning != 100)){
                return false;
            }
            return true;
          }
        },
        evaluation:{
          itemvalid(){
            /*
            var vm = this;
            for (var x in vm.course.evaluation){
              if(vm.course.evaluation[x].length){
                if (parseInt(vm.course.evaluation[x]) > 35){
                    return false
                }
              }
              else{
                vm.$delete(vm.course.evaluation,x);
              }
            }*/
            return true;
          },
          ishun(){
            var vm = this;
            var courseEvalution = 0;
            var count = 0;
            for (var x in vm.course.evaluation){
              if(vm.course.evaluation[x].length!=0){
                count++;
                courseEvalution += parseInt(vm.course.evaluation[x]);
              }
              else{
                vm.$delete(vm.course.evaluation,x);
              }
            }
            
            if ((vm.course.status && !(vm.course.status=='DRA' && count == 0) && courseEvalution != 100)||(count && courseEvalution != 100)){
                return false;
            }
            return true;
          }
        },
        modules:{
          notempty(){
            var vm = this;
            if (vm.course.status && vm.course.status!='DRA' && (!("modules" in vm.course)||(vm.course.modules.length) == 0)){
                return false;
            }
            return true;
          },
          itemnotempty(){
            var vm = this;
            if(("modules" in vm.course)&&(vm.course.modules.length)){
                for (var x in this.course.modules){
                  var size = 0;
                  for (var y in this.course.modules[x]){
                    size++;
                    if(this.course.modules[x][y].length == 0){
                      return false;
                    }
                  }
                  if(size!=3){
                    return false;
                  }
                }
            }
            return true;
          }
        },
        ref_material:{
          notempty(){
            var vm = this;
            if (vm.course.status && vm.course.status!='DRA' && (!("ref_material" in vm.course)||(vm.course.ref_material.length) == 0)){
                return false;
            }
            return true;
          },
          itemnotempty(){
            var vm = this;
            if(("ref_material" in vm.course)&&(vm.course.ref_material.length)){
                for (var x in this.course.ref_material){
                  var size = 0;
                  for (var y in this.course.ref_material[x]){
                    size++;
                    if(this.course.ref_material[x][y].length == 0){
                      return false;
                    }
                  }
                  if(size!=2){
                    return false;
                  }
                }
            }
            return true;
          }
        },
        teaching:{
          notempty(){
            var vm = this;
            if (vm.course.status && vm.course.status!='DRA' && (!("teaching" in vm.course)||(vm.course.teaching.length) == 0)){
              return false;
            }
            return true;
          },
          itemnotempty(){
            var vm = this;
            if(("teaching" in vm.course)&&(vm.course.teaching.length)){
                for (var x in this.course.teaching){
                  var size = 0;
                  for (var y in this.course.teaching[x]){
                    size++;
                    if(this.course.teaching[x][y].length == 0){
                      return false;
                    }
                  }
                  if(size!=2){
                    return false;
                  }
                }
            }
            return true;
          }
        },
        tkp:{
          counttkp(){
            var vm = this;
            var notkp = 0
            for (var x in vm.course.tkp){
                if (vm.course.tkp[x]){
                    notkp += 1;
                }
            }
            if (vm.course.status && vm.course.status!='DRA' && notkp < 2){
                return false;
            }
            return true;
          }
        },
        tgap:{
          counttgap(){
            var vm = this;
            var notgap = 0
            for (var x in vm.course.tgap){
                if (vm.course.tgap[x]==true){
                    notgap += 1
                }
            }
            if (vm.course.status && vm.course.status!='DRA' && notgap < 2){
                return false;
            }
            return true;
          }
        }
      },
      ltpsc:{
        ltp:{
            required
        }
      }
    }
  }
};
</script>
