<template>
  <div :class="showLookup?'btn-group':'input-group'">
    <div class="form-control" v-if="!showLookup">{{
      memberDisp(selectedItem)
    }}</div>
    <vue-bootstrap-typeahead
      v-else
      :disabled="disabled"
      :placeholder="placeholder||'Lookup person'"
      :data="persons"
      :serializer="memberDisp"
      @mta-item-selected="onMemberSelect"
      @mta-input-changed="debouncedQuery"
    />
    <button :disabled="disabled"
        class="btn btn-outline-info"
        type="button"
        @click="showLookup = !showLookup"
      >
        {{ showLookup ? "Show" : "Lookup" }}
    </button>
  </div>
</template>
<script>
import VueBootstrapTypeahead from "./VueBootstrapTypeahead.vue";
import _ from "lodash";
export default {
  name: "PersonLookupField",
  props: ["person", "isView", "disabled", "personRole", "placeholder", "reset"],
  components: {
    VueBootstrapTypeahead: VueBootstrapTypeahead,
  },
  data: function () {
    return {
      showLookup: false,
      persons: [],
      selectedItem: {},
    };
  },
  watch: {
    reset: function() {
      this.showLookup = false;
      this.selectedItem = {};
      this.persons = [];
    }
  },
  mounted() {
    this.showLookup = !this.isView;
    this.selectedItem = this.person;
    console.log(`personRole=${this.personRole} isView=${this.isView} showLookup=${this.showLookup}`);
    console.log("Person="+JSON.stringify(this.person))
  },
  methods: {
    initData() {
      return {
            showLookup: false,
            persons: [],
            selectedItem: {},
          };
    },
    debouncedQuery: _.debounce(async function(inp) {
      
      if (this.personRole == "STU") {
        if (_.isEmpty(inp) || inp.length < 7) {
          console.log("At least first 7 characters of entry no." + inp);
        } else {
          await this.lookupStudents(inp);
        }
      } else {
        if (_.isEmpty(inp) || inp.length < 3) {
          console.log("Min. 3 charaters needed. Ignored.");
          return;
        }
        await this.lookupInstructor(inp);
      }
    }, 400),
    async lookupStudents(qry) {
      let vm = this;
      await vm.doHttp(true, `student_lookup/${qry}`, null,
        (b)=>{vm.persons = b}, (e)=>{console.log(e)})
    },
    async lookupInstructor(qry) {
      let vm = this;
      await vm.doHttp(true, `instructor_lookup/${qry}`, null,
        (b)=>{vm.persons = b}, (e)=>{console.log(e)})
    },
    memberDisp(s) {
      if (s !== undefined && s.first_name !== undefined) {
        if (this.personRole == "STU") {
          return `${s.first_name} ${s.last_name} (${s.org_id})`;
        } else {
          return `${s.first_name} ${s.last_name} (${s.dept_name})`;
        }
      } else {
        return "--";
      }
    },
    onMemberSelect(item) {
      this.showLookup = false;
      this.selectedItem = item;
      this.$emit("personSelected", item);
    },
  },
};
</script>