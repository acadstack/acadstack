<!--
Component for searching users.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <h5>Find Users</h5>
    <form @submit.prevent="find(false)">
      <div class="row mb-2">
        <div class="col">
          <div>
            <label for="st_role">Role</label>
            <select class="form-select" id="st_role" v-model="user.role">
              <option v-for="x in SD.UserRoles" v-bind:value="x.id" :key="x.id">{{ x.value }}</option>
            </select>
          </div>
        </div>
        <div class="col-md-4">
          <div>
            <label for="st_dept">Department</label>
            <select class="form-select" id="st_dept" v-model="user.dept_name">
              <option
                v-for="cs in SD.Departments"
                v-bind:value="cs.id"
                :key="cs.id"
              >{{ cs.value }}</option>
            </select>
          </div>
        </div>
        <div class="col-md-1">
          <div>
            <label for="st_rollno">Org. ID</label>
            <input type="text" class="form-control" id="st_rollno" v-model="user.org_id" />
          </div>
        </div>
        <div class="col-md-2">
          <div>
            <label for="st_firstnm">First Name</label>
            <input type="text" class="form-control" id="st_firstnm" v-model="user.first_name" />
          </div>
        </div>
        <div class="col-md-2">
          <div>
            <label for="st_lastnm">Last Name</label>
            <input type="text" class="form-control" id="st_lastnm" v-model="user.last_name" />
          </div>
        </div>
        <div class="col-md-2">
          <div class="mt-4">
            <button class="btn btn-outline-success me-2" type="submit">
              <i class="bi bi-search"></i>
            </button>
            <button class="btn btn-outline-danger" @click="reset" type="reset">
              <i class="bi bi-eraser"></i>
            </button>
          </div>
        </div>
      </div>
    </form>

    <div class="card">
      <div class="card-header">
        Results
        <span class="float-end">
          <button
            class="btn btn-outline-info btn-sm me-4"
            v-if="user.pg_no > 1"
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
          <div class="col">Name</div>
          <div class="col">Role</div>
          <div class="col">Dept.</div>
          <div class="col">Org. ID</div>
          <div class="col">Photo</div>
          <div class="col-md-1" v-if="canDelete">
            <button class="btn btn-outline-danger btn-sm" @click="deleteMarked">Delete</button>
          </div>
        </div>
        <p v-if="results.users.length == 0">Nothing to show yet!</p>
        <div class="row row-striped mt-4" v-for="(r, i) in results.users" :key="r.id">
          <div class="col-md-1">{{(results.pg_no - 1) * results.pg_size + i + 1}}</div>
          <div class="col">
            <a :href="'#/user.detail/'+r.id">{{r.first_name + " " + r.last_name}}</a>
          </div>
          <div class="col">{{labelFor(SD.UserRoles, r.role)}}</div>
          <div class="col">{{labelFor(SD.Departments, r.person.dept_name)}}</div>
          <div class="col">{{r.person.org_id}}</div>
          <div class="col">
            <img
              v-if="r.photo"
              :src="'get_image/'+r.photo"
              alt="Face photo"
              class="img-thumbnail"
              style="width: 250px;"
            />
            <i v-else class="bi bi-person-bounding-box h3"></i>
          </div>
          <div class="col-md-1" v-if="canDelete">
            <input class="form-check-input" :value="r.id" type="checkbox" v-model="markedItems" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "User",

  data: function() {
    return {
      user: { pg_no: 1 },
      results: { users: [], has_next: false },
      markedItems: []
    };
  },
  computed: {
    canDelete() {
      return this.markedItems.length > 0 && this.hasPermission("user.delete");
    }
  },
  beforeRouteUpdate(to, from, next) {
    console.log("User.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  created: function() {
    console.log("Creating UserSearch");
    // Alias 'this' for accessing in promises
    // var vm = this;
  },
  mounted: function() {
    if (sessionStorage.user){
      this.user = JSON.parse(sessionStorage.user);
    }
    if (sessionStorage.myUserS) {
      this.results = JSON.parse(sessionStorage.myUserS);
    } else {
      this.results = { users: [], has_next: false };
    }
  },
  methods: {
    deleteMarked() {
      let vm = this;
      if (
        confirm("Deleted all selected " + vm.markedItems.length + " items?")
      ) {
        let vm = this;
        vm.$http
          .post("user_delete", {ids: vm.markedItems})
          .then(function(res) {
            if (res.data.status == "OK") {
              vm.markedItems = [];
              vm.find(false); // Refresh results from server
            } else {
              vm.setStatusMessage(res.data.body);
            }
          })
          .catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when contacting the server.");
          });
      } else {
        vm.markedItems = [];
      }
    },
    next_pg() {
      this.user.pg_no += 1;
      this.find(true);
    },
    prev_pg() {
      this.user.pg_no -= 1;
      this.find(true);
    },
    find(is_paging) {
      let vm = this;
      if (!is_paging) vm.user.pg_no = 1;
      sessionStorage.user = JSON.stringify(vm.user);
      vm.results.users = [];
      vm.$http
        .post("user_find", vm.user)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.results = res.data.body;
            sessionStorage.myUserS = JSON.stringify(vm.results);
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      this.results = { users: [], has_next: false };
      this.user = { pg_no: 1 };
      sessionStorage.myUserS = undefined;
      sessionStorage.user = undefined;
    }
  }
};
</script>
