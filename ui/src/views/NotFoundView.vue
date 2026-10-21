<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section>
    <h1>Page not found</h1>
    <p>There is no page at this address. <RouterLink to="/">Go to search</RouterLink>.</p>
  </section>
</template>
