<template>
  <div class="container-fluid">
    <span class="sec-hdr">Generate Degree Certificate</span>
    <div class="row mb-2">    
      <div class="col-2">
        <div class="me-2 mt-2"> 
          <label for="entry_no">Enter Entry Number: </label>
             &nbsp;<input id="entry_num" class="form-control" type="text"  v-model="myInput" />
        </div> 
      </div>
       <div class="col-3">
        <div class="me-2 mt-2">
          <label>Enrollment Type</label>
          <select class="form-select" id="st_entoltype" v-model="enrol_type">
            <option v-for="cs in SD.EnrolTypes" v-bind:value="cs.id" :key="cs.id">{{ cs.value }}</option>
          </select>
        </div>
      </div>
    <div class="col-md-3">
        <button class="btn btn-outline-success me-2 mt-4"  aria-haspopup="true"
                    aria-expanded="false">
            <a class="dropdown-item" :href="`download_consolidated_grade_sheet/${myInput}/${enrolType}`">Generate Consolidated Grade Sheet</a>
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
  name: "ConsolidatedGradeSheet",
  data: function () {
       return {
      myInput: "",
      hindiName: "",
      length: 0,
      enrol_type: ""
      };
      },
    computed: {
      enrolType() {
      return this.enrol_type;
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
