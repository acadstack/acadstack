<template>
  <div class="container-fluid">
    <h6>Help</h6>
    <span v-if="$root.institute && $root.institute.help_email">
      For help, please email <a :href="'mailto:' + $root.institute.help_email">{{ $root.institute.help_email }}</a>.
    </span>
    <p v-if="$root.institute && $root.institute.guide_url">
      <a class="btn btn-outline-info" :href="$root.institute.guide_url" target="_blank">User guide</a>
    </p>
  </div>
</template>

<script>

export default {
  name: "Help"
};
</script>
