<template>
  <div class="container-fluid">
    <p class="h5">Student Registration Transaction Details</p>
    <p>
      NOTE: Only one combination of 
      {academic session, transaction no., 
      date, amount and bank} can be saved per student.
    </p>
  <div class="row mb-2">
        <div class="col">
          <b>Category:</b> {{labelFor(SD.PersonCategories, currentUser.category)}}
        </div>
            <div class="col">
          <b>Degree Type:</b> {{labelFor(SD.DegreeType, currentUser.deg_type)}}
        </div>
  </div>
    <div class="row mb-2">
      <div class="col-md-3">
        <div>
           <acad-session v-bind:acad_session="formData.acadSession"
                label="Academic Session"
                v-on:update:acad_session='formData.acadSession=$event;' id="acadSess" v-model="formData.acadSession" required/>
        </div>
      </div>
      <div class="col-md-3">
        <div>
          <label for="txnAmt">Amount (&#8377;)</label>
          <input type="number" class="form-control"
          min="1" id="txnAmt" v-model="formData.feesTxnAmt" required/>
        </div>
      </div>
      <div class="col-md-3">
        <div>
          <label for="feesTxnNo">Trans. No.</label>
          <input type="text" class="form-control"
          maxlength="60" minlength="1"
          id="feesTxnNo" v-model="formData.feesTxnNo" required/>
        </div>
      </div>
      <div class="col-md-3">
        <div>
          <label for="feesTxnDt">Trans. Date</label>
          <input type="date" class="form-control" 
          id="feesTxnDt" v-model="formData.feesTxnDt" required/>
        </div>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col-md-6">
        <div>
          <label for="txnBank">Bank</label>
          <input type="text" class="form-control" maxlength="60"
          id="txnBank" v-model="formData.feesTxnBank" required/>
        </div>
      </div>
      <div class="col-md-6">
        <div>
          <label for="txnFile">Transaction Proof (.jpg file)</label>
          <FileUploader id="txnFile" destination="save_reg_fees_data"
          file_key="doc_file" save_button_label="Save"
          v-bind:upload_form_data="formData"
          v-on:fu-file-reset="file_reset"
          v-on:fu-file-selected="file_selected"
          v-on:fu-file-upload-error="file_upload_failed"
          v-on:fu-file-uploaded="file_uploaded"/>
        </div>
      </div>
    </div>
    <div class="card">
      <h6 class="card-header">Fees Payment Transactions (Delete the old one to upload a new version)</h6>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Acad. Session</div>
          <div class="col-md-2">Amount (&#8377;)</div>
          <div class="col-md-2">Trans. No. and Dt.</div>
          <div class="col-md-2">Bank</div>
          <div class="col-md-2">Scanned doc.</div>
          <div class="col-md-1"></div>
        </div>
        <p v-if="docs.length == 0">Nothing to show yet!</p>
        <div class="row row-striped mt-4" v-for="(r, i) in docs.filter(x => !x.is_deleted)" :key="r.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-2">{{r.acad_session}}</div>
          <div class="col-md-2">{{r.fees_txn_amt}}</div>
          <div class="col-md-2">{{r.fees_txn_no}} ({{r.fees_txn_dt}})</div>
          <div class="col-md-2">{{r.fees_txn_bank}}</div>
          <div class="col-md-2">
            <a :href="`get_fees_txn_file/${r.doc_file_name}`" target="_blank">
              <img class="img-thumbnail" :src="`get_fees_txn_file/${r.doc_file_name}`" />
            </a>
          </div>
          <div class="col-md-1">
            <button class="btn btn-outline-danger" @click="delete_doc(r)">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FileUploader from "./FileUploader.vue";
import AcadSession from "./AcadSession.vue";
export default {
  name: "RegistrationFeesDetails",
  components: {
    "FileUploader": FileUploader
    , "AcadSession": AcadSession
  },
  data: function() {
    return {
      student_id: 0,
      formData: {
        acadSession: "", feesTxnNo: "",
        feesTxnDt: "", feesTxnBank: "",
        feesTxnAmt: 0
      },
      docs: []
    };
  },
  async mounted() {
    let vm = this;
    if (vm.isStudent) {
      vm.student_id = vm.currentUser.id;
    } else if (vm.isAcad || vm.isDean) {
      vm.student_id = vm.$route.params.user_id;
    } else {
      const msg = "You are not allowed to access this screen!";
      vm.setStatusMessage(msg);
      console.error(msg);
      return;
    }
    await vm.doHttp(true, 'get_reg_fees_data/'+vm.student_id,null,
      (b)=>{vm.docs = b;}, vm.setStatusMessage)
      vm.loaded = true;
  },
  methods: {
      file_reset() {
      let vm = this;
      this.formData = {
        student_id: vm.student_id,
        acadSession: "", feesTxnNo: "",
        feesTxnDt: "", feesTxnBank: "",
        feesTxnAmt: 0
      };
      console.log("Registration fees data reset.");
    },
   
    file_uploaded(res_body) {
      let vm = this;
      vm.docs.push(res_body);
      vm.file_reset();
    },
    file_upload_failed() {
      //  Clear the selected file
      this.file_reset();
    },
    file_selected() {
      this.formData.student_id = this.student_id;
      if (Object.values(this.formData).some(x => !x)) {
        this.setStatusMessage("All fields are mandatory!");
      }
    },

    async delete_doc(doc) {
      let vm = this;
      if (!confirm("Delete the document?")) {
        return;
      }
      await vm.doHttp(true, 'delete_fees_txn_data/'+doc.id, null,
        ()=>{doc.is_deleted = true;}, vm.setStatusMessage);
    }
  }  
};
</script>
