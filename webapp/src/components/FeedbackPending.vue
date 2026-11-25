<!--
Students who have not submitted course feedback in a session, with the
courses and instructors they owe it for.
-->
<template>
  <div class="container-fluid">
    <span class="sec-hdr">Students with Pending Feedback</span>
    <div class="row mb-2">
      <div class="col">
        <label for="frm_typ">Feedback type</label>
        <select class="form-select" id="frm_typ" v-model="crit.form_type">
          <option v-for="cs in SD.FormTypes" :value="cs.id" :key="cs.id">{{ cs.value }}</option>
        </select>
      </div>
      <div class="col">
        <acad-session :acad_session="crit.acad_session" label="Academic Session"
          v-on:update:acad_session="crit.acad_session = $event" />
      </div>
      <div class="col">
        <label for="deg">Degree</label>
        <select id="deg" class="form-select" v-model="crit.degree">
          <option v-for="cs in SD.Degrees" :value="cs.id" :key="cs.id">{{ cs.value }}</option>
        </select>
      </div>
      <div class="col">
        <label for="dept">Dept.</label>
        <select id="dept" class="form-select" v-model="crit.dept_name">
          <option v-for="cs in SD.Departments" :value="cs.id" :key="cs.id">{{ cs.value }}</option>
        </select>
      </div>
      <div class="col">
        <label for="ent_yr">Entry Year</label>
        <input id="ent_yr" class="form-control" type="number" min="2010" max="2099"
          v-model.trim="crit.entry_year" placeholder="Any" />
      </div>
      <div class="col">
        <button class="btn btn-outline-success me-2 mt-3" @click="search" type="submit" title="Search">
          <i class="bi bi-search"></i>
        </button>
        <button class="btn btn-outline-danger me-2 mt-3" @click="reset" type="reset" title="Clear">
          <i class="bi bi-eraser"></i>
        </button>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Student</div>
          <div class="col-md-2">Program</div>
          <div class="col">Feedback not submitted for</div>
          <div class="col-md-2" v-if="searched">
            <a class="btn btn-outline-success" :href="csvUrl">Download CSV</a>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="!searched">Nothing to show yet!</p>
        <p v-else-if="students.length == 0">Every student has submitted this feedback.</p>
        <p v-else class="text-muted">{{ students.length }} students have feedback pending.</p>
        <div class="row row-striped" v-for="(s, i) in students" :key="s.org_id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">{{ s.first_name }} {{ s.last_name }} ({{ s.org_id }})<br />
            <small>{{ s.email }}</small></div>
          <div class="col-md-2">{{ labelFor(SD.Degrees, s.degree) }}, {{ labelFor(SD.Departments, s.dept_name) }},
            {{ s.year_of_entry }}</div>
          <div class="col">
            <div v-for="p in s.pending" :key="p">{{ p }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";

function emptyCriteria() {
  return { form_type: "END_SEM_FB", acad_session: "", degree: "", dept_name: "", entry_year: "" };
}

export default {
  name: "FeedbackPending",
  components: { AcadSession },
  data: function () {
    return { crit: emptyCriteria(), students: [], searched: null };
  },
  computed: {
    csvUrl() {
      // The criteria of the shown results; "-" matches any
      const c = this.searched;
      return "download_feedback_pending/" + [c.form_type, c.acad_session, c.degree, c.dept_name,
        c.entry_year].map((v) => encodeURIComponent(v || "-")).join("/");
    },
  },
  methods: {
    async search() {
      let vm = this;
      if (!vm.crit.form_type || !vm.crit.acad_session) {
        vm.setStatusMessage("Select the feedback type and the academic session.");
        return;
      }
      const crit = { ...vm.crit };
      await vm.doHttp(false, "feedback_pending", crit, (body) => {
        vm.students = body;
        vm.searched = crit;
      }, vm.setStatusMessage);
    },
    reset() {
      this.crit = emptyCriteria();
      this.students = [];
      this.searched = null;
    },
  },
};
</script>
