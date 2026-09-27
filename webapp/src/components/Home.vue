<template>
  <div class="container">
    <p class="h3">
      Academic Information Management System.
    </p>
    <p class="h5 text-danger fw-bold">
      Please DO NOT edit or manipulate the URLs or requests when using this application.
      Doing so may lock your account.
    </p>
    Please proceed by choosing a menu item from the top bar.
    <p>
    <B>Before contacting @acadstack_help for any issues, 
      please check the <a href="https://bit.ly/AcadStackGuide" target="_blank">User Guide</a> for solution.</B>
    </p>
    <div class="card" v-if="isAcad||isSuperuser">
      <div class="card-header">Online Users <b>({{active_users.length}})</b></div>
      <ul class="list-group list-group-flush">
        <li class="list-group-item" v-for="(u, idx) in active_users" :key="u">{{idx+1}}) {{u}}</li>
      </ul>
    </div>
    <div v-if="isStudent">
      <b>NOTE:</b>
      <ul>
        <li>Please directly contact the course instructor for any changes to your enrolment requests.</li>
        <li>We have not yet fully imported your past enrolments data into this system. You may not get to see grades for some of your past courses.</li>
      </ul>
    </div>
  </div>
</template>

<script>

export default {
  name: "Home",
  data: function() {
    return { active_users: [] };
  },
  mounted() {
    // Alias 'this' for accessing in promises
    var vm = this;
    if (!vm.isSuperuser && !vm.isAcad) return;

    return vm.$http.get('./auc')
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.active_users = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when getting active users.");
      });
  },
};
</script>
