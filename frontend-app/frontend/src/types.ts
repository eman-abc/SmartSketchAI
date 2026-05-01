export interface CriticReport {
  decision?: 'accept' | 'revise' | string;
  score?: number | null;
  issues?: string[];
  matched_features?: string[];
  missing_features?: string[];
  prompt_adjustment?: string;
  safety_flags?: string[];
  reasoning_summary?: string;
  model?: string;
}

/**
 * Response from POST /api/forensic/generate/
 */
export interface GenerateResult {
  id: number;
  image_url: string;
  prompt: string;
  scores: {
    clip_score?: number;
    identity_score?: number;
    combined_score?: number;
  };
  metadata: Record<string, unknown>;
  generation_id: string;
  forensic_hash?: string;
  critic_report?: CriticReport | null;
}

/**
 * Request body for POST /api/forensic/generate/
 */
export interface GenerateRequest {
  prompt: string;
  case_type?: string;
  age?: number | null;
}

/**
 * Response from POST /api/forensic/edit/
 */
export interface EditResult {
  id: number;
  original_image_id: number;
  original_image_url: string;
  edited_image_url: string;
  edit_prompt: string;
  identity_score: number;
  identity_preserved: boolean;
  scores: {
    clip_score?: number;
    combined_score?: number;
  };
  metadata: Record<string, unknown>;
  edit_id: string;
  critic_report?: CriticReport | null;
}

/**
 * Request body for POST /api/forensic/edit/
 */
export interface EditRequest {
  original_image_id: number;
  edit_prompt: string;
  strength?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  prompt: string;
  generateResult: GenerateResult | null;
  editResult: EditResult | null;
  createdAt: number;
}
