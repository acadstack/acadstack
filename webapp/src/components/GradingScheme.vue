<!--
Grading Scheme screen: the grading schemes of each program level. A scheme
applies to the sessions in its range (blank = no limit); where the ranges of
a level overlap, the narrowest one wins. For a change in one session, copy a
scheme and set both ends of its range to that session.
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">
        Grading schemes
        <button type="button" class="btn btn-outline-success float-end" :disabled="!loaded" @click="save">
          Save <i class="bi bi-save"></i>
        </button>
      </div>
      <div class="card-body">
        <div class="row mb-3">
          <div class="col-md-5">
            <label for="schemeSel" class="form-label">Scheme</label>
            <select id="schemeSel" class="form-select" v-model.number="cur">
              <option v-for="(s, i) in schemes" :key="i" :value="i">
                {{ s.name }} ({{ s.level }}, {{ s.from_session || "start" }} to {{ s.until_session || "no end" }})
              </option>
            </select>
          </div>
          <div class="col align-self-end">
            <button type="button" class="btn btn-outline-primary me-2" :disabled="!scheme" @click="copyScheme">
              Copy scheme
            </button>
            <button type="button" class="btn btn-outline-danger" :disabled="!scheme" @click="removeScheme">
              Delete scheme
            </button>
          </div>
        </div>

        <template v-if="scheme">
          <div class="row mb-3">
            <div class="col-md-4">
              <label for="schName" class="form-label">Name</label>
              <input id="schName" type="text" class="form-control" v-model="scheme.name" />
            </div>
            <div class="col-md-2">
              <label for="schLevel" class="form-label">Program level</label>
              <select id="schLevel" class="form-select" v-model="scheme.level">
                <option v-for="l in levels" :key="l" :value="l">{{ l }}</option>
              </select>
            </div>
            <div class="col-md-3">
              <label for="schFrom" class="form-label">From session</label>
              <input id="schFrom" type="text" class="form-control" list="sessionList" v-model.trim="scheme.from_session"
                placeholder="blank: from the start" />
            </div>
            <div class="col-md-3">
              <label for="schUntil" class="form-label">Until session</label>
              <input id="schUntil" type="text" class="form-control" list="sessionList" v-model.trim="scheme.until_session"
                placeholder="blank: no end" />
            </div>
            <datalist id="sessionList">
              <option v-for="a in SD.AcademicSessions" :key="a.id" :value="a.id">{{ a.value }}</option>
            </datalist>
            <div class="form-text">Only the current and next two sessions are suggested; type the code of an earlier one.</div>
          </div>

          <div class="row hdr-row mb-2 border-info border-bottom">
            <div class="col-md-1">Grade</div>
            <div class="col-md-1">Points</div>
            <div class="col" v-for="f in FLAGS" :key="f.key" :title="f.hint">{{ f.label }}</div>
            <div class="col-md-1"></div>
          </div>
          <div class="row row-striped mb-1" v-for="(g, i) in scheme.grades" :key="i">
            <div class="col-md-1">
              <input type="text" class="form-control form-control-sm" maxlength="2" v-model.trim="g.grade" />
            </div>
            <div class="col-md-1">
              <input type="number" step="any" min="0" class="form-control form-control-sm" v-model="g.points" />
            </div>
            <div class="col" v-for="f in FLAGS" :key="f.key">
              <input type="checkbox" class="form-check-input" v-model="g[f.key]" />
            </div>
            <div class="col-md-1">
              <button type="button" class="btn btn-sm btn-outline-danger" title="Remove grade"
                @click="scheme.grades.splice(i, 1)">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
          <button type="button" class="btn btn-outline-primary mt-2" @click="addGrade">Add grade</button>
          <p class="text-muted mt-3 mb-0">
            Points are blank for grades that carry none. A grade counted in the CGPA needs points and must earn credit.
            NA (not graded yet) is built in and is not listed here.
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
const FLAGS = [
  { key: "earns_credit", label: "Earns credit", hint: "The student earns the course credits" },
  { key: "in_cgpa", label: "In CGPA", hint: "Counted in SGPA and CGPA" },
  { key: "credit_without_gpa", label: "Credit, no GPA", hint: "Credits are left out of the SGPA; whether credit is earned is set by Earns credit" },
  { key: "excluded_from_gpa", label: "Left out of GPA", hint: "Credits are left out of the GPA" },
  { key: "allowed_for_audit", label: "Audit allowed", hint: "Can be given to a student auditing the course" },
];

export default {
  name: "GradingScheme",
  data: function () {
    return { FLAGS, levels: [], schemes: [], cur: 0, loaded: false };
  },
  computed: {
    scheme() {
      return this.schemes[this.cur];
    },
  },
  mounted: function () {
    this.doHttp(true, "vocab", null, (body) => { this.levels = body.attrs.Degrees.level; }, this.setStatusMessage);
    this.doHttp(true, "settings", null, this.apply, this.setStatusMessage);
  },
  methods: {
    apply(body) {
      const value = body.find(s => s.key == "grading_schemes").value;
      this.schemes = JSON.parse(JSON.stringify(value));
      if (this.cur >= this.schemes.length) this.cur = 0;
      this.loaded = true;
    },
    copyScheme() {
      const c = JSON.parse(JSON.stringify(this.scheme));
      c.name = `${c.name} (copy)`;
      this.schemes.push(c);
      this.cur = this.schemes.length - 1;
    },
    removeScheme() {
      if (!confirm(`Delete the scheme "${this.scheme.name}" and all its grades?`)) return;
      this.schemes.splice(this.cur, 1);
      this.cur = Math.max(0, Math.min(this.cur, this.schemes.length - 1));
    },
    addGrade() {
      this.scheme.grades.push({
        grade: "", points: "", earns_credit: false, in_cgpa: false,
        credit_without_gpa: false, excluded_from_gpa: false, allowed_for_audit: false,
      });
    },
    // The first problem the backend would reject (settings._grading_schemes_valid),
    // or one that would leave a level without a scheme; "" if none.
    problem(value) {
      for (const l of this.levels) {
        if (!value.some(s => s.level == l)) return `No grading scheme is left for ${l}.`;
      }
      for (const s of value) {
        const name = s.name.trim() || "(unnamed)";
        if (!s.name.trim()) return "Every scheme needs a name.";
        if (!s.grades.length) return `Scheme ${name} has no grades.`;
        const seen = new Set();
        for (const g of s.grades) {
          const at = `Scheme ${name}, grade ${g.grade || "(blank)"}`;
          if (!g.grade || g.grade.length > 2) return `${at}: a grade is 1 or 2 characters.`;
          if (g.grade == "NA") return `${at}: NA is built in.`;
          if (seen.has(g.grade)) return `${at}: listed twice.`;
          seen.add(g.grade);
          if (g.points !== null && !(Number.isFinite(g.points) && g.points >= 0)) return `${at}: points must be 0 or more.`;
          if (g.in_cgpa && (g.points === null || !g.earns_credit)) return `${at}: a grade in the CGPA needs points and must earn credit.`;
          if (g.points !== null && (g.credit_without_gpa || g.excluded_from_gpa)) return `${at}: a grade kept out of the GPA has no points.`;
        }
      }
      return "";
    },
    async save() {
      const value = this.schemes.map(s => ({
        ...s,
        from_session: s.from_session || null,
        until_session: s.until_session || null,
        grades: s.grades.map(g => ({
          ...g,
          grade: g.grade.trim().toUpperCase(),
          points: g.points === "" || g.points === null ? null : Number(g.points),
        })),
      }));
      const problem = this.problem(value);
      if (problem) return this.setStatusMessage(problem);
      await this.doHttp(false, "setting_save", { key: "grading_schemes", value }, async (body) => {
        this.apply(body);
        // The grades offered elsewhere (SD.CourseGrades) come from this setting.
        await this.doHttp(true, "get_static_data", null, this.setStaticData, this.setStatusMessage);
        this.setStatusMessage("Saved the grading schemes.");
      }, this.setStatusMessage);
    },
  },
};
</script>
