<!--
Component for teaching learning plan details tab of the course details.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div v-if="!error.course.teaching.notempty && error.course.teaching.$dirty" class="text-danger">Teaching plan must have a item.</div>
    <div v-else-if="!error.course.teaching.itemnotempty && error.course.teaching.$dirty" class="text-danger">Entry of a item in Teaching plan should not be empty.</div>
    
    <div class="card">
      <div class="card-header">Teaching plan
        <span class="float-end" v-if="!print">
          <button class="btn btn-outline-primary" @click="addTeachingItem" type="button" :disabled="viewOnly">Add</button>
        </span>
      </div>
      <div class="card-body">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Week No.</div>
          <div class="col">Lecture/lab topics</div>
          <div class="col-md-1" v-if="!print"></div>
        </div>
        <p v-if="course.teaching.length == 0">Nothing to show yet!</p>
        <div v-else class="row row-striped mt-2" v-for="(x, i) in course.teaching" :key="i">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-2">
            <input type="text" class="form-control" v-model.trim="x.week" :disabled="viewOnly"/>
          </div>
          <div class="col">
            <textarea class="form-control" v-model.trim="x.topics" rows="2" :disabled="viewOnly"></textarea>
          </div>
          <div class="col-md-1" v-if="!print">
            <button class="btn btn-outline-danger" @click="removeItem(x)" type="button" :disabled="viewOnly"><i class="bi bi-trash"></i></button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!error.course.ref_material.notempty && error.course.ref_material.$dirty" class="text-danger">Learning Material must have a item.</div>
    <div v-else-if="!error.course.ref_material.itemnotempty && error.course.ref_material.$dirty" class="text-danger">Entry of a item in Learning Material should not be empty.</div>
    <div class="card mt-2">
      <div class="card-header">Learning Material
        <span class="float-end" v-if="!print">
          <button class="btn btn-outline-primary" @click="addBook" type="button" :disabled="viewOnly">Add</button>
        </span>
      </div>
      <div class="card-body">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-5">Title</div>
          <div class="col-md-5">Details (ISBN, URL, etc.)</div>
          <div class="col-md-1" v-if="!print"></div>
        </div>
        <p v-if="course.ref_material.length == 0">Nothing to show yet!</p>
        <div v-else class="row mt-2" v-for="(x, i) in course.ref_material" :key="i">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col-md-5">
            <input type="text" class="form-control" v-model.trim="x.title" :disabled="viewOnly"/>
          </div>
          <div class="col-md-5">
            <textarea class="form-control" v-model.trim="x.details" rows="2" :disabled="viewOnly"></textarea>
          </div>
          <div class="col-md-1" v-if="!print">
            <button class="btn btn-outline-danger" @click="removeBook(x)" type="button" :disabled="viewOnly"><i class="bi bi-trash"></i></button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseTLP",
  props: ["course","error","print"],
  data: function() {
    return {};
  },
  created: function() {
    console.log("Creating CourseTLP: "+JSON.stringify(this.course));
    let vm = this;
    vm.viewOnly = vm.isStudent;
    if (vm.course.teaching == undefined) {
      vm.$set(vm.course, "teaching", []);
    }
    if (vm.course.ref_material == undefined) {
      vm.$set(vm.course, "ref_material", []);
    }
  },
  methods: {
    addTeachingItem() {
      this.course.teaching.push({week:"", topics:""});
    },
    removeItem(x) {
      this.course.teaching = this.course.teaching.filter(y => y!=x);
    },
    addBook() {
      this.course.ref_material.push({title:"", details:""});
    },
    removeBook(x) {
      this.course.ref_material = this.course.ref_material.filter(y => y!=x);
    }
  }
};
</script>
