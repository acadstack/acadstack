<!--
Component for a logged-in user to change their own password.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">Change Password</div>
      <div class="card-body">
        <div class="row mb-2">
          <div class="col-md-6">
            <div class="mb-2">
              <label for="old_pw">Current Password:</label>
              <div class="input-group">
                <input id="old_pw" :type="showOld ? 'text' : 'password'" class="form-control"
                  v-model="old_password" aria-label="Current password" aria-describedby="btnShowOld">
                <button class="btn btn-outline-primary" type="button" id="btnShowOld"
                  @click="showOld = !showOld">{{ showOld ? "Hide" : "Show" }}</button>
              </div>
            </div>
            <div class="mb-2">
              <label for="new_pw">New Password:</label>
              <div class="input-group">
                <input id="new_pw" :type="showNew ? 'text' : 'password'" class="form-control"
                  v-model="new_password" aria-label="New password" aria-describedby="btnShowNew">
                <button class="btn btn-outline-primary" type="button" id="btnShowNew"
                  @click="showNew = !showNew">{{ showNew ? "Hide" : "Show" }}</button>
              </div>
            </div>
            <div class="mb-2">
              <label for="new_pw2">Confirm New Password:</label>
              <input id="new_pw2" :type="showNew ? 'text' : 'password'" class="form-control"
                v-model="confirm_password" aria-label="Confirm new password">
            </div>
            <div class="mb-2">
              <button type="button" class="btn btn-outline-success me-4" @click="changePassword">Submit</button>
              <a href="#/" class="btn btn-outline-secondary">Cancel</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ChangePassword",
  data() {
    return {
      old_password: "",
      new_password: "",
      confirm_password: "",
      showOld: false,
      showNew: false
    };
  },
  methods: {
    async changePassword() {
      let vm = this;
      if (!vm.old_password || !vm.new_password) {
        vm.setStatusMessage("Please fill in all fields.");
        return;
      }
      if (vm.new_password !== vm.confirm_password) {
        vm.setStatusMessage("New password and confirmation do not match.");
        return;
      }
      await vm.doHttp(false, "change_password",
        { old_password: vm.old_password, new_password: vm.new_password },
        (msg) => {
          vm.setStatusMessage(msg);
          vm.old_password = vm.new_password = vm.confirm_password = "";
          vm.$router.push("/");
        },
        vm.setStatusMessage);
    }
  }
};
</script>
