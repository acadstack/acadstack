<!--
Component for viewing course instructor's feedback in a course.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h4>Instructor feedback for {{fb_data.course}} in {{fb_data.acad_session}}</h4>
        <span>Score = {{fb_data.score}}</span>
      </div>
      <div class="card-body">
        <div class="card">
          <div class="card-body" v-if="loaded">
            <div class="row mb-2" v-for="(x, i) in fb_data.questions_data" :key="x.id">
              <div class="col-md-1">Q.{{i+1}}.</div>
              <div class="col">
                <p>{{x.question}}</p>
                <IChart :chart-id="'FBCh'+i" chart-type="doughnut" 
                :chart-title="'Question #'+(1+i)" ignore-aspect-ratio="true"
                :dataLabels="x.chartdata.labels" :datasets="x.chartdata.datasets" ></IChart>
              </div>
            </div>
            <hr/>
            <p>Descriptive feedback comments</p>
            <div class="row mb-2" v-for="(ansList, q) in fb_data.text_data" :key="q">
              <div class="col">
                <p class="fw-bold">Q. {{q}}</p>
                <ol>
                  <li v-for="item in ansList" :key="item">
                    {{item}}
                  </li>
                </ol>
              </div>
            </div>
          </div>
          <div v-else>Chart data not loaded yet.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import IChart from './IChart.vue';
export default {
  name: "ViewInstructorFeedback",
  components: { IChart },
  data: function () {
    return {
      co_id: 0,
      user_id: 0,
      fb_type: "",
      loaded: false,
      chart_options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: {display: false},
        scales: {
          yAxes: [{
            scaleLabel: {
              display: true,
              labelString: 'Responses in %'
            }
          }]
        }
      },
      fb_data: {
        course: "",
        acad_session: "",
        questions_data: [
          {
            question: "",
            chartdata:
            {
              /** Answer options */
              labels: [],
              datasets: [
                {
                  /** Count of votes for each answer option */
                  data:[]
                }
              ]
            }
          }
        ],
        text_data: {}
      }
    };
  },
  created: function () {
    console.log("Created ViewInstructorFeedback");
  },
  async mounted() {
    let vm = this;
    vm.co_id = vm.$route.params.co_id;
    vm.user_id = vm.$route.params.user_id;
    vm.fb_type = vm.$route.params.fb_type;
    if (vm.co_id > 0 && vm.user_id > 0 && vm.fb_type != undefined) {
      await vm.get_fb_data();
    } else {
      vm.setStatusMessage("Required parameters missing!")
    }
  },
  methods: {
    async get_fb_data() {
      let vm = this;
      try {
        let res =  await vm.$http.get(`get_instructor_feedback/${vm.co_id}/${vm.user_id}/${vm.fb_type}`);
        if (res.data.status == "OK") {
          vm.fb_data = res.data.body;
          vm.loaded = true;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      } catch(error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      }
    }
  }
};
</script>
