// cytoscape-fcose ships no type declarations; it is a Cytoscape extension that registers the
// `fcose` layout.
declare module 'cytoscape-fcose' {
  import type { Ext } from 'cytoscape'

  const fcose: Ext
  export default fcose
}
