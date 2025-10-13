<template>
  <div class="container-fluid">
    <p class="h6">Instructor Details</p>
    <form @submit.prevent="save">
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="ins_email">Email</label>
            <input type="email" class="form-control" id="ins_email" v-model="ins.email"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="ins_dept">Dept.</label>
            <select class="form-select" id="ins_dept" v-model="ins.dept">
              <option v-for="dept in deptList" :value="dept.id" :key="dept.id">{{ dept.name }}</option>
            </select>
          </div>
        </div>
      </div>
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="ins_firstnm">First Name</label>
            <input type="text" class="form-control" id="ins_firstnm" v-model="ins.firstName"/>
          </div>
        </div>
        <div class="col">
          <div>
            <label for="ins_lastnm">Last Name</label>
            <input type="text" class="form-control" id="ins_lastnm" v-model="ins.lastName"/>
          </div>
        </div>
      </div>
      <div class="row mb-2">
        <div class="col">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit">Save 
              <i class="bi bi-save"></i></button>
            <button class="btn btn-outline-danger" @click="reset" type="reset">Clear
              <i class="bi bi-eraser"></i></button>
          </div>
        </div>
      </div>
    </form>
    
    <div v-if="isEdit">
      <h6>Teaching</h6>
      <InstructorTeaching />
    </div>
  </div>
</template>

<script>
import InstructorTeaching from "./InstructorTeaching.vue"

export default {
  name: "InstructorDetails",
  components: {
    InstructorTeaching
  },

  data: function() {
    return { ins: {} };
  },
  computed: {
    isEdit() {
      console.log("isEdit() called")
      return this.$route.params.id > 0;
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log("InstructorDetails.beforeRouteUpdate");
    if (from.path.startsWith(to.path)) {
      this.reset();
    } else if (to.params.id) {
      this.load();
    }
    next();
  },
  created: function() {
    console.log("Creating Instructor Details");
    let vm = this;
    vm.deptList = [{id:1, name: "CSE"}, {id:2, name: "EE"},
    {id:3, name: "ME"}]
    if (vm.isEdit) {
      vm.load();
    } else {
      vm.reset();
    }
  },
  methods: {
    load() {
      // Alias 'this' for accessing in promises
      let vm = this;
      // TODO: Fetch data from an API
      vm.ins = {email: "some@email.com", dept: "ee",
      firstName: "Chaman", lastName: "Laal"};
      vm.deptList = [{name:"CSE", val:"cse"},{name:"EE", val:"ee"}, {name:"ME", val:"me"}];
    },
    save() {
      //TODO:
      console.log("Saving Instructor details.");
    },
    reset() {
      //TODO:
      this.ins = {};
      console.log("Clearing Instructor details.");
    }
  }
};
</script>
