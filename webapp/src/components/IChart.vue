<template>
  <div>
    <canvas :id="chartId"></canvas>
  </div>
</template>
<script>
import Chart from 'chart.js/auto';
import ChartDataLabels from 'chartjs-plugin-datalabels';

export default {
  name: "IChart",
  props: ["chartId", "chartType", "dataLabels", 
          "datasets", "chartTitle", "ignoreAspectRatio"],
  components: { },
  setup() {
    Chart.register(ChartDataLabels);
    Chart.defaults.set('plugins.datalabels', {
      color: '#000000',
      font: { weight: 'bold' }
    });
  },
  data() {
    return { 
      COLORS: ['#40bbda', '#ff4700', '#ffbb00', '#0b7622', 
        '#76430b', '#201d72', '#77c4df', '#726e29',
        '#51504A', '#AE8F36', '#1F08DF', '#9F08DF',
        '#AB82EB', '#5521A5', '#65026A', '#4C652B',
        '#2B652F', '#367797', '#383734', '#862404']
    }
  },
  mounted() {
    let vm = this;
    console.log("ignoreAspectRatio="+vm.ignoreAspectRatio)
    const mar = vm.ignoreAspectRatio == undefined || vm.ignoreAspectRatio == "false"
    const ctx = document.getElementById(vm.chartId);
    const dsList = [];
    this.datasets.forEach((dsItem, idx) => {
      const c = this.getDataColors(idx, dsItem.data.length);
      const ds = {
                label: dsItem.label,
                data: dsItem.data,
                backgroundColor: c[0],
                borderColor: c[1],
                borderWidth: 1
              };
      dsList.push(ds);
    });
    const myChart = new Chart(ctx, {
        type: vm.chartType,
        data: {
            labels: vm.dataLabels,
            datasets: dsList
        },
        options: {
          responsive: true,
          maintainAspectRatio: mar,
          plugins: {
            legend: {
              position: 'top',
            },
            title: {
              display: vm.chartTitle !== undefined && vm.chartTitle !== '',
              position: 'bottom',
              text: vm.chartTitle
            }
          },
          scales: {
            x: {
              display: true,
            },
            y: {
              display: true,
              // ticks: {
              //   // forces step size to be 5 units
              //   stepSize: 5
              // }
            }
          }
        }
    });

    console.debug("Mounted chart "+vm.chartId+". Width = "+
    myChart.width+". Title: "+vm.chartTitle)
  },
  methods: {
    getDataColors(dsIdx, dataLen) {
      if (!['pie', 'doughnut'].includes(this.chartType)) {
        const c = this.COLORS[dsIdx%dataLen];
        return [c, c];
      } else {
        let bgColor = []
        let borColor = []
        for (let i=0; i<dataLen; i++) {
          const c = this.COLORS[i%dataLen];
          bgColor.push(c);
          borColor.push(c);
        }
        return [bgColor, borColor]
      }
    }
  },
};
</script>
