<template>
  <div class="container-fluid">
    <p class="h6">Upload face photo</p>
    <p>Please ensure the following before uploading:</p>
    <ol>
      <li>Only the .jpg format files are allowed.</li>
      <li>The photo should contain only ONE face.</li>
    </ol>
    <div class="row">
      <div class="col-md-6">
        <FileUploader destination="face_add" file_key="photo_file" 
        v-bind:upload_form_data="kface" 
        v-on:fu-file-reset="file_reset"
        v-on:fu-file-uploaded="fileUploaded"
        @fu-file-selected="photoSelected"
        max_file_size_mb="1"/>
      </div>
      <div class="col-md-6">
        <div class="align-items-center text-center">
          <div v-if="photo_new">
            New:
            <img v-bind:src="photo_new" class="img-thumbnail" style="width: 250px;" />
          </div>
          <div v-if="photo && photo.length > 0">
            <img :src="'get_image/' + photo" class="img-thumbnail" style="width: 250px;" />
          </div>
          <div v-if="!photo_new && !photo">
            <i class="h1 bi bi-person-bounding-box"></i>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
export default {
  name: "KnownFaceUpload",
  components: {
    "FileUploader": FileUploader
  },
  data: function() {
    return { kface: {}, photo_new: "", photo: "" };
  },
  async mounted() {
    const vm = this
    await vm.doHttp(true, "my_photo", null, 
      (b)=>{ vm.photo = b}, vm.setStatusMessage)
  },
  methods: {
    file_reset() {
      console.log("File uploaded reset.");
    },
    fileUploaded(resBody) {
      this.setStatusMessage(resBody);
    },
    photoSelected(file) {
      let vm = this;
      if (!file) {
        console.log("No photo selected.");
        return;
      }
      console.log("Adding image.");
      let reader = new FileReader();
      reader.onload = function (e) {
        vm.photo_new = e.target.result;
        console.log("Image read.");
      };
      reader.readAsDataURL(file);
    }
  }  
};
</script>
