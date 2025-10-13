<!--
Component for PhD progress report

@author Balwinder Sodhi

-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">
        <span class="float-start">Progress report for student</span>
        <div v-if="!(isStudent || viewOnly)" class="dropdown me-2 float-end">
          <button
            type="button"
            class="btn btn-primary dropdown-toggle"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            Action
          </button>
          <div class="dropdown-menu">
            <a
              class="dropdown-item"
              @click.prevent="onAction(act)"
              v-for="act in actions"
              :key="act"
              >{{ act.label }}</a
            >
          </div>
      </div>
      </div>
      <div class="card-body">
        <div class="row mb-2">
          <div class="col-md-4">
            <label for="studt">Student:</label>
            <my-dc-students :student="ppr.student" v-on:student-selected="ppr.student=$event"/>
          </div>
          <div class="col-md-3">
            <acad-session :acad_session="ppr.acad_session" 
                  :isEdit="isEdit" :disabled="viewOnly"
                  label="Academic Session"
                  v-on:update:acad_session='setAcadSession'/>
          </div>
          <div class="col-md-3">
            <label for="status">Status:</label>
            <span class="form-control">{{labelFor(SD.PPRStatuses, ppr.status)}}</span>
          </div>
          <div class="col-md-2">
            <div class="form-check form-check-inline mt-4">
              <input class="form-check-input" type="checkbox" 
              v-model="ppr.is_satisfactory" :disabled="viewOnly" id="ccb">
              <label class="form-check-label" for="ccb">Satisfactory</label>
            </div>
          </div>
        </div>
        <div class="row mb-2">
          <div class="col-md-12">
            <label for="rem">Remarks:</label>
            <textarea
              id="rem" :disabled="viewOnly"
              class="form-control"
              v-model="ppr.note"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
import MyDcStudents from "./MyDcStudents.vue";
export default {
  name: "PhdProgressReport",
  components: {
    AcadSession: AcadSession,
    MyDcStudents: MyDcStudents
  },
  data: function () {
    return {
      myStudents: [],
      ppr: {student: 0, status: "DRA"},
      /**
       * Defines the allowed actions to each role. The key is
       * role and value is the action label and the status of
       * course that will be set when action is performed.
       */
      actionsMap: {
        HOD: [
          { label: "Approve", status: "APP" },
          { label: "Return to DC", status: "RET" },
        ],
        DEA: [
          { label: "Approve", status: "APP" },
          { label: "Return to DC", status: "RET" },
        ],
        FAC: [
          { label: "Save as Draft", status: "DRA" },
          { label: "Submit to DC Chair", status: "SUB" },
          { label: "Approve as DC Chair", status: "APP" },
        ],
        ACA: [
          { label: "Approve", status: "APP" },
          { label: "Submit to DC Chair", status: "SUB" },
          { label: "Return to DC", status: "RET" },
          { label: "Save as Draft", status: "DRA" },
        ],
      },
    };
  },
  computed: {
    isEdit() {
      const x = this.$route.params.ppr_id;
      const ed = x != undefined && x > 0;
      console.log(`isEdit() called: ppr_id=${x}. isEdit=${ed}`);
      return ed;
    },
    actions() {
      return this.actionsMap[this.userRole];
    }
  },
  async created() {
    console.log("Creating PhdProgressReport");
    let vm = this;
    if (vm.isEdit) {
      await vm.load();
    } else {
      vm.reset();
    }
    vm.markViewOnly()
  },
  unmounted() {
    this.viewOnly = false;
  },
  methods: {
    setAcadSession(acd) {
      this.ppr.acad_session=acd;
    },
    async markViewOnly() {
      let vm = this;
      vm.viewOnly = vm.isEdit;
      /* Editable status for roles */
      const cs = vm.ppr.status;
      let isdcc = false;
      if ((vm.isAcad || vm.isDean) &&  cs != "DRA") {
        vm.viewOnly = false;
      } else {
        const rurl = `isdcc/${vm.thisUser.id}/${vm.ppr.student}`;
        await vm.doHttp(true, rurl, null,
                        (body)=>{isdcc = body}, vm.setStatusMessage
                      );
        if (isdcc && cs != "SUB") vm.viewOnly = false;
        else if (!isdcc && ["SUB","APP"].includes(cs)) vm.viewOnly = true;
        else vm.viewOnly = false;
      }
      console.log(`viewOnly=${vm.viewOnly}, isdcc=${isdcc}, cs=${cs}`);
    },
    onStudentSelect(c) {
      console.log("Selected student: " + JSON.stringify(c));
      this.ppr.student = c;
    },
    isDcValid() {
      // TODO:
      return true;
    },
    async load() {
      let vm = this;
      vm.loaded = false;
      let ppr_id = vm.$route.params.ppr_id;
      await vm.doHttp(true, `ppr_get/${ppr_id}`, null,
        (body)=>{vm.ppr = body}, vm.setStatusMessage
      );
    },
    async save() {
      let vm = this;
      //TODO: Check status and role before allowing save
      if (!vm.isDcValid()) {
        vm.setStatusMessage("Please supply valid details in report.");
      } else {
        if (!confirm("Confirm save?")) {
          return;
        }
        console.log("Saving Phd progress report.");
        await vm.doHttp(false, "ppr_save", vm.ppr, 
          async function(body) {
            vm.ppr = body;
            if (!vm.isEdit) {
              const v = `${vm.$route.path}/${vm.ppr.id}`;
              vm.$router.push({ path: v });
            }
            await vm.markViewOnly();
            vm.setStatusMessage("Progress report saved successfully!");
          }, vm.setStatusMessage);
      }
    },
    reset() {
      this.ppr = {student: 0, status: "DRA"};
      console.log("Clearing progress report.");
    },
    async onAction(act) {
      let vm = this;
      console.log("Changing progress report status to: " + act.status);
      vm.ppr.status = act.status;
      await vm.save();
    }
  },
};
</script>
