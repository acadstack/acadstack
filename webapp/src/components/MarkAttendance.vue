<!--
Component for marking attendence by uploading the class photo.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Upload Group Photo</p>
    <p>Please upload a photo in JPG format only.</p>
    <form @submit.prevent="save">
      <div class="row mb-2">
        <div class="col-md-6">
          <label for="codet">Course:</label>
          <select class="form-select" id="codet" required
                v-model="kface.course_offering">
            <option v-for="cs in RunningCourses" v-bind:value="cs.id"
              :key="cs.id">{{ cs.value }}</option>
          </select>
        </div>
        <div class="col">
          <div>
            <label for="uploadFile">Photo:</label>
            <input id="uploadFile" class="form-control" type="file" @change="handleFile" multiple="multiple"/>
          </div>
        </div>
      </div>
      <div class="row mb-2">
        <div class="col">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit">
              Check
              <i class="bi bi-save"></i>
            </button>
            <button class="btn btn-outline-danger" @click="reset" type="reset">
              Clear
              <i class="bi bi-eraser"></i>
            </button>
          </div>
        </div>
      </div>
    </form>
    <hr/>
    <h4>Results</h4>
    <p v-if="result !== ''">{{result}}</p>
    <p v-else>Nothing to show yet!</p>
  </div>
</template>

<script>

export default {
  name: "MarkAttendance",
  components: {},
  data: function() {
    return { 
      RunningCourses: [],
      courses: [],
      kface: { group_photos: [] }, result: '' };
  },
  async mounted() {
    let vm = this
    await vm.doHttp(true, `running_courses`, null,
        (b)=>{vm.RunningCourses = b}, vm.setStatusMessage)
  },
  methods: {
    onCourseSelect(c) {
      this.kface.course_offering = c.id;
    },
    save() {
      let vm = this;
      if (!confirm("Confirm action?")) {
        vm.setStatusMessage("User canceled action!");
        return;
      }
      let formData = new FormData();
      formData.append("course_offering", vm.kface.course_offering)
      vm.kface.group_photos.forEach(ph => {
        formData.append("group_photos", ph, ph.name);
      });
      
      console.log("Uploading group photos.");
      vm.$http
        .post("mark_attendance", formData, {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        })
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.result = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      this.RunningCourses = []
      this.kface = { group_photos: [], course_offering: "" };
      this.result = '';
      console.log("Clearing upload.");
    },
    handleFile(e) {
      var files = e.target.files || e.dataTransfer.files;
      if (!files.length) {
        console.log("No photo selected.");
        return;
      }
      for (let i = 0; i < files.length; i++) {
        this.kface.group_photos.push(files[i])
      }
      console.log(this.kface.group_photos.length + " files added.")
    }
  }
};
</script>
