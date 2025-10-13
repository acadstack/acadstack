<template>
  <div class="container-fluid">
    <span class="sec-hdr">Bulk Download Semester Grade</span>
    <div class="row mb-2">
      <div class="col-6">
        <label for="deg">Degree</label>
        <select id="deg" class="form-select" v-model.trim="search_crit.degree">
          <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col-6">
        <label for="dept">Dept.</label>
        <select id="dept" class="form-select" v-model.trim="search_crit.dept_name">
          <option
            v-for="cs in SD.Departments"
            v-bind:value="cs.id"
            :key="cs.id"
          >
            {{ cs.value }}
          </option>
        </select>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col-6">
        <label for="ent_yr">Entry Year</label>
        <input
          id="ent_yr"
          class="form-control"
          type="number"
          min="2010"
          max="2099"
          v-model.trim="search_crit.for_year"
          placeholder="YYYY (e.g., 2019)"
        />
      </div>
      <div class="col-6">
        <label>Enrollment Type</label>
        <select
          class="form-select"
          id="st_entoltype"
          v-model="search_crit.enrol_type"
        >
          <option v-for="cs in SD.EnrolTypes" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col-6">
        <acad-session
          v-bind:acad_session="search_crit.acad_session"
          label="Academic Session"
          v-on:update:acad_session="search_crit.acad_session = $event"
        />
      </div>
      <div class="col-4">
        <button
          class="btn btn-outline-success me-2 mt-3"
          @click="search"
          type="submit"
        >
          <i class="bi bi-search"></i>
        </button>
        <button
          class="btn btn-outline-danger me-2 mt-3"
          @click="reset"
          type="reset"
        >
          <i class="bi bi-eraser"></i>
        </button>
      </div>
      <div style="margin-top:20px" v-if="job_key != ''" class="col-2">
        <button class="btn btn-outline-primary mb-2" @click="check_status">
          Check Status
        </button>
        <div v-if="job_status.status != undefined">
          <p>Status: {{ job_status.status }}<br /></p>
        </div>
        <div v-if="job_status.status == 'DONE'">
          <a
            class="btn btn-outline-success"
            :href="`get_gradesheets/${job_key}`"
            target="_blank"
            >Download</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
import _ from "lodash";
export default {
  name: "bulkSemesterGrade",
  components: {
    AcadSession: AcadSession,
  },
  data: function () {
    return {
      search_crit: {
        degree: "",
        dept_name: "",
        acad_session: "",
        enrol_type: "",
        for_year: "",
      },
      job_status: {},
      bulk_sem_grades: [],
      job_key: "",
    };
  },
  mounted: function () {
    if (this.$route.name == "gs.bulkdown") {
      if (sessionStorage.CCRData) {
        let dd = JSON.parse(sessionStorage.CCRData);
        this.bulk_sem_grades = dd.bulk_sem_grades;
        this.search_crit = dd.search_crit;
      } else {
        this.reset();
      }
    } else {
      this.reset();
    }
  },
  methods: {
    async search() {
      let vm = this;
      if (
        vm.search_crit.degree === "" ||
        vm.search_crit.dept_name === "" ||
        vm.search_crit.for_year === "" ||
        vm.search_crit.enrol_type === "" ||
        vm.search_crit.acad_session === ""
      ) {
        vm.setStatusMessage("Please specify all search condition!");
        return;
      }
      console.log("Running Bulk_download_semester_grade");
      await vm.doHttp(
        false,
        "bulk_download_sem_grade",
        vm.search_crit,
        (b) => {
          vm.job_key = b.job_key;
        },
        vm.setStatusMessage
      );
    },
    check_status() {
      let vm = this;
      vm.job_status = {};
      vm.$http
        .get("job_status/" + this.job_key)
        .then(function (res) {
          vm.job_status = res.data.body;
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when checking job status.");
        });
    },
    reset() {
      this.job_key = "";
      this.bulk_sem_grades = [];
      this.job_status = {};
      this.search_crit = {
        degree: "",
        dept_name: "",
        acad_session: "",
        enrol_type: "",
        for_year: "",
      };
    },
  },
};
</script>

<style>
table {
  font-family: "Open Sans", sans-serif;
  /* width: 750px; */
  width: auto;
  border-collapse: collapse;
  /* border: 3px solid #44475C; */
  margin: 15px 15px 0 30px;
}

table th {
  text-transform: uppercase;
  text-align: left;
  background: #44475c;
  color: #fff;
  padding: 8px;
  min-width: 30px;
}

table td {
  text-align: left;
  padding: 10px;
  border-right: 2px solid #7d82a8;
}
table td:last-child {
  border-right: none;
}
</style>