export type VerificationState = 'UNVERIFIED' | 'INFERRED' | 'VERIFIED' | 'DISPUTED';

export interface Entity {
  id: string;
  name: string;
  type: string;
  confidence: number;
  verification_state: VerificationState;
  aliases: string[];
  labels: string[];
  version: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface Relationship {
  id: string;
  from_entity_id: string;
  to_entity_id: string;
  type: string;
  confidence: number;
  verification_state: VerificationState;
}

export interface GraphResponse {
  nodes: Entity[];
  edges: Relationship[];
  truncated: boolean;
  node_count: number;
  edge_count: number;
}

export interface TrustComponents {
  evidence_weight: number;
  freshness_decay: number;
  verification_bonus: number;
  conflict_penalty: number;
  evidence_count: number;
}

export interface TrustScore {
  score: number;
  components: TrustComponents;
  algorithm: string;
  computed_at: string;
}

export interface EvidenceItem {
  id: string;
  source_type: string;
  confidence: number;
  verification_state: string;
  extracted_at: string;
  content_preview: string;
}

export interface ProvenanceInfo {
  id: string;
  origin: string;
  extraction_method: string;
  agent_id: string;
  session_id: string | null;
  timestamp: string;
}

export interface ConflictEvent {
  version: number;
  change_reason: string;
  changed_by: string;
  changed_at: string;
}

export interface ExplainResponse {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  verification_state: VerificationState;
  is_disputed: boolean;
  trust_score: TrustScore | null;
  evidence: EvidenceItem[];
  provenance: ProvenanceInfo | null;
  conflict_history: ConflictEvent[];
}
