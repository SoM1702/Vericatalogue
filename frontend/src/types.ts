export type FieldStatus = 'verified' | 'inferred' | 'missing' | 'conflict'
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'edited'

export interface Evidence {
  source_file: string
  page: number | null
  row: number | null
  snippet: string
  method: string
}

export interface NormalizedValue {
  value: string | number | number[] | null
  unit: string | null
  display: string | null
}

export interface ValidationResult {
  rule: string
  status: 'pass' | 'fail' | 'warning'
  message: string
}

export interface ProductAttribute {
  field: string
  raw_value: string | null
  normalized_value: NormalizedValue | null
  normalization_explanation: string | null
  status: FieldStatus
  confidence: number
  confidence_label: string
  evidence: Evidence[]
  validation_results: ValidationResult[]
  review_status: ReviewStatus
  review_note: string | null
  reviewed_value: string | null
  agent_decision: string | null
  agent_reason: string | null
}

export interface ProductRecord {
  id: string
  category: 'industrial_valves_fittings'
  source_kind: 'synthetic_demo' | 'uploaded' | 'manual'
  attributes: ProductAttribute[]
  created_at: string
}

export interface RecordOption {
  index: number
  label: string
  source_file: string
  page: number | null
  detected_fields: string[]
}

export interface EnrichmentResult {
  product: ProductRecord
  message: string
  record_options: RecordOption[]
  ai_candidate_count: number
}

export interface ReviewAgentToolTrace {
  tool:
    | 'identify_exceptions'
    | 'inspect_provenance'
    | 'evaluate_validation'
    | 'rank_human_actions'
    | 'evidence_extraction'
    | 'normalization_check'
    | 'validation_check'
    | 'conflict_resolution'
    | 'decision_agent'
    | 'policy_engine'
  outcome: string
  item_count: number
}

export interface ReviewAgentTask {
  field: string
  status: FieldStatus
  review_status: ReviewStatus
  priority: number
  recommended_action: 'resolve_conflict' | 'find_source_value' | 'verify_candidate'
  reason: string
  evidence_count: number
  human_approval_required: boolean
}

export interface ReviewAgentPlan {
  id: string
  product_id: string
  agent_name: string
  mode: 'bounded_local_orchestration'
  created_at: string
  tool_trace: ReviewAgentToolTrace[]
  tasks: ReviewAgentTask[]
  summary: string
  mutations_made: boolean
  human_approval_required: boolean
  guardrail: string
}

export interface BatchMetrics {
  product_count: number
  completeness_score: number
  fields_requiring_review: number
  conflict_count: number
  missing_mandatory_fields: number
  duplicate_candidate_count: number
  priority_products: PriorityProduct[]
  metric_note: string
}

export interface PriorityProduct {
  product_id: string
  manufacturer_part_number: string
  product_title: string
  priority: number
  reasons: string[]
  statuses: FieldStatus[]
}

export interface BatchResult {
  products: ProductRecord[]
  metrics: BatchMetrics
  message: string
}

export interface AgentDecision {
  product_id: string
  attribute_field: string
  agent_name: string
  agent_action: string
  input_context: string | null
  output: string | null
  evidence_ids: string[]
  reason: string | null
  confidence: number
  created_at: string
}

