<!--
Component for the evaluation components of a course offering, whose scores
are uploaded with the grades.
-->
<template>
  <div class="card mb-2">
    <div class="card-header">Evaluation Components</div>
    <div class="card-body">
      <p v-if="!saved" class="text-muted">
        Not saved yet. Shown below are the items of the course's evaluation plan;
        change them as needed and save.
      </p>
      <div class="row mb-1 hdr-row">
        <div class="col-md-3">Code (CSV column)</div>
        <div class="col-md-5">Name</div>
        <div class="col-md-2">Weight %</div>
        <div class="col-md-2" v-if="canEdit">Remove</div>
      </div>
      <p v-if="items.length == 0">Nothing added yet!</p>
      <div class="row mb-2" v-for="(c, i) in items" :key="i">
        <div class="col-md-3">
          <input class="form-control" type="text" maxlength="10" v-model.trim="c.code"
            :disabled="!canEdit" placeholder="E.g. MSE"/>
        </div>
        <div class="col-md-5">
          <input class="form-control" type="text" maxlength="100" v-model.trim="c.label"
            :disabled="!canEdit" placeholder="E.g. Mid-sem exam"/>
        </div>
        <div class="col-md-2">
          <input class="form-control" type="number" min="0" max="100" v-model="c.weight"
            :disabled="!canEdit"/>
        </div>
        <div class="col-md-2" v-if="canEdit">
          <button class="btn btn-outline-danger" type="button" @click="items.splice(i, 1)">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
      <div v-if="canEdit">
        <button class="btn btn-outline-primary me-2" type="button"
          @click="items.push({code: '', label: '', weight: null})">
          Add <i class="bi bi-plus"></i>
        </button>
        <button class="btn btn-outline-success" type="button" @click="save">
          Save Components <i class="bi bi-save"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "EvalComponents",
  props: ["co_id"],
  data: function() {
    return {
      items: [],
      saved: false
    };
  },
  computed: {
    canEdit() {
      return this.hasPermission('grades.upload');
    }
  },
  watch: {
    co_id() {
      this.load();
    }
  },
  created() {
    this.load();
  },
  methods: {
    show(b) {
      this.items = b.components;
      this.saved = b.saved;
    },
    load() {
      if (this.co_id) {
        this.doHttp(true, `eval_components/${this.co_id}`, null, this.show,
          this.setStatusMessage);
      }
    },
    save() {
      let vm = this;
      vm.doHttp(false, "eval_components_save",
        {course_offering: vm.co_id, components: vm.items},
        (b) => { vm.show(b); vm.setStatusMessage("Saved the evaluation components."); },
        vm.setStatusMessage);
    }
  }
};
</script>
