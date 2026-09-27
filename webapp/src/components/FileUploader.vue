<template>
  <div>
    <form @submit.prevent="save">
      <div class="input-group">
        <input id="uploadFile" class="form-control" type="file" @change="handleFile" />
        <div v-if="destination">
          <button class="btn btn-outline-primary me-1" type="submit">{{save_label}}</button>
          <button class="btn btn-outline-danger" @click="reset" type="reset">Clear</button>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  name: "FileUploader",
  /**
   * 'destination' is the URL of remote service to which to POST.
   * 'upload_form_data' is an object whose enties will be POSTed.
   * 'file_key' is the form field name under which the file will
   * be stored in the form.
   * 'save_button_label' if supplied will be used as the label for
   * save button. Default label will be "Upload".
   * 'max_file_size_mb' is the max. file size allowed (in MB). 
   * Default is 1MB.
   */
  props: ["destination", "upload_form_data", "file_key", 
    "save_button_label", "max_file_size_mb"],
  emits: ["fu-file-uploaded", "fu-file-upload-error",
    "fu-file-reset", "fu-file-selected"],
  data: function() {
    return { data_file: "", file_name: "", save_label: "Upload" };
  },
  async created() {
    if (this.save_button_label != undefined) {
      this.save_label = this.save_button_label;
    }
    if (this.max_file_size_mb == undefined) {
      this.max_file_size_mb = 1;
    }
  },
  methods: {
    save() {
      let vm = this;
      if (!vm.destination) {
        console.debug("No upload destination specified. Ignoring save.");
        return;
      }
      if (!confirm("Confirm save?")) {
        vm.setStatusMessage("User canceled save!");
        return;
      }
      if (vm.data_file == "" || vm.file_name == "") {
        vm.setStatusMessage("Please select a file!");
        return;
      }
      /** Prepare the form payload to POST. */ 
      const payload = new FormData();
      if (vm.upload_form_data != undefined) {
        /** Add all entries as form properties. */
        for (const [key, value] of Object.entries(vm.upload_form_data)) {
          payload.set(key, value);
        }
      }
      payload.set(vm.file_key, vm.data_file, vm.data_file.name);

      console.log("Uploading file.");
      vm.$http
        .post(vm.destination, payload, {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        })
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.$emit("fu-file-uploaded", res.data.body);
          } else {
            vm.data_file = ""
            vm.file_name = ""
            vm.setStatusMessage(res.data.body);
            vm.$emit("fu-file-upload-error", res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          const msg = "Error occurred when contacting the server.";
          vm.setStatusMessage(msg);
          vm.$emit("fu-file-upload-error", msg);
        });
    },
    reset() {
      this.data_file = ""
      this.file_name = ""
      this.$emit("fu-file-reset");
      console.log("Clearing upload.");
    },
    handleFile(e) {
      let files = e.target.files || e.dataTransfer.files;
      let errMsg = undefined;
      if (!files.length) {
        errMsg = "No file selected!";
      } else if (files[0].size > 1000000 * this.max_file_size_mb) {
        errMsg = `Please select a file smaller than the max. allowed file size ${this.max_file_size_mb}MB`;
      }
      if (errMsg != undefined) {
        console.debug(errMsg);
        this.setStatusMessage(errMsg);
        this.$emit("fu-file-upload-error", errMsg);
        return;
      }
      this.data_file = files[0];
      this.file_name = files[0].name;
      /**
       * A listener can react to this event, e.g., to display
       * the contents of the selected file before uploading.
       */
      this.$emit("fu-file-selected", files[0]);
    }
  }
};
</script>
