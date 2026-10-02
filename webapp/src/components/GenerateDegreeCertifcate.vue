<template>
  <div class="container-fluid">
    <span class="sec-hdr">Generate Degree Certificate</span>
    <div class="row mb-2">    
    <div class="col-2">
            <div class=" me-2 mt-2"> 
          <label for="entry_no">Enter Entry Number: </label>
             &nbsp;<input id="entry_num" class="form-control" type="text"  v-model="myInput" />
            </div> 
      </div>
    <div class="col-2">
            <div class=" me-2 mt-2"> 
          <label for="hindi_name">Name in a second language: </label>
             &nbsp;<input id="hindi_name" class="form-control" type="text"  v-model="hindiName" />
            </div> 
    </div>
    <div class="col-3">
            <div class=" me-2 mt-2"> 
          <label for="thesis_title">Enter Thesis Title(applicable for phd students only) </label>
             &nbsp;<input id="thesis_title" class="form-control" type="text"  v-model="thesis_title" />
            </div> 
    </div>
    <div class="col-3">
            <div class=" me-2 mt-2"> 
          <label for="doc_sr_no">Doc. Sr. No.</label>
             &nbsp;<input id="doc_sr_no" class="form-control" type="text"  v-model="doc_sr_no" />
            </div> 
    </div>
    <div class="col-2">
            <div class=" me-2 mt-2">
          <label for="convocation_date">Convocation date</label>
             &nbsp;<input id="convocation_date" class="form-control" type="date"  v-model="convocation_date" />
            </div>
    </div>
       <div class="col-md-3">
        <button class="btn btn-outline-success me-2 mt-4"  aria-haspopup="true" 
                    aria-expanded="false">
            <a class="dropdown-item" :href="certificateUrl">Generate Degree</a>
        </button>
        <button class="btn btn-outline-danger me-2 mt-3" @click="reset" type="reset">
            <i class="bi bi-eraser"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "GenerateDegreeCertifcate",
  data: function () {
       return {
      myInput: "",
      hindiName: "",
      thesis_title: "",
      doc_sr_no: "",
      convocation_date: "",
      length: 0
      };
      },
computed: {
    certificateUrl() {
        const q = new URLSearchParams({hi_name: this.hindiName, thesis_title: this.thesis_title,
            doc_sr_no: this.doc_sr_no, convocation_date: this.convocation_date});
        return `download_degree_certifcate/${encodeURIComponent(this.myInput)}?${q}`;
    }
},
methods: {
    search: function () {
        this.length = this.myInput.length;
        },     
    reset() {
      this.myInput = "";
      this.length = "";
    }
}
};
</script>
