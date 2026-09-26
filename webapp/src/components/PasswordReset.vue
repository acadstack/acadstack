<!--
Component for password reset screen.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">Request Password Reset</div>
      <div class="card-body">
        <div class="row mb-2">
          <div class="col-md-6">
            <div class="mb-2">
              <label for="login">Your Login ID:</label>
              <input type="text" class="form-control" v-model="user.login_id"
                id="login" placeholder="Your login ID" />
            </div>
            <div class="mb-2">
              <label for="email">Registered Email:</label>
              <input type="email" class="form-control" v-model="user.email"
                id="email" placeholder="Your email address" />
            </div>
            <div class="mb-2">
              <button type="button" class="btn btn-outline-primary me-4" @click="requestKey">Request Reset</button>
              <a href="#/login" class="btn btn-outline-danger">Cancel</a>
            </div>
          </div>
          <div class="col-md-6" v-show="showKey">
            <div class="mb-2" v-show="!showNewPass">
              <label for="passwd">New Password:</label>
              <div class="input-group">
                <input id="passwd" type="password" class="form-control" v-model="user.new_password" aria-label="Your new password" aria-describedby="btnShow">
                <button class="btn btn-outline-primary" type="button" id="btnShow" @click="showNewPass=!showNewPass">Show</button>
              </div>
            </div>
            <div class="mb-2" v-show="showNewPass">
              <label for="passwd2">New Password:</label>
              <div class="input-group">
                <input id="passwd2" type="text" class="form-control" v-model="user.new_password" aria-label="Your new password" aria-describedby="btnHide">
                <button class="btn btn-outline-primary" type="button" id="btnHide" @click="showNewPass=!showNewPass">Hide</button>
              </div>
            </div>
            <div class="mb-2">
              <label for="rsk">Reset Key:</label>
              <input id="rsk" type="text" class="form-control" placeholder="Confirmation key" v-model="user.key_code" aria-label="Confirmation key sent to your email." aria-describedby="btnAdd">
            </div>
            <button class="btn btn-outline-success" type="button" id="btnAdd" @click="passwordReset">Submit</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "PasswordReset",
  data: function() {
    return { user: {}, showKey: false, showNewPass: false };
  },
  methods: {
    requestKey() {
      let vm = this;
      console.log("Requesting password reset key.");
      vm.$http.post('gen_prk', vm.user)
      .then(function (res) {
        console.log(res);
        if (res.data.status == "OK") {
          vm.showKey = true;
          vm.setStatusMessage(res.data.body);
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    },
    passwordReset() {
      let vm = this;
      console.log("Password reset for user.");
      vm.$http.post('reset_password', vm.user)
      .then(function (res) {
        console.log(res);
        if (res.data.status == "OK") {
          vm.$router.push('/login');
        }
        vm.setStatusMessage(res.data.body);
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    },
    reset() {
      this.user = {};
      this.showKey =  this.showNewPass = false
      console.log("Clearing details.");
    }
  }
};
</script>
