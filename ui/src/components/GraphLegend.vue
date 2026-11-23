<script setup lang="ts">
// The key to the relationship families (visual language version 2). Each swatch repeats the
// line, marker and colour of graph-style.ts; the words carry the meaning, so it reads without
// colour too. With `toggleable` each family is a switch that shows or hides its relationships.
import type { RelationshipFamily } from '@/lib/graph'
import { ALERT, FAMILY_COLOURS } from '@/lib/graph-style'

const props = defineProps<{ toggleable?: boolean; hidden?: readonly RelationshipFamily[] }>()
const emit = defineEmits<{ toggle: [family: RelationshipFamily] }>()

interface Swatch {
  name: string
  types: string
  family?: RelationshipFamily
  colour: string
  dash?: string
  width?: number
  marker: 'arrow' | 'hollow' | 'chevron' | 'dot' | 'none'
  double?: boolean
}

const swatches: Swatch[] = [
  { name: 'Alert path', types: 'numbered steps', colour: ALERT, width: 4.5, marker: 'arrow' },
  { name: 'Money', types: 'paid', family: 'money', colour: FAMILY_COLOURS.money, marker: 'arrow' },
  {
    name: 'Ownership and control',
    types: 'owns, controls, consolidates',
    family: 'ownership',
    colour: FAMILY_COLOURS.ownership,
    marker: 'hollow',
    double: true,
  },
  {
    name: 'People and roles',
    types: 'director, represents, position, family, associate',
    family: 'roles',
    colour: FAMILY_COLOURS.roles,
    dash: '7 3.5',
    marker: 'chevron',
  },
  {
    name: 'Holds an account',
    types: 'holds',
    family: 'account',
    colour: FAMILY_COLOURS.account,
    marker: 'dot',
  },
  {
    name: 'Address',
    types: 'registered address',
    family: 'address',
    colour: FAMILY_COLOURS.address,
    dash: '0.1 5',
    width: 2.25,
    marker: 'none',
  },
  {
    name: 'Possible match, not confirmed',
    types: 'no direction',
    family: 'match',
    colour: FAMILY_COLOURS.match,
    dash: '10 3 2 3',
    marker: 'none',
  },
]

function isShown(swatch: Swatch): boolean {
  return !swatch.family || !(props.hidden ?? []).includes(swatch.family)
}
</script>

<template>
  <ul class="graph-legend" :aria-label="props.toggleable ? undefined : 'Relationship key'">
    <li v-for="swatch in swatches" :key="swatch.name">
      <component
        :is="props.toggleable && swatch.family ? 'button' : 'span'"
        class="graph-legend__item"
        v-bind="
          props.toggleable && swatch.family
            ? { type: 'button', 'aria-pressed': isShown(swatch) }
            : {}
        "
        @click="props.toggleable && swatch.family && emit('toggle', swatch.family)"
      >
        <svg width="44" height="14" viewBox="0 0 44 14" aria-hidden="true" focusable="false">
          <line
            x1="1"
            y1="7"
            x2="36"
            y2="7"
            :stroke="swatch.colour"
            :stroke-width="swatch.double ? 4.5 : (swatch.width ?? 1.5)"
            :stroke-dasharray="swatch.dash"
            stroke-linecap="round"
          />
          <line
            v-if="swatch.double"
            x1="1"
            y1="7"
            x2="36"
            y2="7"
            stroke="#ffffff"
            stroke-width="1.5"
          />
          <path v-if="swatch.marker === 'arrow'" d="M35,2 L43,7 L35,12 z" :fill="swatch.colour" />
          <path
            v-else-if="swatch.marker === 'hollow'"
            d="M35,2 L43,7 L35,12 z"
            fill="#ffffff"
            :stroke="swatch.colour"
            stroke-width="1.5"
          />
          <path
            v-else-if="swatch.marker === 'chevron'"
            d="M36,2 L42,7 L36,12"
            fill="none"
            :stroke="swatch.colour"
            stroke-width="1.75"
          />
          <circle
            v-else-if="swatch.marker === 'dot'"
            cx="39"
            cy="7"
            r="3.5"
            :fill="swatch.colour"
          />
        </svg>
        <span>
          <strong>{{ swatch.name }}</strong>
          <span v-if="!props.toggleable" class="muted"> ({{ swatch.types }})</span>
        </span>
      </component>
    </li>
  </ul>
</template>
