export interface Citation {
  section: string;
  quote: string;
  quote_verified: boolean;
}

export interface ClaimIn {
  claimant?: string;
  date?: string;
  category?: string;
  amount?: number;
  currency?: string;
  description?: string;
  receipt_available: boolean;
}

export interface ValidationResult {
  check: string;
  status: "pass" | "fail" | "warn";
  detail: string;
}

export interface ValidationResultResponse {
  id: number;
  claim_id: number;
  passed: boolean;
  errors: ValidationResult[];
  warnings: ValidationResult[];
  created_at: string;
}

export interface AIReviewResponse {
  id: number;
  claim_id: number;
  category: string;
  confidence: number;
  verdict: string;
  reasoning: string;
  citations: Citation[];
  missing_info: string[];
  uncertain: boolean;
  uncertain_reasons: string[];
  created_at: string;
}

export interface DecisionCreate {
  action: "approve" | "reject" | "request_clarification" | "override_category";
  reason?: string;
  category?: string;
}

export interface DecisionResponse {
  id: number;
  claim_id: number;
  action: string;
  reason?: string;
  created_at: string;
}

export interface ClaimResponse {
  id: number;
  claimant?: string;
  date?: string;
  category?: string;
  amount?: number;
  currency?: string;
  description?: string;
  receipt_available: boolean;
  created_at: string;
}

export interface ClaimListItem extends ClaimResponse {
  ai_verdict?: string;
  ai_uncertain?: boolean;
  validation_status?: string;
  overall_status?: string;
  latest_decision?: string;
}

export interface ClaimDetailResponse {
  claim: ClaimResponse;
  validation?: ValidationResultResponse;
  ai_review?: AIReviewResponse;
  ai_status: string;
  overall_status?: string;
  history: DecisionResponse[];
}

export const CATEGORY_OPTIONS = [
  { label: "Select...", value: "" },
  { label: "Meals", value: "meals" },
  { label: "Travel Local", value: "travel_local" },
  { label: "Travel Intercity", value: "travel_intercity" },
  { label: "Accommodation", value: "lodging" },
  { label: "Software", value: "software" },
  { label: "Client Entertainment", value: "client_entertainment" },
  { label: "Office Supplies", value: "office_supplies" },
  { label: "Training", value: "training" },
  { label: "Other", value: "other" }
];
