<!--
Component for showing the attendance for enrolled students in a course.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Find attendence</p>
     <div class="row mb-2">
        <div class="col-md-4">
          <label for="sbo">Show results:</label>
          <select class="form-select" id="sbo" v-model="searchBy" @change="load">
            <option value="DAY">Day-wise</option>
            <option value="STUDENT">Student-wise</option>
          </select>
        </div>
        <div class="col">
          <label for="codet">Course:</label>
          <select class="form-select" id="codet" v-model="co_id" @change="load">
            <option v-for="cs in RunningCourses" v-bind:value="cs.id"
              :key="cs.id">{{ cs.value }}</option>
          </select>
        </div>
        <div class="col-md-1">
          <button class="btn btn-outline-danger mt-4" @click="reset">Clear</button>
        </div>
    </div>
    <div v-if="searchBy=='DAY'" class="card">
        <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-2">S#</div>
          <div class="col-md-2">Date</div>
          <div class="col-md-4">Present</div>
          <div class="col-md-4">Absent</div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="attData.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in attData" :key="s.id">
          <div class="col-md-2">{{i+1}}</div>
          <div class="col-md-2">
            <a :href="'#/co.att/'+co_id+'/'+s.attend_dt">{{s.attend_dt}}</a>
          </div>
          <div class="col-md-4">{{s.present}}</div>
          <div class="col-md-4">{{s.total - s.present}}</div>
        </div>
      </div>
    </div>
    <div v-else class="card" style="padding: 10px">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Roll No.</div>
          <div class="col">Name</div>
          <div class="col-md-1">Enrol. Type</div>
          <div class="col" :disabled=1>Status</div>
          <div class="col-md-1">Attnd.</div>
          
        </div>
      </div>
      <div class="card-body">
        <p v-if="attData.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in attData" :key="s.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-2">
            <span v-if="!isStudent">
              <a :href="'#/std.detail/'+s.user_id">{{s.org_id}}</a>
            </span>
            <span v-else>{{s.org_id}}</span>
          </div>
          <div class="col">{{s.student}}</div>
          <div class="col-md-1">{{labelFor(SD.EnrolTypes, s.enrol_type)}}</div>
          <div class="col">
            {{labelFor(SD.EnrolStatuses, s.enrol_status)}}
          </div>
          <div class="col-md-1">
            <span v-if="s.attendance">
              <a v-if="!isStudent" :href="`#/att.detail/${s.id}`">{{s.attendance}}%</a>
            </span>
            <span v-else>--</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "AttendanceSearch",
  components: {
  },
  data: function() {
    return {
            searchBy: "DAY",
            attData: [],
            co_id: 0,
            RunningCourses: []
        };
  },
  async mounted() {
    console.log("Mounted AttendanceSearch");
    let vm = this
    await vm.doHttp(true, `running_courses`, null,
        (b)=>{vm.RunningCourses = b}, vm.setStatusMessage)
  },
  methods: {
    async load() {
      console.log("Loading attendance.");
      let vm = this;
      if (!vm.co_id) {
        vm.setStatusMessage("Please select a course!")
        return
      }
      vm.attData = []
      let url = `get_course_enrollments/${vm.co_id}`
      if (vm.searchBy == "DAY") {
        url = `daywise_att/${vm.co_id}`
      }
      await vm.doHttp(true, url, null, (b)=>{ vm.attData = b },
              vm.setStatusMessage)
    },
    reset() {
      this.searchBy="DAY"
      this.attData=[]
      this.co_id=0
    }
  }

};
</script>
