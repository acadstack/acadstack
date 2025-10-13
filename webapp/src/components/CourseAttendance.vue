<!--
Component for showing the attendance records for a course on a date.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Attendance details for date: {{att_dt}}</p>
    <div class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Roll No.</div>
          <div class="col">Name</div>
          <div class="col-md-4">Present?</div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="data.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in data" :key="s.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-2">{{s.roll_no}}</div>
          <div class="col">{{s.name}}</div>
          <div class="col-md-2">{{s.attend == 'P' ? "Yes" : "No"}}
            &nbsp; [<a :href="`#/att.detail/${s.ce_id}`">Details</a>]
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseAttendance",

  data: function() {
    return {
      co_id: 0,
      att_dt: "",
      data: []
    };
  },
  computed: {
  },
  async mounted() {
    let vm = this;
    vm.co_id = vm.$route.params.co_id;
    vm.att_dt = vm.$route.params.att_dt;
    await vm.load()
  },
  methods: {
    async load() {
      console.log("Loading attendance details for course.");
      let vm = this;
      await vm.doHttp(true, `course_attd_on_date/${vm.co_id}/${vm.att_dt}`,
        null, (b)=>{vm.data = b}, vm.setStatusMessage)
    }
  }
};
</script>
