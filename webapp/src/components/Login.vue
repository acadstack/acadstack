<!--
Component for login screen.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="row mb-2">
      <div class="col-md-4">
        <div class="card shadow-lg rounded">
          <div class="card-header">Login</div>
          <div class="card-body">
            <form @submit.prevent="authenticate">
              <div class="mb-2">
                <label for="login">Login ID:</label>
                <input type="text" class="form-control" v-model="user.login_id"
                  id="login" placeholder="Your login ID" />
              </div>
              <div class="mb-2">
                <label for="passwd">Password:</label>
                <input type="password" class="form-control" v-model="user.password"
                  id="passwd" placeholder="Your password" />
              </div>
              <div class="mb-2">
                <button type="submit" class="btn btn-outline-primary me-4">Submit</button>
                <button type="reset" class="btn btn-outline-danger me-4">Cancel</button>
              </div>
              <div class="mb-2">
                <a class="mt-4 me-4" href="#/pass.reset">[Password Reset]</a>
                <a class="mt-4" href="/acadstack">[All Login Options]</a>
              </div>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <p class="lead">A System For Managing Academic Information</p>
        <p class="text-center fw-bold text-danger">
            By proceeding with the login you agree to the 
            <a href="http://bit.ly/AcadStack_Terms" target="_blank">terms of use</a> of this service.
        </p>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "Login",
  data: function() {
    return { user: {} };
  },
  mounted: function() {
    console.log("Clearing the local session storage.");
    sessionStorage.clear();
    localStorage.clear();
  },
  methods: {
    authenticate() {
      let vm = this;
      console.log("Authenticating user.");
      vm.$http.post('login', vm.user)
      .then(function (res) { 
        // console.log(res);
        if (res.data.status == "OK") {
          vm.$emit("user-logged-in", res.data.body);
        } else {
          console.log("Emitting status-message event: "+res.data.body);
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    },
    reset() {
      this.user = {};
      console.log("Clearing user details.");
    }
  }
};
</script>
