<script setup>
import { RouterView } from 'vue-router'
import Navbar from "./components/Navbar.vue";
</script>

<template>
  <div id="appMain" class="container-fluid">
    <Navbar v-bind:navItems="navData" v-bind:user="currentUser" v-on:logout-user="onLogout"/>
    <br/>
    <div style="z-index: 999;" class="overflow-auto position-fixed top-50 start-50 translate-middle">
      <div v-if="statusMsg != ''" class="alert alert-warning alert-dismissible fade show" role="alert">
        {{statusMsg}}
        <button @click="setStatusMessage('')" type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    </div>
    
    <router-view v-if="initDone" v-on:user-logged-in="onLogin" :key="$route.fullPath"></router-view>
    <p v-else>Loading...</p>

  </div>
</template>
<script>
export default {
  setup() {
    
  },
  components: {
    Navbar,
    RouterView
  },
  data: function() {
    return {
      navData:{menus:{}, links:[]},
      initDone: false,
      user: {},
      statusMessage: '',
      staticData: {},
      viewOnlyFlag: false,
      eventsStatusMap: []
    }
  },
  async mounted() {
    const vm = this
    vm.setupHttpInterceptors()
    vm.attachRouteGuardsForAuth()
    await vm.initSession();
    vm.initDone = true;
  },
  methods: {
    setupHttpInterceptors() {
      let vm = this;
      // Add AJAX interceptors
      vm.$http.interceptors.request.use(function (config) {
        // Do something before request is sent
        vm.statusMessage = "Please wait..."
        return config;
      }, function (error) {
        // Do something with request error
        return Promise.reject(error);
      });
      vm.$http.interceptors.response.use(function (response) {
        // Any status code that lie within the range of 2xx cause this function to trigger
        // Do something with response data
        vm.statusMessage = "";
        return response;
      }, function (error) {
        // Any status codes that falls outside the range of 2xx cause this function to trigger
        // Do something with response error
        vm.statusMessage = "Error occurred: " + error;
        return Promise.reject(error);
      });
      console.log("Setup the HTTP request interceptors.")
    },
    attachRouteGuardsForAuth() {
      const vm = this
      // Attach auth checking navigation guard
      vm.$router.beforeEach((to, from, next) => {
          try {
              const rootComp = vm.$root
              console.log("Path=" + to.path + ". authenticated=" + rootComp.authenticated);
              if (to.path === "/login" || to.path === "/help"
                  || to.path === "/pass.reset") {
                  next()
              } else if (!rootComp.authenticated) {
                  next("/login")
              } else {
                  next()
              }
          } catch (error) {
              console.log("Error: " + error)
          }

      })
      console.log("Attached route guard for auth checks.")
    },
    async get_events_status() {
      let vm = this;
      console.debug("Getting events statuses.");
      try {
        let res = await vm.$http.get('./open_events');
        if (res.data.status == "OK") {
          vm.eventsStatus = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when getting academic events status.");
      }
    },
    async initSession() {
      let vm = this;
      try {
        console.log("Loading logged in user if any.");
        let res = await vm.$http.get('./current_user');
        if (res.data.status == "OK") {
          await vm.onLogin(res.data.body);
        } else {
          console.log("No logged in user found.");
          await vm.onLogout();
          vm.setStatusMessage("No logged in user found.");
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when getting current user.");
      }
    },
    async getStaticData() {
      let vm = this;
      console.log("Loading static data.");
      try {
        let res = await vm.$http.get('./get_static_data')
        if (res.data.status == "OK") {
          vm.setStaticData(res.data.body);
          if (res.data.body["AcademicSessions"].length == 0) {
            vm.setStatusMessage("A valid current academic session is not configured. Some features may not work properly.");
          }
        } else {
          vm.setStatusMessage("Failed to load static data: "+res.data.body);
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when getting static data.");
      }
    },
    async onLogin(sessData) {
      console.log("User logged IN.");
      this.setCurrentUser(sessData.user);
      this.isOAuth = sessData.user.is_oauth !== undefined && sessData.user.is_oauth;
      await this.getStaticData();
      await this.get_events_status();
      if (sessData.nav !== undefined) {
        this.navData = sessData.nav;
      }
      
      if (this.$route.name == "login") {
        this.$router.push('/');
      }
    },
    async onLogout() {
      console.log("User logged OUT.");
      sessionStorage.clear();
      localStorage.clear();
      let vm = this;
      vm.setCurrentUser({});
      vm.navData = {menus:{}, links:[]};
      try {
        let res = await this.$http.get('logout')
        if (res.data.status == "OK") {
          console.log("User logged out.");
          vm.$router.push('/login');
          if (vm.isOAuth) {
            vm.setStatusMessage("You are logged out only from AcadStack, and not your Google account!");
          }
        } else {
          console.log("Logout failed: "+res.data.body);
        }
      } catch(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when logging out.");
      }
    }

  }
}
</script>