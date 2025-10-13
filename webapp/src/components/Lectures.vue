<template>
  <div class="container-fluid">
    <span class="sec-hdr">Course lectures in academic session</span>
    <div class="row mb-2">
      <div class="col float-start">
        <input v-model.trim="session" maxlength="7" placeholder="YYYY-S" />
        <button
          class="btn btn-outline-success me-2"
          @click="search"
          type="submit"
        >
          <i class="bi bi-search"></i>
        </button>
        <button class="btn btn-outline-danger" @click="reset" type="reset">
          <i class="bi bi-eraser"></i>
        </button>
        <div
          v-if="!v$.session.required && v$.session.$dirty"
          class="text-danger"
        >
          This is a requird feild
        </div>
        <div
          v-else-if="!v$.session.validsession && v$.session.$dirty"
          class="text-danger"
        >
          Session is invalid
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="row hdr-row">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Session (W=Winter, S=Summer, M=Monsoon)</div>
          <div class="col-md-1">Code</div>
          <div class="col">Title</div>
          <div class="col-md-2">No of Lectures</div>
        </div>
      </div>
      <div class="card-body">
        <p v-if="lecture.length == 0">Nothing to show yet!</p>
        <div class="row row-striped" v-for="(s, i) in lecture" :key="s.id">
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">{{s.acad_session}}</div>
          <div class="col-md-1">{{s.code}}</div>
          <div class="col">{{s.title}}</div>
          <div class="col-md-2">{{s.lecture}}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import useVuelidate from '@vuelidate/core'
import { required } from '@vuelidate/validators'
export default {
  setup () {
    return { v$: useVuelidate() }
  },
  name: "Lectures",
  data: function() {
    return {
      session: "",
      lecture: [],
    };
  },
  methods: {
    search() {
      let vm = this;
      vm.v$.session.$touch();
      if (vm.v$.session.$invalid) {
        return;
      } else {
        console.log("Searching lecture");
        vm.$http
          .get(`course_lect_in_session/${vm.session}`)
          .then(function(res) {
            if (res.data.status == "OK") {
              vm.lecture = res.data.body.data;
            } else {
              vm.setStatusMessage(res.data.body);
            }
          })
          .catch(function(error) {
            console.log(error);
            vm.setStatusMessage("Error occurred when contacting the server.");
          });
      }
    },
    reset() {
      this.v$.$reset();
      this.session = "";
    },
  },
  validations() {
    return {
      session: {
        required,
        validsession() {
          return this.acadSessionRegExp.test(this.session);
        },
      }
    }
  },
};
</script>
