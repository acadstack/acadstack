<template>
  <div class="container-fluid">
    <span class="sec-hdr">Generate Semester Grade</span>
    <div class="row mb-2">    
    <div class="col-2">
        <div>
          <label for="entry_no">Enter Entery Number</label>
          <input
            id="entry_no"
            class="form-control"
            type="text"
            v-model.trim="search_crit.entry_no"
           
          />
        </div>
      </div>
    <div class="col-5">
        <div>
          <acad-session v-bind:acad_session="search_crit.acad_session"
                label="Academic Session"
                v-on:update:acad_session='search_crit.acad_session=$event'/>
        </div>
      </div>
      <div class="col-3">
        <div>
          <label>Enrollment Type</label>
          <select class="form-select" id="st_entoltype" v-model="search_crit.enrol_type">
            <option v-for="cs in SD.EnrolTypes" v-bind:value="cs.id" :key="cs.id">{{ cs.value }}</option>
          </select>
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
        <a class="btn btn-outline-primary mt-3" 
          :href="`download_sem_grade/${sem_grades['last_acad_session']}/${sem_grades['entry_no']}/${printType}`">
          <i class="bi bi-filetype-pdf"></i>
        </a>       
      </div>
    </div>
     
    <div class="card mb-5">
       <div > 
          <table>
            <tbody>                
                <tr><td>Name :</td><td>{{ sem_grades["name"] }}</td></tr>
                <tr><td>Entry Number :</td><td>{{ sem_grades["entry_no"] }}</td></tr>
                <tr><td>Programme :</td><td>{{ sem_grades["degree"] }} {{ sem_grades["dept_name"] }}<p v-if="printType !== 'C' && sem_grades['deg_type_spec']!='-SELECT-'"><span>{{ sem_grades["deg_type_spec"] }}</span></p></td></tr>
                <tr><td>Semester :</td><td>{{ sem_grades["last_acad_session"] }}</td></tr> 
               </tbody>
            </table> 
           </div>
        <table id="firstTable">
            <thead> 
              <tr>
                <th>Course Code</th>
                <th>Course Title</th>
                <th>Credits</th>
                <th>Grade</th>
             </tr>
            </thead>
            <tbody>
          <tr v-for="(c) in sem_grades['courses']" :key="c.id">
                <td>{{ c.code.toUpperCase()}}</td>
                <td>{{ c.title.toUpperCase()}}</td>
                <td>{{ c.ltp.split("-")[4].replace(/\.00$/,'') }}</td>
                <td>{{ c.grade.toUpperCase() }}</td>
                </tr>
                </tbody>
      </table>         
 
      <div class="card-body">
        <p v-if="sem_grades.length == 0"><b>Nothing to show yet!</b></p>
        <div class="col-md-6">EARNED CREDITS (EC): {{ sem_grades["ec"] }}</div>
        <div class="col-md-6">SEMETER GRADE POINT AVERAGE (SGPA): {{ sem_grades["sgpa"] }}</div>
        <div class="col-md-6">CUMULATIVE EARNED CREDITS (CEC): {{ sem_grades["cec"] }}</div>
        <div class="col-md-6">CUMULATIVE GRADE POINT AVERAGE (CGPA): {{ sem_grades["cgpa"] }}</div>
      </div>
       <table>
           <tr><td ><b>DATE:&nbsp;{{ sem_grades["date_issue"] }}</b></td> </tr>  
        </table>
    </div>
  </div>
</template>

<script>
import AcadSession from "./AcadSession.vue";
export default {
  name: "GenerateSemesterGrade",
  components: {
    "AcadSession": AcadSession
  },
  data: function () {
    return {
      search_crit: {
        acad_session: "",
        entry_no: "",
        enrol_type: ""
      },
      sem_grades: [],
    };
  },
  computed: {
    printType() {
      return this.search_crit.enrol_type;
    }
  },
  mounted: function() {
    if(this.$route.name=='semester.grade') {
      if (sessionStorage.CCRData) {
        let dd = JSON.parse(sessionStorage.CCRData);
        this.sem_grades = dd.sem_grades;
        this.search_crit = dd.search_crit;
      } else {
        this.reset();
      }
    } else {
      this.reset();
    }
  },
  methods: {
  
    search() {
      let vm = this;
      console.log("Running generate_semester_grade");
      vm.$http
        .post("generate_semester_grade", vm.search_crit)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.sem_grades = res.data.body;
            if(vm.$router.currentRoute.name=='semester.grade') {
              let dd = {sem_grades: vm.sem_grades, search_crit: vm.search_crit};
              sessionStorage.CCRData = JSON.stringify(dd);
            }
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
      this.sem_grades = [];
      this.search_crit = {
        acad_session: "",
       entry_no: ""
      };
    }
  }
};
</script>

<style>
table {
  font-family: 'Open Sans', sans-serif;
  /* width: 750px; */
  width: auto;
  border-collapse: collapse;
  /* border: 3px solid #44475C; */
  margin: 15px 15px 0 30px;
}

table th {
  text-transform: uppercase;
  text-align: left;
  background: #44475C;
  color: #FFF;
  padding: 8px;
  min-width: 30px;
}

table td {
  text-align: left;
  padding: 10px;
  border-right: 2px solid #7D82A8;
}
table td:last-child {
  border-right: none;
}  
</style>