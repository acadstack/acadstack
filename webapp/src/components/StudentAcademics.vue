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
                  <span class="badge bg-warning text-dark ms-2" v-if="acs_item.withheld">Result withheld{{ acs_item.hold_reason ? `: ${acs_item.hold_reason}` : "" }}</span>
                  <a class="btn btn-sm btn-light ms-2" v-if="isStudent && acs_item.declared && !acs_item.withheld"
                    :href="`download_sem_grade/${acs_index}/${org_id}/${key}`">Grade sheet</a>
                  <button type="button" class="btn btn-sm btn-light ms-2" v-if="hasPermission('results.withhold')"
                    @click="resultHold(acs_index, !acs_item.withheld)">
                    {{ acs_item.withheld ? "Release result" : "Withhold result" }}</button>
                </div>
                <div class="row row-striped" v-for="(c, index) in filterEnrolments(acs_item.courses)" :key="c.id">
                  <div class="col-md-1">{{ index + 1 }}</div>
                  <div class="col">
                    <a :href="`#/co.detail/${c.co_id}`" v-if="hasPermission('offerings.edit')">{{
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
                    <a :href="`#/att.detail/${c.id}`" v-if="hasPermission('attendance.view') || isStudent">{{ c.attendance }}%</a>
                    <span v-else>{{ c.attendance }}%</span>
                  </div>
                  <div class="col-md-1">
                    <div class="dropdown me-2" v-if="show_add_withdraw(c)">
                      <button type="button" class="btn btn-primary dropdown-toggle"
                        data-bs-toggle="dropdown" aria-expanded="false">
                        Action
                      </button>
                      <div class="dropdown-menu">
                        <a class="dropdown-item" @click.prevent="dropWithdraw (c.id, 'DROP')" :class="{disabled: !canDropWithdraw(c, acs_index, 'DROP')}">Drop Course</a>
                        <a class="dropdown-item" @click.prevent="dropWithdraw(c.id, 'WDRAW')" :class="{disabled: !canDropWithdraw(c, acs_index, 'WDRAW')}">Withdraw Course</a>
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
  props: {user_id: Number, org_id: String, enrollments: Object, acad_sessions: Array},
  data: function() {
    return {
      showEnrolled: true
    };
  },
  methods: {
    show_add_withdraw(c) {
      return (this.hasPermission('enrolments.edit:any') || this.isStudent) && 
        !['WDRAW', 'DROP'].includes(c.enrol_status) && 
        ['R', 'E'].includes(c.status);
    },
    /** Mirrors validate_enrolment_change: an audited course is dropped in the withdraw window. */
    canDropWithdraw(c, acs, status) {
      if (this.hasPermission('enrolments.edit:any')) return true;
      if (status == 'WDRAW' || c.enrol_type == 'A') return this.isCourseWithdrawOpen(acs);
      return this.isCourseAddDropOpen(acs);
    },
    dropWithdraw(id, status) {
      let vm = this;
      let st = (status == "DROP" ? "drop" : "withdraw");
      if (!confirm(`Confirm course ${st}?`)) {
        return;
      }
      // Fetch data from an API
      vm.$http
        .post(`drop_withdraw_course/${id}/${status}`)
        .then(function(res) {
          if (res.data.status == "OK") {
            vm.$emit("reload-student-info");
            vm.setSuccessMessage(res.data.body);
          } else {
            vm.setStatusMessage(res.data.body, 'error');
          }
        })
        .catch(function(error) {
          console.log(error);
          vm.setStatusMessage(vm.httpErrorMessage(error), 'error');
        });
    },
    async resultHold(acad_session, hold) {
      let vm = this;
      let reason = "";
      if (hold) {
        reason = prompt(`Reason for withholding the result of ${acad_session}:`);
        if (reason === null) return;
      } else if (!confirm(`Release the result of ${acad_session}?`)) {
        return;
      }
      await vm.doHttp(false, "result_hold",
        {user_id: vm.user_id, acad_session: acad_session, hold: hold, reason: reason},
        (msg) => {
          vm.setSuccessMessage(msg);
          vm.$emit("reload-student-info");
        }, (msg) => vm.setStatusMessage(msg, 'error'));
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
