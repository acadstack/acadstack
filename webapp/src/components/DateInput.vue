<script>
export default {
    props: ['modelValue', 'rule'],
    emits: ['update:modelValue']
}
</script>

<template>
    <input class="form-control" type="date" :disabled="viewOnly" :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)" />
    <div v-if="rule.$invalid && rule.$dirty"
        class="text-danger">This is a requird feild</div>
</template>