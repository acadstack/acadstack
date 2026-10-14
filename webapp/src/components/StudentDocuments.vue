<template>
  <div class="container-fluid">
    <div v-if="hasPermission('student_docs.upload')">
      <p class="h6">Upload Student Documents</p>
      <div class="row mb-2">
        <div class="col-md-4">
          <div>
            <label for="docDesc">Document description</label>
            <input type="text" class="form-control" 
            id="docDesc" v-model="formData.description" required/>
          </div>
        </div>
        <div class="col">
          <FileUploader destination="upload_student_doc"
          file_key="doc_file"
          v-bind:upload_form_data="formData"
          v-on:fu-file-reset="file_reset"
          v-on:fu-file-selected="file_selected"
          v-on:fu-file-uploaded="file_uploaded"/>
        </div>
      </div>
    </div>
    <div class="card mb-2" v-for="sec in sections" :key="sec.title">
      <h6 class="card-header">{{sec.title}}</h6>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col-md-3">File Name</div>
          <div class="col">Document Description</div>
          <div class="col-md-2">Uploaded By</div>
          <div class="col-md-2">Updated On</div>
          <div class="col-md-1"></div>
        </div>
        <p v-if="sec.rows.length == 0">Nothing to show yet!</p>
        <div class="row row-striped mt-4" v-for="(r, i) in sec.rows" :key="r.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-3">
            <a :href="'get_doc/'+r.id" target="_blank">{{r.file_name}}</a>
          </div>
          <div class="col">{{r.description}}</div>
          <div class="col-md-2">{{r.txn_login_id}}</div>
          <div class="col-md-2">{{r.upd_ts}}</div>
          <div class="col-md-1">
            <button v-if="r.can_delete" class="btn btn-outline-danger" @click="delete_doc(r)">Delete</button>
          </div>
        </div>
      </div>
    </div>
    <p v-if="hasPermission('student_docs.upload')" class="small text-muted">
      You can delete only the documents you uploaded. Delete the old one to upload a new version.
      Fee payment proofs are shown on the Registration Fees screen.
    </p>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
export default {
  name: "StudentDocuments",
  components: {
    "FileUploader": FileUploader
  },
  props: ["student_id"],
  data: function() {
    return { formData: {}, docs: [] };
  },
  computed: {
    sections() {
      let live = this.docs.filter(x => !x.is_deleted);
      return [
        {title: "Uploaded by student", rows: live.filter(x => x.uploaded_by_student)},
        {title: "Uploaded by staff", rows: live.filter(x => !x.uploaded_by_student)}
      ];
    }
  },
  created() {
    console.debug("Created StudentDocuments :: student_id="+this.student_id);
  },
  mounted() {
    let vm = this;
    vm.formData.student_id = vm.student_id;
    if (vm.student_id == undefined) {
      console.log("Not loading student docs. student_id is undefined")
      return;
    }
    return vm.$http.get('get_student_docs/'+vm.student_id)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.docs = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        vm.setStatusMessage("Error: "+error);
      });
  },
  methods: {
    file_reset() {
      this.formData = {};
      console.log("File uploaded reset.");
    },
    file_uploaded(res) {
      let vm = this;
      vm.docs.push(res);
    },
    file_selected() {
      
    },
    delete_doc(doc) {
      let vm = this;
      if (!confirm("Delete the document?")) {
        return;
      }
      vm.$http.post('delete_doc/'+doc.id)
        .then(function (res) {
          if (res.data.status == "OK") {
            doc.is_deleted = true;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          vm.setStatusMessage("Error: "+error);
        });
    }
  }  
};
</script>
