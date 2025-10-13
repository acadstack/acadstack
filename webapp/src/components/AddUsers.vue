<!--
Component for uploading users.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <p class="h6">Add Users</p>
    <p>Please upload new users information in CSV format only.</p>
    <div>
      <div class="row mb-2">
        <div class="col mb-1">
          <FileUploader destination="add_users"
                file_key="users_file"
                v-bind:upload_form_data="formData"
                v-on:fu-file-reset="reset"
                v-on:fu-file-selected="file_selected"
                v-on:fu-file-uploaded="file_uploaded"
                />
        </div>
      </div>
      <div class="row mb-2">
        <div class="col card">
          <div class="card-header">Confirm Users Information</div>
          <div class="card-body">
            <div class="row hdr-row">
              <div class="col">S#</div>
              <div class="col">Org. ID</div>
              <div class="col-md-2">Login ID</div>
              <div class="col-md-2">First Name</div>
              <div class="col-md-2">Last Name</div>
              <div class="col">Role</div>
              <div class="col">Dept.</div>
              <div class="col">Degree</div>
              <div class="col">Year of entry</div>
              <div class="col-md-2">Email</div>
            </div>
            <p v-if="result.length == 0">Nothing to show yet!</p>
            <div class="row row-striped" v-for="(r, idx) in result" :key="idx">
              <div class="col">{{idx+1}}</div>
              <div class="col">{{r.org_id}}</div>
              <div class="col-md-2">{{r.login_id}}</div>
              <div class="col-md-2">{{r.first_name}}</div>
              <div class="col-md-2">{{r.last_name}}</div>
              <div class="col">{{r.role}}</div>
              <div class="col">{{r.department}}</div>
              <div class="col">{{r.degree}}</div>
              <div class="col">{{r.year_of_entry}}</div>
              <div class="col-md-2">{{r.email}}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
export default {
  name: "AddUsers",
  components: {
    "FileUploader": FileUploader
  },
  data: function() {
    return {
      result: [],
      formData: {},
    };
  },
  methods: {
    reset() {
      this.result = [];
      console.log("Clearing upload.");
    },
    file_uploaded(res_body) {
      this.setStatusMessage(res_body);
    },
    file_selected(file) {
      let vm = this;
      if (!file) {
        console.log("No CSV file selected.");
        return;
      }
      const reader = new FileReader();
      reader.onload = function(evt) {
        let data = [];
        let rr = evt.target.result.split("\n");
        rr.forEach(row => {
          let cols = row.split(",");
          data.push({ org_id: cols[0], login_id: cols[1],
          first_name: cols[2], last_name: cols[3],
          role: cols[4], department: cols[5], 
          degree: cols[6], year_of_entry: cols[7], 
          email: cols[8] });
        });
        /** Remove the header row */
        data.splice(0, 1);
        vm.result = data;
      };
      reader.readAsText(file);
    }
  }
};
</script>
