<!--
Component for showing the academics details of a student.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div class="card mb-2">
      <div class="card-header">
        <div class="row mb-2">
          <div class="col-md-10">
            <p class="text-danger"><b>NOTE: Some of the grades shown here may
              be pending approval by the senate. The records confirmed by the
              academic section will take precedence over anything shown here.
            </b></p>
          </div>
          <div class="col-md-2">
            <div class="form-check form-check-inline">
              <input class="form-check-input" type="checkbox" id="filterCb" v-model="showEnrolled">
              <label class="form-check-label" for="filterCb">Show only Enrolled</label>
            </div>
          </div>
        </div>
        <div class="row hdr-row border-bottom border-info">
          <div class="col-md-1">S#</div>
          <div class="col">Course</div>
          <div class="col-md-1">Enrol.</div>
          <div class="col-md-1">Enrol. status</div>
          <div class="col-md-1">Course cat.</div>
          <div class="col-md-1">Grade</div>
          <div class="col-md-1">Attd.</div>
          <div class="col-md-1"></div>
        </div>
      </div>
      <div class="card-body">
        <div v-for="(item, key,index) in enrollments" :key="index">
            <div v-if="item" class="h3 card-header"><h4>Academics for {{labelFor(SD.EnrolTypes, key)}} Courses</h4></div>
           <div v-for="(acs_item, acs_index)  in item['enrollments']" :key="acs_index">
                <div class="bg-dark text-white p-1">
                  <span class="me-2">Academic session: {{ acs_index}} </span> |
                  <span class="me-2">SGPA: {{ acs_item.sgpa }}</span> |
                  <span class="me-2">Credits registered: {{ acs_item.creg }}</span> |
                  <span class="me-2">Earned Credits: {{ acs_item.ec }}</span> |
                  <span class="me-2">Cumul. Earned Credits: {{ acs_item.cec }}</span> |
                  <span>CGPA: {{ acs_item.cgpa }}</span>
                </div>
                <div class="row row-striped" v-for="(c, index) in filterEnrolments(acs_item.courses)" :key="c.id">
                  <div class="col-md-1">{{ index + 1 }}</div>
                  <div class="col">
                    <a :href="`#/co.detail/${c.co_id}`" v-if="!isStudent && !isPlacement">{{
                      `${c.code} - ${c.title} (${c.ltp})`
                    }}</a>
                    <span v-else>{{ `${c.code} - ${c.title} (${c.ltp})` }}</span>
                    ({{labelFor(SD.OfferingStatuses, c.status)}})
                  </div>
                  <div class="col-md-1">
                    {{ labelFor(SD.EnrolTypes, c.enrol_type) }}
                  </div>
                  <div class="col-md-1">
                    {{ labelFor(SD.EnrolStatuses, c.enrol_status) }}
                  </div>
                  <div class="col-md-1">
                    {{c.cc_category }}
                  </div>
                  <div class="col-md-1">{{ c.grade }}</div>
                  <div class="col-md-1">
                    <a :href="`#/att.detail/${c.id}`" v-if="!isPlacement"
                      :class="{ 'text-danger fw-bold': isLowAttendance(c.attendance) }"
                      :title="isLowAttendance(c.attendance) ? `Below the minimum attendance of ${SD.MinAttendancePercentRequired}%` : ''"
                      >{{ c.attendance }}%</a>
                    <span v-else :class="{ 'text-danger fw-bold': isLowAttendance(c.attendance) }">{{ c.attendance }}%</span>
                  </div>
                  <div class="col-md-1">
                    <div class="dropdown me-2" v-if="show_add_withdraw(c)">
                      <button type="button" class="btn btn-primary dropdown-toggle"
                        data-bs-toggle="dropdown" aria-expanded="false">
                        Action
                      </button>
                      <div class="dropdown-menu">
                        <a class="dropdown-item" @click.prevent="dropWithdraw (c.id, 'DROP')" :disabled="!isCourseAddDropOpen(acs)">Drop Course</a>
                        <a class="dropdown-item" @click.prevent="dropWithdraw(c.id, 'WDRAW')" :disabled="!isCourseWithdrawOpen(acs)">Withdraw Course</a>
                      </div>
                    </div>
                    <div v-else></div>
                  </div>
              </div>  
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudentAcademics",
  props: {user_id: Number, enrollments: Object, acad_sessions: Array},
  data: function() {
    return {
      showEnrolled: true
    };
  },
  methods: {
    show_add_withdraw(c) {
      return (this.isAcad || this.isDean || this.isStudent) && 
        !['WDRAW', 'DROP'].includes(c.enrol_status) && 
        ['R', 'E'].includes(c.status);
    },
    dropWithdraw(id, status) {
      let vm = this;
      let st = (status == "DROP" ? "drop" : "withdraw");
      if (!confirm(`Confirm course ${st}?`)) {
        vm.setStatusMessage("User canceled the action!");
        return;
      }
      // Fetch data from an API
      vm.$http
        .get(`drop_withdraw_course/${id}/${status}`)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.setStatusMessage("dropped successfully");
            vm.$emit("reload-student-info");
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage("Error: " + error);
        });
    },
    filterEnrolments(enrolList) {
      let vm = this;
      return enrolList.filter(function (item) {
        if (vm.showEnrolled) {
          return item.enrol_status == 'ENRO';
        } else {
          return true;
        }
      });
    }
  },
};
</script>
