<!--
Component for uploading courses.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Add Courses</p>
    <p>Please upload new courses information in CSV format only.</p>
    <div>
      <div class="row mb-2">
        <div class="col">
          <form @submit.prevent="save">
            <div class="row mb-2">
              <div class="col-md-4">
                <label for="uploadFile">Courses CSV File:</label>
                <input id="uploadFile" class="form-control" type="file" @change="handleFile" />
              </div>
              <div class="col">
                <div class="mt-4">
                  <button class="btn btn-outline-success me-2" type="button" 
                    @click="save" :disabled="!result.length">
                    Upload
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
        </div>
      </div>
      <div class="row mb-2">
        <div class="col card">
          <div class="card-header">Confirm Courses Information</div>
          <div class="card-body">
            <div class="row hdr-row">
              <div class="col-md-1">S#</div>
              <div class="col-md-2">Code</div>
              <div class="col">Title</div>
              <div class="col-md-3">LTPSC</div>
            </div>
            <p v-if="result.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(r, idx) in result" :key="idx">
              <div class="col-md-1">{{idx+1}}</div>
              <div class="col-md-2">{{r.code}}</div>
              <div class="col">{{r.title}}</div>
              <div class="col-md-3">{{r.ltp}}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "AddUsers",
  data: function() {
    return {
      courses: { courses_file: "", file_name: "" },
      result: []
    };
  },
  methods: {
    save() {
      let vm = this;
      if (!confirm("Confirm action?")) {
        vm.setStatusMessage("User canceled action!");
        return;
      }
      let formData = new FormData();
      formData.append(
        "courses_file",
        vm.courses.courses_file,
        vm.courses.courses_file.name
      );

      console.log("Uploading courses information.");
      vm.$http
        .post("cour_add", formData, {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        })
        .then(function(res) {
          vm.setStatusMessage(res.data.body);
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      this.courses = { courses_file: "", file_name: "" };
      this.result = [];
      console.log("Clearing upload.");
    },
    handleFile(e) {
      let vm = this;
      var files = e.target.files || e.dataTransfer.files;
      if (!files.length) {
        console.log("No CSV file selected.");
        return;
      }
      vm.courses.courses_file = files[0];
      vm.courses.file_name = files[0].name;
      const reader = new FileReader();
      reader.onload = function(evt) {
        let data = [];
        let rr = evt.target.result.split("\n");
        rr.forEach(row => {
          let cols = row.split(",");
          data.push({ code: cols[0], title: cols[1]
          , ltp: cols[2]});
        });
        /** Remove the header row */
        data.splice(0, 1);
        vm.result = data;
      };
      reader.readAsText(files[0]);
    }
  }
};
</script>
