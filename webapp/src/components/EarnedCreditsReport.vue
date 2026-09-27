<template>
  <div class="container-fluid">
    <span class="sec-hdr">Check Total Credits Earned</span>
    <div class="row mb-2">
      <div class="col">
        <label for="deg">Degree</label>
        <select id="deg" class="form-select" v-model.trim="search_crit.degree">
          <option v-for="cs in SD.Degrees" v-bind:value="cs.id" :key="cs.id">
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col">
        <label for="dept">Dept.</label>
        <select id="dept" class="form-select" v-model.trim="search_crit.dept_name">
          <option
            v-for="cs in SD.Departments"
            v-bind:value="cs.id"
            :key="cs.id"
          >
            {{ cs.value }}
          </option>
        </select>
      </div>
      <div class="col">
        <label for="ent_yr">Entry Year</label>
        <input
          id="ent_yr"
          class="form-control"
          type="number"
          min="2010"
          max="2099"
          v-model.trim="search_crit.entry_year"
          placeholder="YYYY (e.g., 2019)"
        />
      </div>
    </div>
    <div class="row mb-2">
      <div class="col">
        <div>
          <label for="minc">Min. Credits</label>
          <input id="minc" class="form-control" type="number" v-model.trim="search_crit.min_credits" min="0"/>
        </div>
      </div>
      <div class="col">
        <div>
          <label for="maxc">Max. Credits</label>
          <input id="maxc" class="form-control" type="number" v-model.trim="search_crit.max_credits" min="0"/>
        </div>
      </div>
      <div class="col">
        <div>
          <acad-session v-bind:acad_session="search_crit.acad_session"
                label="Academic Session"
                v-on:update:acad_session='search_crit.acad_session=$event'/>
        </div>
      </div>
      <div class="col">
        <div>
          <label for="exclCourse">Exclude Course(s)</label>
          <input id="exclCourse" class="form-control" type="text" v-model.trim="search_crit.exclude_course" maxlength="6" placeholder="E.g. II302"/>
        </div>
      </div>
      <div class="col">
        <button class="btn btn-outline-success me-2 mt-3"
          @click="search" type="submit">
          <i class="bi bi-search"></i>
        </button>
        <button class="btn btn-outline-danger me-2 mt-3" @click="reset" type="reset">
          <i class="bi bi-eraser"></i>
        </button>        
        <button v-if="isAcad || isDean" class="btn btn-outline-info mt-3" @click="email_students" type="button">  
          <i class="bi bi-envelope"></i>
        </button>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Session</div>
          <div class="col-md-2">Entry No.</div>
          <div class="col-md-2">Name</div>
          <div class="col">Email</div>
          <div class="col-md-2">Total Credits</div>
          <div v-if="isAcad || isDean" class="col-md-1">
            <div class="form-check form-check-inline">
              <input type="radio" id="rb1" value="include" 
                v-model="search_crit.mark_type"
                class="form-check-input">
              <label class="form-check-label" 
              for="rb1">Include</label>
            </div>
            <div class="form-check form-check-inline">
              <input type="radio" id="rb2" 
              value="exclude" v-model="search_crit.mark_type"
              class="form-check-input">
              <label class="form-check-label" for="rb2">Exclude</label>
            </div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="credits.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in credits" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">{{s.acad_session}}</div>
          <div class="col">
            <a :href="'#/std.detail/'+s.user_id">{{s.entry_no}}</a>
          </div>
          <div class="col-md-2">{{ s.first_name }} {{s.last_name}}</div>
          <div class="col">{{s.email}}</div>
          <div class="col-md-2">{{s.credits}}</div>
          <div v-if="isAcad || isDean" class="col-md-1">
            <input class="form-check-input" type="checkbox" 
              v-model="search_crit.marked_items" :value="s.user_id"/>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "EarnedCreditsReport",
  components: {
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      search_crit: {
        report_name: "EARNED_CREDITS",
        degree: "",
        dept_name: "",
        entry_year: "",
        acad_session: "",
        min_credits: 0,
        max_credits: 30,
        marked_items: [],
        mark_type: "exclude",
        exclude_course: "II301"
      },
      credits: [],
    };
  },
  mounted: function() {
    if(this.$route.name=='credits.earned') {
      if (sessionStorage.CredEarnedData) {
        let dd = JSON.parse(sessionStorage.CredEarnedData);
        this.credits = dd.credits;
        this.search_crit = dd.search_crit;
      } else {
        this.reset();
      }
    } else {
      this.reset();
    }
  },
  methods: {
    search() {
      let vm = this;
      console.log("Searching Credits");
      vm.$http
        .post("credits_earned", vm.search_crit)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.credits = res.data.body.data;
            if(vm.$router.currentRoute.name=='credits.earned') {
              let dd = {credits: vm.credits, search_crit: vm.search_crit};
              sessionStorage.CredEarnedData = JSON.stringify(dd);
            }
            vm.setStatusMessage("Found "+vm.credits.length+" records");
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    email_students() {
      let vm = this;
      if (!confirm("Do you want to send emails?")) {
        return;
      }
      vm.$http
        .post("notify_credit_violation", vm.search_crit)
        .then(function (res) {
          vm.setStatusMessage(res.data.body);
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      sessionStorage.CredEarnedData = undefined;
      this.search_crit = {
        report_name: "EARNED_CREDITS",
        degree: "",
        dept_name: "",
        entry_year: "",
        acad_session: "",
        min_credits: 0,
        max_credits: 30,
        marked_items: [],
        mark_type: "exclude",
        exclude_course: "II301"
        };
      this.credits = [];
    },
  },
};
</script>
