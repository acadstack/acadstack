<template>
  <div class="container-fluid">
    <p class="h6">Upload known faces</p>
    <p>Please ensure the following before uploading:</p>
    <ol>
      <li>The ZIP file should contain only the .jpg files.</li>
      <li>Each .jpg file should contain only ONE face.</li>
      <li>Name of the .jpg file must be of the following format:
      [Org. ID of the person].jpg
      Examples: 2018CSB1234.jpg, uttam.prasanna.jpg</li>
    </ol>
    <FileUploader destination="kface_bulk_add" file_key="zip_file" 
    v-bind:upload_form_data="kface" 
    v-on:fu-file-reset="file_reset"
    v-on:fu-file-uploaded="fileUploaded"
    max_file_size_mb="500"/>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
export default {
  name: "KnownFaceZipUpload",
  components: {
    "FileUploader": FileUploader
  },
  data: function() {
    return { kface: {} };
  },
  methods: {
    file_reset() {
      console.log("File uploaded reset.");
    },
    fileUploaded(resBody) {
      this.setStatusMessage(resBody);
    }
  }  
};
</script>
