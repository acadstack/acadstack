<template>
    <div>
        <label for="crs_sess">{{label}} 
            <small class="text-primary" v-if="isOtherAcadSession||isEdit">(YYYY-X, here 'X' can be: I = First Semester, II = Second Semester, S=Summer and T1, T2 etc. for trimesters.)</small>
        </label>
        <div class="input-group">
            <select v-if="!isEdit && !isOtherAcadSession" class="form-select" 
                id="crs_sess" v-model.trim="my_acad_session" :disabled="disabled">
                <option
                v-for="cs in SD.AcademicSessions"
                v-bind:value="cs.id"
                :key="cs.id"
                >{{cs.id}} : {{ cs.value }}</option>
            </select>
            <input v-else
                type="text"
                class="form-control"
                id="crs_sess"
                :disabled="disabled"
                v-model.trim="my_acad_session"
                placeholder="YYYY-X"
                aria-describedby="acadSessHelp"
                />
            <div v-if="!isEdit" class="input-group-text form-check-inline">
                <input class="form-check-input" type="checkbox" id="cb1" v-model="isOtherAcadSession" :disabled="disabled">
                <label class="form-check-label" for="cb1">Other</label>
            </div>
        </div>
        <small v-if="isOtherAcadSession" id="acadSessHelp" class=" text-primary">
            <b>NOTE: </b>
            <ul>
                <li v-for="x in SD.AcademicSessions" :key="x.id">
                <b>{{x.id}}</b> is {{x.value}}.
                </li>
            </ul>
        </small>
    </div>                  
</template>
<script>
export default {
  name: "AcadSession",
  props: ["label", "acad_session", "isEdit", "disabled"],
  data: function() {
    return {
        isOtherAcadSession: false,
        my_acad_session: ""
    };
  },
  watch: {
    // Whenever acad_session changes, this function will run
    my_acad_session: function (valNew) {
        this.$emit('update:acad_session', valNew)
    }
  },
  mounted() {
      if (this.label == undefined || this.label == "") {
          this.label = "Academic Session"
      }
      this.my_acad_session = this.acad_session;
      console.log(`acad_session=${this.acad_session}`);
  }
};
</script>