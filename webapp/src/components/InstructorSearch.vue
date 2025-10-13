<template>
  <div class="container-fluid">
    <p class="h6">Find Instructors</p>
    <form @submit.prevent="find">
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
              <option v-for="dept in deptList" :value="dept.val" :key="dept.name">{{ dept.name }}</option>
            </select>
          </div>
        </div>
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
        <div class="col-md-2">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit"><i class="bi bi-search"></i></button>
            <button class="btn btn-outline-danger" @click="reset" type="reset"><i class="bi bi-eraser"></i></button>
          </div>
        </div>
      </div>
    </form>
    
    <div class="card">
      <div class="card-header">Results</div>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col">Name</div>
          <div class="col">Summary</div>
        </div>
        <p v-if="results.length == 0">Nothing to show yet!</p>
        <div class="row mb-2" v-for="(r, i) in results" :key="r.id">
          <div class="col-md-1">{{i+1}}</div>
          <div class="col"><a :href="'#/ins.detail/'+r.id">{{r.name}}</a></div>
          <div class="col">{{r.summary}}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "InstructorSearch",

  data: function() {
    return { results: [], ins: {} };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("InstructorSearch.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  created: function() {
    console.log("Creating InstructorSearch");
    // Alias 'this' for accessing in promises
    var vm = this;
    vm.deptList = [{name:"CSE", val:"cse"},{name:"EE", val:"ee"}, {name:"ME", val:"me"}]
  },
  methods: {
    find() {
      // TODO: Fetch from API
      this.results = [
        {id:1, name:"Dr. G.G Jalebi", summary:"Dept. of CSE. Teaches XXX, YYY"},
        {id:2, name:"Dr. Guru Prachand", summary:"Dept. of EE. Also doing OK"},
        {id:3, name:"Dr. Komal Hriday", summary:"Dept. of ME. OKOK he is doing."}
      ]
    },
    reset() {
      this.results = []
      this.ins = {}
    }
  }
};
</script>
