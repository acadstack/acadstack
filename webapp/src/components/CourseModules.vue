<!--
Component for modules tab of the course details.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div class="card">
      <div v-if="!error.course.modules.notempty && error.course.modules.$dirty" class="text-danger">Modules must have a item.</div>
      <div v-else-if="!error.course.modules.itemnotempty && error.course.modules.$dirty" class="text-danger">Entry of a item in Modules should not be empty.</div>
    
      <div class="card-header">Module-wise Course Contents (Include laboratory/design activities)
        <span class="float-end" v-if="!print">
          <button class="btn btn-outline-primary" @click="addItem" type="button" :disabled="viewOnly">Add</button>
        </span>
      </div>
      <div class="card-body">
        <p v-if="course.modules.length == 0">Nothing to show yet!</p>
        <div v-else>
          <div class="row hdr-row">
            <div class="col-md-1">S#</div>
            <div class="col">Module Title</div>
            <div class="col-md-1">Lect.</div>
            <div class="col">Module Details</div>
            <div class="col-md-1" v-if="!print"></div>
          </div>
          <div class="row row-striped mt-2" v-for="(x, i) in course.modules" :key="x.id">
            <div class="col-md-1">{{i+1}}</div>
            <div class="col">
              <input type="text" class="form-control" v-model.trim="x.title" :disabled="viewOnly"/>
            </div>
            <div class="col-md-1">
              <input type="number" class="form-control" v-model.trim="x.lectures" :disabled="viewOnly"/>
            </div>
            <div class="col">
              <textarea class="form-control" v-model.trim="x.details" rows="2" :disabled="viewOnly"></textarea>
            </div>
            <div class="col-md-1"  v-if="!print">
              <button class="btn btn-outline-danger" @click="removeItem(x)" type="button" :disabled="viewOnly"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseModules",
  props: ["course","error", "print"],
  data: function() {
    return {};
  },
  created: function() {
    console.log("Creating CourseModules:"+this.course.modules);
    this.viewOnly = this.isStudent;
    // if (this.mod.items == undefined) this.mod.items = [];
  },
  methods: {
    addItem() {
      console.log("Adding module.")
      this.course.modules.push({});
    },
    removeItem(x) {
      console.log("Removing module.")
      let idx = this.course.modules.indexOf(x)
      this.course.modules.splice(idx, 1)
    }
  }
};
</script>
