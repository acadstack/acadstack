<!--
Component for Creating Feedback Form.
-->
<template>
  <div>
    <div class="card">
      <div class="card-header">
        <div class="row align-items-center">
          <div class="col-md-4"><h4>Form definition</h4></div>
          <div class="col">
            <label>Load existing form</label>
            <select
              class="form-select"
              v-model.trim="selectedForm"
            >
              <option v-for="n in feedback_forms" v-bind:value="n" :key="n.id">
                {{ n.form_name }}
              </option>
            </select>
          </div>
          <div class="col-auto">
            <button
              class="btn btn-outline-primary mt-4"
              @click="load"
              type="button"
            >
              Load
            </button>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="row align-items-center pb-2">
          <div class="col">
            <label for="frm_nm">Form Name</label>
            <input
              id="frm_nm"
              type="text"
              class="form-control"
              minlength="5"
              v-model.trim="form.form_name"
            />
          </div>
          <div class="col">
            <label for="frm_typ">Form Type</label>
            <select class="form-select" id="frm_typ" 
            v-model.trim="form.form_type">
              <option
                v-for="cs in SD.FormTypes"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
          <div class="col">
            <label for="isActiv">Active</label>
            <input
              id="isActiv"
              type="checkbox"
              class="form-check-input"
              v-model.trim="form.is_active"
            />
          </div>
          <div class="col-md-4">
            <div class="mt-4 float-end">
              <button
                class="btn btn-outline-success me-2"
                type="button"
                @click="save"
              >
                Save
                <i class="bi bi-save"></i>
              </button>
              <button
                class="btn btn-outline-danger"
                type="button"
                @click="clear"
              >
                Clear
                <i class="bi bi-eraser"></i>
              </button>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-body">
            <div class="row border-bottom border-info pb-1">
              <div class="col-md-2"><h4>Questions</h4></div>
              <div class="col">
                <button
                  class="btn btn-outline-primary float-end"
                  @click="addItem"
                  type="button"
                >
                  Add Question
                </button>
              </div>
            </div>
            <div class="row hdr-row">
              <div class="col-md-1">S#</div>
              <div class="col">Question</div>
              <div class="col-md-2">Optional?</div>
              <div class="col-md-2">Is text?</div>
              <div class="col-md-2">Multiple answer?</div>
              <div class="col">Answer options (Comma-separated)</div>
              <div class="col-md-1"></div>
            </div>
            <p v-if="form.form_questions.length == 0">Nothing to show yet!</p>
            <div v-else class="row mt-2" v-for="(x, i) in form.form_questions" :key="x.id">
              <div class="col-md-1">{{ i + 1 }}</div>
              <div class="col">
                <textarea
                  type="text"
                  class="form-control"
                  v-model.trim="x.question"
                  rows="2"
                ></textarea>
              </div>
              <div class="col-md-2">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model.trim="x.is_optional"
                />
              </div>
              <div class="col-md-2">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model.trim="x.is_text"
                />
              </div>
              <div class="col-md-2">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model.trim="x.is_multianswer"
                />
              </div>
              <div class="col">
                <textarea
                  class="form-control"
                  v-model.trim="x.ans_options"
                  rows="2"
                ></textarea>
              </div>
              <div class="col-md-1">
                <button
                  class="btn btn-outline-danger"
                  @click="removeItem(x)"
                  type="button"
                >
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CreateFeedbackForm",
  data: function () {
    return {
      form: { form_name: "", is_active: true, 
      form_type: "", form_questions: [] },
      feedback_forms: [],
      selectedForm: {},
    };
  },
  async created() {
    await this.getForms();
  },
  methods: {
    addItem() {
      console.log("Adding question.");
      this.form.form_questions.push({});
    },
    removeItem(x) {
      console.log("Removing question.");
      let idx = this.form.form_questions.indexOf(x);
      this.form.form_questions.splice(idx, 1);
    },
    getForms() {
      let vm = this;
      return vm.$http
        .get("get_feedback_forms")
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.feedback_forms = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    save() {
      let vm = this;
      console.log(vm.form);
      vm.$http
        .post("form_save", vm.form)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.setStatusMessage(res.data.body);
            vm.getForms();
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    load() {
      let vm = this;
      vm.$http
        .get("load_feedback_form/" + vm.selectedForm.id)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.form = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    clear() {
      this.form = { form_name: "", 
        is_active: true, form_type: "",
        form_questions: [] };
      this.selectedForm = {};
    },
  },
};
</script>
