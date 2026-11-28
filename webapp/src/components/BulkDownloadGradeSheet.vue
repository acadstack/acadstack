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
          :disabled="job_state == 'running'"
        >
          <i class="bi bi-file-earmark-zip me-1"></i>Generate grade sheets
        </button>
        <button
          class="btn btn-outline-danger me-2 mt-3"
          @click="reset"
          type="reset"
        >
          <i class="bi bi-eraser"></i>
        </button>
      </div>
    </div>
    <div v-if="job_key" class="card mt-2">
      <div class="card-body">
        <div v-if="job_state == 'running'">
          <span class="spinner-border spinner-border-sm me-2" role="status"></span>
          Generating the grade sheets. This can take a few minutes; the status
          updates by itself.
        </div>
        <div v-else-if="job_state == 'failed'" class="text-danger">
          <i class="bi bi-exclamation-triangle me-1"></i>{{ job_error }}
        </div>
        <div v-else-if="job_state == 'done'">
          <p class="mb-2">
            <i class="bi bi-check-circle text-success me-1"></i>
            {{ job_result.sheets }} of {{ job_result.students }} grade sheets are ready.
          </p>
          <p v-if="job_result.no_results.length" class="mb-1">
            No results for this session and enrolment type: {{ job_result.no_results.join(", ") }}
          </p>
          <p v-if="job_result.withheld.length" class="mb-1">
            Left out, results withheld: {{ job_result.withheld.join(", ") }}
          </p>
          <p v-if="job_result.feedback_pending.length" class="mb-1">
            Left out, end-semester feedback not submitted: {{ job_result.feedback_pending.join(", ") }}
          </p>
          <p v-if="job_result.errors.length" class="mb-1 text-danger">
            Could not be processed: {{ job_result.errors.join("; ") }}
          </p>
          <a class="btn btn-outline-success mt-2" :href="`get_gradesheets/${job_key}`"
            target="_blank">Download</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";

// The submitted request, kept so that the page can show its status after the
// user comes back to it.
const JOB_KEY = "BulkGradeSheetJob";
const POLL_MS = 3000;

function emptyCriteria() {
  return { degree: "", dept_name: "", acad_session: "", enrol_type: "", for_year: "" };
}

export default {
  name: "bulkSemesterGrade",
  components: {
    AcadSession: AcadSession,
  },
  data: function () {
    return {
      search_crit: emptyCriteria(),
      job_key: "",
      // running, done or failed
      job_state: "",
      job_result: null,
      job_error: "",
      poll_timer: null,
    };
  },
  mounted: function () {
    let saved = null;
    try {
      saved = JSON.parse(sessionStorage.getItem(JOB_KEY) || "null");
    } catch {
      saved = null;
    }
    if (saved && saved.job_key) {
      this.search_crit = saved.search_crit;
      this.watchJob(saved.job_key);
    }
  },
  beforeUnmount: function () {
    this.stopPolling();
  },
  methods: {
    async search() {
      let vm = this;
      if (Object.values(vm.search_crit).some((v) => v === "")) {
        vm.setStatusMessage("Please specify all search condition!");
        return;
      }
      await vm.doHttp(
        false,
        "bulk_download_sem_grade",
        vm.search_crit,
        (b) => {
          vm.setSuccessMessage("Request submitted. The grade sheets are being generated.");
          try {
            sessionStorage.setItem(JOB_KEY, JSON.stringify(
              { job_key: b.job_key, search_crit: vm.search_crit }));
          } catch {
            // Only resuming after leaving the page needs it
          }
          vm.watchJob(b.job_key);
        },
        vm.setStatusMessage
      );
    },
    watchJob(job_key) {
      this.stopPolling();
      this.job_key = job_key;
      this.job_state = "running";
      this.job_result = null;
      this.job_error = "";
      this.checkStatus();
      this.poll_timer = setInterval(this.checkStatus, POLL_MS);
    },
    stopPolling() {
      if (this.poll_timer) {
        clearInterval(this.poll_timer);
        this.poll_timer = null;
      }
    },
    checkStatus() {
      let vm = this;
      vm.$http
        .get("bulk_gradesheets_status/" + vm.job_key)
        .then(function (res) {
          let b = res.data.body;
          if (res.data.status != "OK") {
            vm.stopPolling();
            vm.job_state = "failed";
            vm.job_error = b;
          } else if (b.status == "done") {
            vm.stopPolling();
            if (b.error) {
              vm.job_state = "failed";
              vm.job_error = b.error;
            } else {
              vm.job_state = "done";
              vm.job_result = b.result;
            }
          }
        })
        .catch(function (error) {
          // A passing network error; the next poll tries again
          console.log(error);
        });
    },
    reset() {
      this.stopPolling();
      this.job_key = "";
      this.job_state = "";
      this.job_result = null;
      this.job_error = "";
      this.search_crit = emptyCriteria();
      try {
        sessionStorage.removeItem(JOB_KEY);
      } catch {
        // Nothing saved to remove
      }
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