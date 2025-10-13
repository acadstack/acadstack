<!--
Component for workflow notes.

@author Balwinder Sodhi
-->
<template>
  <div>
    <div class="card">
      <div class="card-header">Notes</div>
      <div class="card-body">
        <div v-if="!print">
          <h5>Add New</h5>
          <div class="input-group">
            <textarea :disabled="!ent_key" class="form-control" aria-describedby="btnAddOn" rows="2" v-model="wfn.note"></textarea>
            <button :disabled="!ent_key" class="btn btn-outline-info" type="button" id="btnAddOn"
              @click="addNote">Save</button>
          </div>
        </div>
        <h5>Existing Notes: </h5>
        <p v-if="items.length == 0">Nothing to show yet!</p>
        <div v-else class="list-group">
          <div class="list-group-item list-group-item-action"
              v-for="x in items" :key="x.id">
            <div class="d-flex justify-content-between">
              <h6 class="mb-1">{{x.ins_ts}} :: {{x.txn_login_id}}</h6>
              <button class="btn btn-outline-danger" @click="removeItem(x)" type="button"><i class="bi bi-trash"></i></button>
            </div>
            <p class="mb-1">{{x.note}}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "WorkflowNotes",
  props: ["ent_name", "ent_key","print"],
  data: function() {
    return {
      wfn:{note:"", 
      entity_name: this.ent_name, 
      entity_key: this.ent_key}, 
      items:[]
    };
  },
  created: function() {
    let vm = this;
    console.log(`Loading WorkflowNotes for ${vm.ent_name} KEY: ${vm.ent_key}`);
    if (vm.ent_key > 0) {
      vm.$http.get(`wfnote_find/${vm.ent_name}/${vm.ent_key}`)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.items = res.data.body;
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    }
  },
  methods: {
    addNote() {
      let vm = this;
      vm.$http.post("wfnote_save", vm.wfn)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.items.push(res.data.body);
          vm.wfn.note = "";
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error occurred when contacting the server.");
      });
    },
    removeItem(x) {
      let vm = this;
      vm.$http.get(`wfnote_delete/${x.id}`)
      .then(function (res) {
        if (res.data.status == "OK") {
          vm.items = vm.items.filter(y => y!=x);
        } else {
          vm.setStatusMessage(res.data.body);
        }
      })
      .catch(function (error) {
        console.log(error);
        vm.setStatusMessage("Error: "+error);
      });
    }
  }
};
</script>
