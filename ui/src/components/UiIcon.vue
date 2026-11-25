<script setup lang="ts">
defineProps<{
  name:
    | 'search'
    | 'alerts'
    | 'sources'
    | 'arrow'
    | 'download'
    | 'network'
    | 'shield'
    | 'plus'
    | 'minus'
    | 'fit'
}>()

const paths = {
  search: 'm21 21-4.4-4.4M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  alerts: 'M9 3h6l6 6v6l-6 6H9l-6-6V9l6-6Zm3 4v6m0 4h.01',
  sources: 'M20 6c0 2.2-16 2.2-16 0s16-2.2 16 0Zm0 0v12c0 2.2-16 2.2-16 0V6m0 6c0 2.2 16 2.2 16 0',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  download: 'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
  network:
    'M9 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm12 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm-6 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM9 6h6M7.5 9l3 6m6-6-3 6',
  shield: 'M12 3 4 6v6c0 4 8 9 8 9s8-5 8-9V6l-8-3Zm-4 9 3 3 5-6',
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  fit: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
}
</script>

<template>
  <svg
    class="ui-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path :d="paths[name]" />
  </svg>
</template>
