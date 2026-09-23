// API types come from the backend's OpenAPI contract (backend/openapi.json) via
// `npm run types:generate`, so they cannot drift from the server. Do not hand-edit schema.d.ts.
import type { components } from './schema'

export type ChatTurn = components['schemas']['ChatTurn']
export type ChatRequest = components['schemas']['ChatRequest']
export type ChatResponse = components['schemas']['ChatResponse']
export type HealthResponse = components['schemas']['HealthResponse']
export type PostSummary = components['schemas']['PostSummary']
export type PostDetail = components['schemas']['PostDetail']
