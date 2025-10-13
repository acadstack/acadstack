<template>
  <div class="input-group">
    <span v-if="label" class="input-group-text">{{label}}</span>
    <select
      id="mdcs"
      :disabled="viewOnly"
      class="form-select"
      v-model="selStudent"
    >
      <option
        v-for="cs in myStudents"
        v-bind:value="cs.user_id"
        :key="cs.user_id"
      >
        {{ cs.first_name }} {{ cs.last_name }} 
        -- {{cs.org_id}}
        ({{ cs.dept_name }},
        {{ cs.year_of_entry }})
      </option>
    </select>
  </div>
</template>
<script>
export default {
  name: "MyDcStudents",
  props:["student", "label"],
  data: function () {
    return {
        selStudent: {},
        myStudents: [],
    };
  },
  watch: {
    // Whenever student changes, this function will run
    selStudent: function (valNew) {
      this.$emit("student-selected", valNew);
    },
  },
  async mounted() {
    let vm = this;
    console.debug("Mounting MyDcStudents. viewOnly="+vm.viewOnly);
    await vm.doHttp(true, "my_dc_students", null, 
      (body)=>{
        vm.myStudents = body;
        vm.selStudent = vm.student
      }, vm.setStatusMessage);
    
  },
};
</script>