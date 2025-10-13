<!--
Component for Online Fees Submission.
-->
<template>
  <div class="container-fluid">
    <p class="h6">Online Fees submission:</p>
    <acad-session label="For academic session"
      v-bind:acad_session="acad_session"
      v-on:update:acad_session='acad_session=$event'/>
    <p v-if="!acad_session">Please select an academic session to proceed</p>
    <p v-else-if="!isCourseRegOpen(acad_session)" 
      class="text-dark alert alert-warning text-center">
      <b>You cann't submit fees at this moment, as course registration for {{acad_session}} is not open at this time.
      Please contact the academic section for further details.</b>
    </p>
    <div v-else>
      <div class="row mb-2">
        <div class="col">
         <div class="card mt-2">
            <div class="card-header">GENERAL INSTRUCTIONS</div>
            <div class="card-body">
              <div class="row align-items-center pb-2">
                <div class="col">
                    <ul>
                      <li>The beneficiary making a payment to F/C/I for the services/goods availed.</li>
                      <li>Bank shall not be responsible, in any way, for the quality or merchantability of any product/merchandise or any of the services related thereto, whatsoever, offered to the User by the Corporate Customer. Any disputes regarding the same or delivery of the Service or otherwise will be settled between Corporate Customer and the User and Bank shall not be a party to any such dispute. Any request for refund by the User on any grounds whatsoever should be taken up directly with the Corporate Customer and the Bank will not be concerned with such a request.</li>
                      <li>Bank takes no responsibility in respect of the services provided and User shall not be entitled to make any claim against the Bank for deficiency in the services provided by the Corporate Customer.</li>
                      <li>The User shall not publish, display, upload or transmit any information prohibited under Rule 3(2) of the Information Technology (Intermediaries guidelines) Rules, 2011.</li>
                      <li>In case of non-compliance of the terms and conditions of usage by the User, the Bank has the right to immediately terminate the access or usage rights of the User to the computer resource of the Bank and remove the non-compliant information.</li>                      
                    </ul>
                </div>
              </div>
          </div>
          </div>
        </div>
       
      </div>
        <div class="row mb-2">
              <div class="col">
                        <!-- <input
                    id="isActive"
                    v-model="Active"
                    type="checkbox"
                    class="form-check-input"
                  /> 
                   -->
                <input class="form-check-input" v-model="checked" type="checkbox" id="agree" value="agree" />
                  <label for="isActive">&nbsp;&nbsp;have read and accepted the terms and conditions stated above. (Click Check Box to proceed for payments.) </label>
                   <!-- &nbsp;&nbsp;&nbsp;<button :disabled="!checkOne" class="btn btn-outline-light btn-lg px-5 mb-1"  >Proceed </button> -->
              </div>
              <div class="col" >
                  <button :disabled="!checked" class="btn btn-primary"  aria-expanded="false" >Proceed </button>
                  <!-- <button :disabled="!Active" type="button" class="btn btn-primary " aria-expanded="false">
                      Action
                </button> -->
            </div>
      </div>
    </div>
  </div>
</template>

<script>
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import AcadSession from "./AcadSession.vue";
import _ from "lodash";

export default {
  name: "OnlineFeesSubmission",
  components: {
    "VueBootstrapTypeahead": VueBootstrapTypeahead,
    "AcadSession": AcadSession
  },
  data: function() {
    return {
      acad_session: "",
      formData: {},
      result: [],
      checked : false

    };
  },
  methods: {
  
    reset() {
      this.acad_session = "";
      console.log("Clearing Consent.");
    },   
  }
};
</script>
