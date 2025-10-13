<template>
  <div>
    <input type="text" class="form-control" v-model="typed" 
      :disabled="disabled" :placeholder="placeholder"/>
    <div v-if="data.length > 0 && !selectionDone" 
      style="z-index: 12; max-height: 300px;"
      class="card position-fixed bg-secondary overflow-auto">
      <button @click="clear" type="button" class="btn-close float-end" aria-label="Close"></button>
      <div class="list-group">
        <button type="button" class="list-group-item list-group-item-action"
          v-for="x in data" :key="x" 
          @click="itemSelected(x)">{{serializer(x)}}</button>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    "data": Object,
    "placeholder": { type: String, default: "Start typing..." },
    "hideOnSelect": { type: Boolean, default: true },
    "disabled": { type: Boolean, default: false },
    "serializer": { type: Function }
  },
  emits: ["mta-input-changed", "mta-item-selected"],
  data() {
    return {
      typed: "",
      selectionDone: false,
      skipChangeEvent: false
    }
  },
  watch: {
    typed(valNew, valOld) {
      if (valNew !== null && valNew !== valOld) {
        this.inputChanged()
      }
    }
  },
  methods: {
    async itemSelected(si) {
      this.$emit("mta-item-selected", si)
      if (this.hideOnSelect) this.clear()
      this.skipChangeEvent = true
      this.typed = this.serializer(si)
    },
    async inputChanged() {
      let vm = this;
      if (vm.skipChangeEvent) {
        vm.skipChangeEvent = false
      } else {
        vm.selectionDone = false
        vm.$emit("mta-input-changed", vm.typed)
      }
    },
    clear() {
      this.typed = null
      this.data.splice(0, this.data.length)
      this.selectionDone = true
      this.skipChangeEvent = false
    }
  }
}
</script>
<style scoped>
  /* The container <div> - needed to position the dropdown content */
  .popup-menu {
    position: relative;
    display: inline-block;
  }
</style>