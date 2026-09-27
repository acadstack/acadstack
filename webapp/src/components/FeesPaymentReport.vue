<template>
  <div class="container-fluid">
    <span class="sec-hdr">Fees Payment Report</span>
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
      <div class="col">
        <div>
          <acad-session v-bind:acad_session="search_crit.acad_session"
                label="Academic Session"
                v-on:update:acad_session='search_crit.acad_session=$event'/>
        </div>
      </div>
      <div class="col-md-2">
        <button
          class="btn btn-outline-success me-2 mt-3"
          @click="search"
          type="submit"
        >
          <i class="bi bi-search"></i>
        </button>
        <button class="btn btn-outline-danger me-2 mt-3" @click="reset" type="reset">
          <i class="bi bi-eraser"></i>
        </button>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Entry #</div>
          <div class="col-md-2">Student</div>
          <div class="col-md-2">Acad. Session</div>
          <div class="col">Payment(s)</div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="payments.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in payments" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">
            <a :href="'#/std.detail/'+s.student_id">{{ s.org_id }}</a></div>
          <div class="col-md-2">{{ s.first_name }} {{ s.last_name }}</div>
          <div class="col-md-2">{{ s.acad_session }}</div>
          <div class="col">
            <ol>
              <li v-for="(tx,) in s.txn_info" :key="tx">
                {{ txnEntry(tx) }}
                <a :href="`get_fees_txn_file/${tx.doc_file}`" target="_blank">
                  <img style="width: 60px;" :src="`get_fees_txn_file/${tx.doc_file}`" />
                </a>
              </li>
            </ol>
            
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "FeePaymentReport",
  components: {
    "AcadSession": AcadSession
  },
  data: function () {
    return {
      search_crit: {
        acad_session: "",
        degree: "",
        dept_name: "",
        entry_year: ""
      },
      payments: [],
    };
  },
  async mounted() {
    if(this.$route.name=='fees.report') {
      if (sessionStorage.PaymentData) {
        let dd = JSON.parse(sessionStorage.PaymentData);
        this.payments = dd.payments;
        this.search_crit = dd.search_crit;
      } else {
        this.reset();
      }
    } else {
      this.reset();
    }
  },
  methods: {
    txnEntry(t) {
      return `₹${t.txn_amt}/- on ${t.txn_dt} Trans. No. ${t.txn_no}. Bank ${t.bank}`;
    },
    search() {
      let vm = this;
      console.debug("Running fees payment report.");
      vm.$http
        .post("fees_payment_report", vm.search_crit)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.payments = res.data.body.data;
            if(vm.$router.currentRoute.name=='fees.report') {
              let dd = {payments: vm.payments, search_crit: vm.search_crit};
              sessionStorage.PaymentData = JSON.stringify(dd);
            }
            vm.setStatusMessage("Found "+vm.payments.length+" records");
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.log(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    reset() {
      sessionStorage.PaymentData = undefined;
      this.payments = [];
      this.search_crit = {
        acad_session: "",
        degree: "",
        dept_name: "",
        entry_year: ""
      };
    }
  }
};
</script>
