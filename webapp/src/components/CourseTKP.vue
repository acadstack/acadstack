<!--
Component for TKP tab of the course details.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div v-if="error.course.tkp.$error && error.course.tkp.$dirty" class="text-danger">tkp must have atleast 2 item.</div>
    <div class="card">
      <div class="card-header">Targeted Knowledge Profile</div>
      <div class="card-body">
        <div class="form-check" v-for="(w, i) in wk_items" :key="i">
          <input class="form-check-input" type="checkbox" 
          v-model="tkp[i]" v-bind:id="'wk'+i" :disabled="viewOnly"/>
          <label class="form-check-label" v-bind:for="'wk'+i">
            {{w}}
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseTKP",
  props: ["tkp","error"],
  data: function() {
    return {
      wk_items: [
        "WK1: A systematic, theory-based understanding of the natural sciences applicable to the discipline.",
        "WK2: Conceptually-based mathematics, numerical analysis, statistics and formal aspects of computer and information science to support analysis and modelling applicable to the discipline.",
        "WK3: A systematic, theory-based formulation of engineering fundamentals required in the engineering discipline.",
        "WK4: Engineering specialist knowledge that provides theoretical frameworks and bodies of knowledge for the accepted practice areas in the engineering discipline; much is at the forefront of the discipline.",
        "WK5: Knowledge that supports engineering design in a practice area.",
        "WK6: Knowledge of engineering practice (technology) in the practice areas in the engineering discipline.",
        "WK7: Comprehension of the role of engineering in society and identified issues in engineering practice in the discipline: ethics and the professional responsibility of an engineer to public safety; the impacts of engineering activity: economic, social, cultural, environmental and sustainability.",
        "WK8: Engagement with selected knowledge in the research literature of the discipline."
      ]
    };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("CourseTKP.beforeRouteUpdate");
    // just use `this`
    // this.name = to.params.name;
    next();
  },
  created: function() {
    console.log("Creating CourseTKP:"+this.tkp);
    this.viewOnly = this.isStudent;
    let l = this.tkp.length;
    if (l < 8) {
      for (let x=0; x<8-l; x++) this.tkp.push(false);
    }
  }
};
</script>