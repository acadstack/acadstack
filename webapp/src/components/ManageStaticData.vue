<!--
(This screen is not used yet)
Component for managing static data items.

@author Balwinder Sodhi
-->
<template>
  <div class="container-fluid">
    <div class="card">
      <div class="card-header">Static data items</div>
      <div class="card-body">
        <div class="row hdr-row mb-2 border-info border-bottom">
          <div class="col-md-1">S#</div>
          <div class="col-md-2">Category</div>
          <div class="col-md-4">Item key</div>
          <div class="col">Item value</div>
          <div class="col-md-2">
            <button type="button" class="btn btn-outline-primary" @click="addItem">
              Add Item
            </button>
          </div>
        </div>
        <div class="row row-striped mb-2" v-if="sd_items.length == 0">
          Nothing available yet to show!
        </div>
        <div
          v-else
          class="row row-striped mb-2"
          v-for="(s, i) in sd_items"
          :key="i"
        >
          <div class="col-md-1">{{ i + 1 }}</div>
          <div class="col-md-2">
            <input type="text" class="form-control" v-model="s.sd_type" />
          </div>
          <div class="col-md-4">
            <input type="text" class="form-control" v-model="s.sd_key" />
          </div>
          <div class="col">
            <textarea rows="2" class="form-control" v-model="s.sd_value"></textarea>
          </div>
          <div class="col-md-2">
            <button
              class="btn btn-sm btn-outline-success me-2"
              type="button"
              @click="saveSdItem(s)"
            >
              <i class="bi bi-save"></i>
            </button>
            <button
              class="btn btn-sm btn-outline-danger"
              @click="deleteSdItem(s)"
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
  name: "ManageStaticData",
  data: function () {
    return {
      sd_items: []
    };
  },
  mounted: function () {
    this.loadSdItems();
  },
  methods: {
    addItem() {
      let vm = this;
      vm.sd_items.push({ sd_type: "", sd_key: "", sd_value: "" });
      console.debug("Added item to cat" + JSON.stringify(vm.sd_items));
    },
    deleteSdItem(item) {
      item.is_deleted=true;
      this.saveSdItem(item);
    },
    saveSdItem(item) {
      if (!confirm("Confirm save?")) {
        return;
      }
      console.debug("Saving: " + JSON.stringify(item));
      let vm = this;
      return vm.$http
        .post("save_sd", item)
        .then(function (res) {
          if (res.data.status == "OK") {
            vm.sd_items = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.error(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    },
    loadSdItems() {
      let vm = this;
      return vm.$http
        .get("load_sd")
        .then(function (res) {
          console.debug("Response: "+JSON.stringify(res));
          if (res.data.status == "OK") {
            vm.sd_items = res.data.body;
          } else {
            vm.setStatusMessage(res.data.body);
          }
        })
        .catch(function (error) {
          console.error(error);
          vm.setStatusMessage("Error occurred when contacting the server.");
        });
    }
  }
};
</script>
