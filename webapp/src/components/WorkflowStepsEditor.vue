<!--
Edits a list of workflow steps (domain/workflow.py's Step: a registered
check or effect name, plus optional parameters) for WorkflowAdmin.vue.
The list is [{name, paramsText}], parameters held as JSON text so a
half-typed value survives editing; WorkflowAdmin parses it on save.

@author Balwinder Sodhi
-->
<template>
    <div>
        <div class="small text-muted" v-if="modelValue.length == 0">None.</div>
        <div class="row g-1 mb-1" v-for="(step, idx) in modelValue" :key="idx">
            <div class="col-5">
                <select class="form-select form-select-sm" :value="step.name"
                    @change="update(idx, { name: $event.target.value })">
                    <option v-if="!options.includes(step.name)" :value="step.name">
                        {{ step.name || "-- choose --" }}
                    </option>
                    <option v-for="o in options" :key="o" :value="o">{{ o }}</option>
                </select>
            </div>
            <div class="col">
                <input type="text" class="form-control form-control-sm font-monospace"
                    :class="{ 'is-invalid': !paramsValid(step.paramsText) }" :value="step.paramsText"
                    placeholder='parameters as JSON, e.g. {"code": "DC_APPROVED"}'
                    @input="update(idx, { paramsText: $event.target.value })">
            </div>
            <div class="col-auto">
                <button class="btn btn-sm btn-outline-danger" type="button" title="Remove"
                    @click="remove(idx)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
        <button class="btn btn-sm btn-outline-primary" type="button" @click="add">
            Add {{ noun }} <i class="bi bi-plus-circle"></i>
        </button>
    </div>
</template>

<script>
export default {
    name: "WorkflowStepsEditor",
    props: {
        modelValue: { type: Array, required: true },
        options: { type: Array, required: true },
        noun: { type: String, default: "step" }
    },
    emits: ["update:modelValue"],
    methods: {
        paramsValid(text) {
            if (!text || !text.trim()) return true;
            try {
                const v = JSON.parse(text);
                return v !== null && typeof v == "object" && !Array.isArray(v);
            } catch {
                return false;
            }
        },
        update(idx, change) {
            const steps = this.modelValue.map(s => ({ ...s }));
            Object.assign(steps[idx], change);
            this.$emit("update:modelValue", steps);
        },
        remove(idx) {
            this.$emit("update:modelValue", this.modelValue.filter((_, i) => i != idx));
        },
        add() {
            this.$emit("update:modelValue", [...this.modelValue, { name: "", paramsText: "" }]);
        }
    }
};
</script>
