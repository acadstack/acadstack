<!--
Component for showing the slot-wise list of courses offered in an academic session.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h5>Slotwise Courses</h5>
    <div class="row mb-2">
        <div class="col float-start">
            <acad-session v-bind:acad_session="acad_session"
                label="Load for session"
                v-on:update:acad_session='onAcadSessionChange'/>
        </div>
    </div>
    <div class="row hdr-row border-info border-bottom">
        <div class="col-md-1">S#</div>
        <div class="col-md-6">Course (Code/Title/LTPCS)</div>
        <div class="col-md-5">Coordinator</div>
    </div>
    <p v-if="Object.keys(slots_data).length == 0">Nothing to show yet!</p>
    <div v-else class="card" v-for="(val, key) in slots_data" :key="key">
        <div class="card-header">Slot <span class="fw-bolder">{{labelFor(SD.CourseSlots, key)||key}}</span></div>
        <div class="card-body">
            <div class="row row-striped" v-for="(r, i) in val" :key="r">
                <div class="col-md-1">{{i+1}}</div>
                <div class="col-md-6">
                    <a :href="'#/co.detail/'+r.co_id">{{r.code}} : {{r.title}}</a>
                     ({{r.ltp}})
                </div>
                <div class="col-md-5">{{r.instructor}}</div>
            </div>
        </div>
    </div>
  </div>
  
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "SlotWiseCourses",
  components: {
    "AcadSession": AcadSession
  },
  data: function(){
      return{
          acad_session:"",
          slots_data: {}
      }
  },
  mounted() {
    if (sessionStorage.mySlotwiseCoff) {
        let x = JSON.parse(sessionStorage.mySlotwiseCoff);
        this.acad_session = x.acad_session;
        this.slots_data = x.slots_data;
    }
  },
  methods: {
    onAcadSessionChange(acs) {
        this.acad_session = acs;
        this.search();
    },
    search(){
        let vm = this;
        console.log("Loading slotwise courses");
        vm.$http
        .get("get_slotwise_courses/"+vm.acad_session)
        .then(function(res) {
                if (res.data.status == "OK") {
                    vm.slots_data = res.data.body;
                    let x = {"acad_session": vm.acad_session, "slots_data": vm.slots_data};
                    sessionStorage.mySlotwiseCoff = JSON.stringify(x);   
                } else {
                    vm.setStatusMessage(res.data.body);
                }
            }
        ).catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset(){
        this.acad_session = "";
        this.slots_data =  {};
        sessionStorage.mySlotwiseCoff = undefined;
    }
  },
};
</script>