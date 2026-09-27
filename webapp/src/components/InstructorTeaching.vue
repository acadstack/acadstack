<template>
  <div>
    <div class="card">
      <div class="card-header">
        Results
      <span class="float-end">
          <button
            class="btn btn-outline-info btn-sm me-4"
            v-if="course.pg_no > 1"
            @click="prev_pg"
          >Prev</button>
          <button
            class="btn btn-outline-info btn-sm me-4"
            v-if="results.has_next"
            @click="next_pg"
          >Next</button>
        </span>
      </div>
      <div class="card-body">
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Session</div>
          <div class="col-md-6">Course</div>
          <div class="col">Class Size</div>
          <div class="col">Feedback</div>
        </div>
        <p v-if="results.courses.length == 0">Nothing to show!</p>
        <div class="row row-striped" v-for="(c, index) in results.courses" :key="c.id">
          <div class="col-md-1">{{ index + 1 }}</div>
          <div class="col-md-2">
            <a :href="'#/co.detail/'+c.id">
            {{c.session}}</a></div>
          <div class="col-md-6">
            <a :href="'#/cour.detail/'+c.code">
            {{c.name}}</a>
            </div>
          <div class="col">{{c.classSize}}</div>
          <div class="col">{{c.feedback}}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "InstructorTeaching",
  props: ["user_id"],
  data: function() {
    return { 
      results: { courses: [], has_next: false },
    course: { pg_no: 1 }
    };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("InstructorTeaching.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  
  created: function() {
    console.log("Creating InstructorTeaching");
    // Alias 'this' for accessing in promises
    var vm = this;
    // TODO: Fetch data from an API
    vm.find();
  },
  
  methods: {
    refreshView() {
    },
    find(){
    var vm = this;
    let id = vm.user_id
    vm.$http.post('get_instructor_academics/'+id,vm.course)
    .then(function (res) {
      if (res.data.status == "OK") {
        vm.results = res.data.body;
        sessionStorage.mykey = JSON.stringify(vm.results);
      } else {
        vm.setStatusMessage(res.data.body);
      }
    })
    .catch(function (error) {
      console.log(error);
      vm.setStatusMessage("Error: "+error);
    });
  },
  next_pg() {
      this.course.pg_no += 1;
      this.find();
    },
    prev_pg() {
      this.course.pg_no -= 1;
      this.find();
    },
  }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>

</style>
