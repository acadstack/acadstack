<!--
Component for listing the course offerings.

@author Balwinder Sodhi
-->
<template>
  <div class="card">
    <div class="card-header">
      <div class="row hdr-row border-bottom border-info">
        <div class="col-md-1">S#</div>
        <div class="col">Session (W=Winter, S=Summer, M=Monsoon)</div>
        <div class="col">Coordinator</div>
        <div class="col">Class Size</div>
      </div>
    </div>
    <div class="card-body">
      <div class="row row-striped" v-for="(c, index) in offerings" :key="c.id">
        <div class="col-md-1">{{ index + 1 }}</div>
        <div class="col">
          <a :href="'#/co.detail/'+c.co_id">{{c.acad_session}}</a>
        </div>
        <div class="col">{{c.coordinator}}</div>
        <div class="col">{{c.class_size}}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseOfferings",
  props: ['cid'],
  data: function() {
    return {offerings:[]}
  },
  created: function() {
    console.log("Created CourseOfferings: ");
    let vm = this;
    if(vm.cid!=undefined){
      vm.$http.get(`offerings_of_course/${vm.cid}`)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.offerings = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body)
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error: "+error);
      });
    }
  }
};
</script>
