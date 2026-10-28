<!--
Component for listing the students whose advisor is the logged-in user.
-->
<template>
  <div class="container-fluid">
    <p class="h6">My Advisees</p>
    <div class="card">
      <div class="card-header">
        Students assigned to you as their advisor
        <span v-if="loaded" class="float-end">{{students.length}} students</span>
      </div>
      <div class="card-body">
        <p v-if="!loaded">Loading...</p>
        <p v-else-if="students.length == 0">No students are assigned to you.</p>
        <template v-else>
          <div class="row hdr-row border-bottom border-info">
            <div class="col-1">S#</div>
            <div class="col">Roll No.</div>
            <div class="col">Name</div>
            <div class="col">Department</div>
            <div class="col">Degree</div>
            <div class="col">Entry Year</div>
          </div>
          <div class="row row-striped" v-for="(s, i) in students" :key="s.user_id">
            <div class="col-1">{{i+1}}</div>
            <div class="col">
              <a v-if="hasPermission('students.academics:any')" :href="'#/std.detail/'+s.user_id">{{s.org_id}}</a>
              <span v-else>{{s.org_id}}</span>
            </div>
            <div class="col">{{s.name}}</div>
            <div class="col">{{labelFor(SD.Departments, s.dept)}}</div>
            <div class="col">{{labelFor(SD.Degrees, s.for_degree)}}</div>
            <div class="col">{{s.year}}</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "MyAdvisees",
  data: function() {
    return {
      loaded: false,
      students: []
    };
  },
  async created() {
    let vm = this;
    await vm.doHttp(true, `get_advisor_detail/${vm.currentUser.id}`, null,
      (body) => { vm.students = body; }, vm.setStatusMessage);
    vm.loaded = true;
  }
};
</script>
