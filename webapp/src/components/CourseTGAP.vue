<!--
Component for TGAP tab of the course details.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div v-if="error.course.tkp.$error && error.course.tkp.$dirty" class="text-danger">tkp must have atleast 2 item.</div>
    <div class="card">
      <div class="card-header">Targeted Graduate Attribute Profile</div>
      <div class="card-body">
        <div class="form-check" v-for="(ti, i) in tgap_items" :key="i">
          <input class="form-check-input" type="checkbox" v-model="tgap[i]" v-bind:id="'tgap'+i" :disabled="viewOnly"/>
          <label
            class="form-check-label"
            v-bind:for="'tgap'+i"
          >{{ti}}</label>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseTGAP",
  props: ["tgap","error"],
  data: function() {
    return {
      tgap_items: [
        "WA1: Apply knowledge of mathematics, natural science, engineering fundamentals and an engineering specialization as specified in WK1 to WK4 respectively to the solution of complex engineering problems.",
        "WA2: Identify, formulate, research literature and analyse complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences and engineering sciences. (WK1 to WK4)",
        "WA3: Design solutions for complex engineering problems and design systems, components or processes that meet specified needs with appropriate consideration for public health and safety, cultural, societal, and environmental considerations. (WK5)",
        "WA4: Conduct investigations of complex problems using research-based knowledge (WK8) and research methods including design of experiments, analysis and interpretation of data, and synthesis of information to provide valid conclusions.",
        "WA5: Create, select and apply appropriate techniques, resources, and modern engineering and IT tools, including prediction and modelling, to complex engineering problems, with an understanding of the limitations. (WK6)",
        "WA6: Apply reasoning informed by contextual knowledge to assess societal, health, safety, legal and cultural issues and the consequent responsibilities relevant to professional engineering practice and solutions to complex engineering problems. (WK7)",
        "WA7: Understand and evaluate the sustainability and impact of professional engineering work in the solution of complex engineering problems in societal and environmental contexts. (WK7)",
        "WA8: Apply ethical principles and commit to professional ethics and responsibilities and norms of engineering practice. (WK7)",
        "WA9: Function effectively as an individual, and as a member or leader in diverse teams and in multi-disciplinary settings.",
        "WA10: Communicate effectively on complex engineering activities with the engineering community and with society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations, and give and receive clear instructions.",
        "WA11: Demonstrate knowledge and understanding of engineering management principles and economic decision-making and apply these to one’s own work, as a member and leader in a team, to manage projects and in multidisciplinary environments.",
        "WA12: Recognize the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change."
      ]
    };
  },
  beforeRouteUpdate(to, from, next) {
    console.log("CourseTGAP.beforeRouteUpdate");
    next();
  },
  created: function() {
    console.log("Creating CourseTGAP");
    this.viewOnly = this.isStudent;
    let l = this.tgap.length;
    if (l < 12) {
      for (let x=0; x < 12-l; x++) this.tgap.push(false);
    }
  }
};
</script>
