<!--
Component for the application's navigation bar.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <nav class="navbar navbar-expand-lg" style="background-color: #b8d6d9;" data-bs-theme="light" v-bind:class=" { 'navbarOpen': show }">
      <a class="navbar-brand ms-2" href="#">
        <img :src="logo" alt="Logo" width="30" height="30" class="d-inline-block align-text-top">
        AcadStack</img>
      </a>
      <button
        class="navbar-toggler"
        type="button"
        data-toggle="collapse"
        data-target="#navbarCollapse"
        aria-controls="navbarCollapse"
        aria-expanded="false"
        aria-label="Toggle navigation"
        @click.stop="toggleNavbar()"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarCollapse" v-bind:class="{ 'show': show }">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li role="button" class="nav-item dropdown" v-for="[m, items] in Object.entries(navItems.menus)" :key="m">
            <a
              class="nav-link dropdown-toggle"
              href="#" role="button"
              data-bs-toggle="dropdown" aria-expanded="false"
            >{{m}}</a>
            <div class="dropdown-menu">
              <div v-for="mi in items" :key="mi.label">
                <a class="dropdown-item" :href="mi.href">{{ mi.label }}</a>
              </div>
            </div>
          </li>
          <li class="nav-item" v-for="l in navItems.links" :key="l.label">
            <a class="nav-link" :href="l.href">{{l.label}}</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#/help">Help</a>
          </li>
        </ul>
        <span class="me-2" v-if="user.login_id != undefined">
          <span class="navbar-text me-1" style="font-size: small">{{user.login_id}} ({{user.role_name}})</span>
          <button class="btn btn-outline-danger" type="button" @click="logout">
            <i class="bi bi-power"></i>
          </button>
        </span>
      </div>
    </nav>
  </div>
</template>

<script>
import logo from '@/assets/acadstack-logo-small.png'
export default {
  name: "Navbar",
  props: ["navItems", "user"],
  data() {
    return {
      show: true,
      logo
    };
  },
  methods: {
    logout() {
      console.log("Clicked logged out.");
      this.$emit("logout-user");
    },
    toggleNavbar() {
      this.show = !this.show;
    }
  }
};
</script>

