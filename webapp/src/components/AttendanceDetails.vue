<!--
Component for showing the attendance records of a student in a
specific course in which he/she is enrolled.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p
      class="h6"
    >Attendance details for {{attend.rollNo}} in course {{attend.course}} in {{attend.session}}</p>
    <form>
      <div class="card">
        <div class="card-header">
          <div class="row hdr-row">
            <div class="col-md-1">S#</div>
            <div class="col">Lecture/lab date</div>
            <div class="col">Attendance</div>
            <div class="col">Photos</div>
            <div class="col">Remarks</div>
          </div>
        </div>
        <div class="card-body">
          <p v-if="attend.records.length == 0">Nothing to show yet!</p>
          <div class="row row-striped" v-for="(s, i) in attend.records" :key="s.id">
            <div class="col-md-1">{{i+1}}</div>
            <div class="col">{{s.lectureDate}}</div>
            <div class="col">{{s.attendance}}</div>
            <div class="col">
              <span v-if="s.photos.length == 0">No classroom photos.</span>
              <span class="me-1" v-for="(ph, ii) in s.photos" :key="ph">
                [<a :href="'get_class_photo/'+ph+'/'+attend.user_id" target="_blank">Photo-{{ii}}</a>]
                <!-- [<a :href="'get_image/'+ph" target="_blank">Photo-{{ii}}</a>] -->
              </span>
            </div>
            <div class="col">{{s.remarks}}</div>
          </div>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  name: "AttendanceDetails",

  data: function() {
    return { attend: {records:[]} };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called: id=" + this.$route.params.id);
      return this.$route.params.id > 0;
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log(
      "AttendanceDetails.beforeRouteUpdate: to=" +
        to.path +
        ". from=" +
        from.path
    );
    if (from.path.startsWith(to.path)) {
      this.reset();
    } else if (to.params.id) {
      this.load();
    }
    next();
  },
  created: function() {
    console.log("Creating Course Details");
    //console.log("cid "+this.$route.params.id)
    // Alias 'this' for accessing in promises
    let vm = this;
    if (vm.isEdit) {
      vm.load();
    } else {
      vm.reset();
    }
  },
  methods: {
    load() {
      console.log("Loading Attendance details.");
      
      let vm = this;
      let cid = vm.$route.params.id;
      vm.$http
        .get("get_student_att_details/" + cid)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.attend = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error: " + error);
        });
    },
    save() {
      //TODO:
      console.log("Saving Attendance details.");
    },
    reset() {
      //TODO:
      this.attend = {records:[]} ;
      console.log("Clearing Attendance details.");
    }
  }
};
</script>
