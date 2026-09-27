<!--
Component for managing course slot timings.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">
        Course slot timings
        <span class="float-end">
            <button
            type="button"
            @click="addSlot"
            class="btn btn-success btn-sm me-2"
            >
            Add
            </button>
            <button
            type="button"
            @click="loadSlots"
            class="btn btn-primary btn-sm"
            >
            Refresh
            </button>
        </span>
      </div>
      <div class="card-body">
        <div class="row hdr-row mb-2 border-info border-bottom">
          <div class="col-md-1">S#</div>
          <div class="col-md-3">Slot</div>
          <div class="col-md-2">Week day</div>
          <div class="col-md-2">Start time</div>
          <div class="col-md-2">End time</div>
          <div class="col-md-2"></div>
        </div>
        <div class="row row-striped mb-2" v-if="slot_timings.length == 0">
            Nothing available yet to show!
        </div>
        <div v-else
          class="row row-striped mb-2"
          v-for="(s, i) in slot_timings"
          :key="s"
        >
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-3">
            <select class="form-select" v-model="s.slot">
                  <option
                    v-for="x in SD.CourseSlots"
                    v-bind:value="x.id"
                    :key="x.id"
                  >{{ x.value }}</option>
            </select>
          </div>
          <div class="col-md-2">
            <select class="form-select" v-model="s.week_day">
                <option value="0">Monday</option>
                <option value="1">Tuesday</option>
                <option value="2">Wednesday</option>
                <option value="3">Thursday</option>
                <option value="4">Friday</option>
                <option value="5">Saturday</option>
                <option value="6">Sunday</option>
            </select>
          </div>
          <div class="col-md-2">
            <input type="number" class="form-control" v-model="s.start_time" placeholder="HHHH" />
          </div>
          <div class="col-md-2">
            <input type="number" class="form-control" v-model="s.end_time" placeholder="HHHH"/>
          </div>
          <div class="col-md-2">
            <button
              class="btn btn-sm btn-outline-success me-2"
              type="button"
              @click="saveSlot(s)"
            >
              <i class="bi bi-save"></i>
            </button>
            <button
              class="btn btn-sm btn-outline-danger"
              @click="deleteSlot(s)"
              type="button"
            >
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CourseSlotTiming",
  data: function () {
    return {
      slot_timings: [],
    };
  },
  mounted: function () {
    this.loadSlots();
  },
  methods: {
    addSlot() {
      this.slot_timings.push({ slot:"", week_day: 1});
    },
    deleteSlot(s) {
      s.is_deleted = true;
      this.saveSlot(s);
    },
    saveSlot(s) {
      let vm = this;
      if (s.start_time >= s.end_time) {
          vm.setStatusMessage("Start time should be before the end time!");
          return;
      }
      if (!confirm("Confirm save?")) {
        return;
      }
      
      console.debug("Saving: "+JSON.stringify(s));
      vm.$http
        .post("save_slot", s)
        .then(function (res) {
          if (res.data.status == "OK") {
            if (s.is_deleted) {
              vm.slot_timings = vm.slot_timings.filter(
                (item) => !item.is_deleted
              );
              vm.setStatusMessage("Deleted successfully!");
            } else {
              vm.setStatusMessage("Saved successfully!");
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
    loadSlots() {
      let vm = this;
      return vm.$http
        .get("load_slots")
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.slot_timings = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.error(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
  },
};
</script>
