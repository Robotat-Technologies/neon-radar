// Short names for the generated API types (contract C3). Never write API types by hand:
// they come from contracts/openapi/v1.json through `npm run gen:api` (src/api/schema.d.ts).
import type { components, operations } from './schema'

type Schemas = components['schemas']

export type Alert = Schemas['Alert']
export type AlertDetail = Schemas['AlertDetail']
export type AlertPage = Schemas['AlertPage']
export type AlertSummary = Schemas['AlertSummary']
export type Citation = Schemas['Citation']
export type DatasetInfo = Schemas['DatasetInfo']
export type Disclaimers = Schemas['Disclaimers']
export type EntityDetail = Schemas['EntityDetail']
export type EntitySummary = Schemas['EntitySummary']
export type GraphEdge = Schemas['GraphEdge']
export type GraphNode = Schemas['GraphNode']
export type MetaResponse = Schemas['MetaResponse']
export type NodeFlags = Schemas['NodeFlags']
export type Problem = Schemas['Problem']
export type SearchHit = Schemas['SearchHit']
export type SearchResponse = Schemas['SearchResponse']
export type Subgraph = Schemas['Subgraph']
export type TypologyDetail = Schemas['TypologyDetail']
export type TypologySummary = Schemas['TypologySummary']

export type SearchParams = operations['search']['parameters']['query']
export type SearchLabel = NonNullable<NonNullable<SearchParams['labels']>[number]>
export type NetworkParams = NonNullable<operations['get_network']['parameters']['query']>
export type AlertListParams = NonNullable<operations['list_alerts']['parameters']['query']>
export type AlertPriority = AlertSummary['priority']
