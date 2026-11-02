// Miroir des schémas Pydantic du backend (app/schemas.py)
export type Stance = 'supports' | 'refutes' | 'context';
export type ClaimVerdict = 'vrai' | 'plutot_vrai' | 'mitige' | 'non_Hoe aona?ble' | 'plutot_faux' | 'faux';
export type GlobalVerdict = 'fiable' | 'plutot_fiable' | 'a_verifier' | 'douteux';
export type Status = 'pending' | 'running' | 'done' | 'error';
export type InputKind = 'text' | 'image' | 'document' | 'audio' | 'url';

export interface Preferences {
  weight_source: number;
  weight_veracity: number;
  weight_ai: number;
  deep_ai_detection: boolean;
  ai_exclusion_threshold: number;
  min_source_reliability: number;
  default_country: string;
  report_language: 'fr' | 'en' | 'mg';
  history_retention_days: number;
}

export interface InputSummary {
  kind: InputKind;
  name: string;
  size: number | null;
  extracted_chars: number;
  ai_probability: number;
  ai_signals: string[];
  reliability: number | null;
  reliability_reasons: string[];
  url: string | null;
  note: string | null;
}

export interface Evidence {
  id: string;
  url: string;
  title: string;
  publisher: string;
  domain: string;
  origin: 'factcheck' | 'wikipedia' | 'news' | 'web' | 'user_source';
  category: string;
  published_at: string | null;
  excerpt: string;
  image_url: string | null;
  reliability: number;
  reliability_reasons: string[];
  relevance: number;
  stance: Stance;
  confidence: number;
  justification: string;
  rating: string | null;
  ai_probability: number;
}

export interface Statistic {
  id: string;
  indicator_code: string;
  indicator_name: string;
  country: string;
  country_code: string;
  latest_year: number | null;
  latest_value: number | null;
  unit: string;
  series: { year: number; value: number }[];
  claimed_value: string | null;
  source_name: string;
  source_url: string;
  last_updated: string | null;
  stance: Stance;
  comment: string;
}

export interface Claim {
  id: string;
  text: string;
  search_query: string;
  truth_score: number;
  evidence_weight: number;
  verdict: ClaimVerdict;
  verdict_label: string;
  conclusion: string;
  arguments_for: string[];
  arguments_against: string[];
  evidence: Evidence[];
  statistics: Statistic[];
}

export interface Criterion {
  key: 'source' | 'veracity' | 'ai';
  label: string;
  score: number;
  summary: string;
  details: string[];
}

export interface ExcludedSource { url: string; title: string; reason: string; ai_probability: number; }
export interface ArticleSource { n: number; title: string; publisher: string; url: string; }

export interface Article {
  title: string;
  lead: string;
  body_markdown: string;
  tags: string[];
  sources: ArticleSource[];
  generated_by: 'llm' | 'modele';
  generated_at: string;
}

export interface AnalysisResult {
  global_score: number;
  verdict: GlobalVerdict;
  verdict_label: string;
  summary: string;
  topic: string;
  criteria: Criterion[];
  claims: Claim[];
  inputs: InputSummary[];
  excluded_sources: ExcludedSource[];
  article: Article | null;
  warnings: string[];
  tools_used: string[];
  weights: Record<string, number>;
}

export interface AnalysisOut {
  id: string;
  created_at: string;
  updated_at: string;
  status: Status;
  progress: number;
  step: string;
  title: string;
  input_kind: string;
  global_score: number | null;
  verdict: GlobalVerdict | null;
  result: AnalysisResult | null;
  error: string | null;
}

export interface AnalysisListItem {
  id: string;
  created_at: string;
  status: Status;
  title: string;
  input_kind: string;
  global_score: number | null;
  verdict: GlobalVerdict | null;
}

export interface AnalysisPage { items: AnalysisListItem[]; total: number; }

export interface ProviderStatus {
  key: string;
  label: string;
  role: string;
  configured: boolean;
  requires_key: boolean;
  signup_url: string | null;
}

export interface Health {
  status: string;
  mcp_mode: string;
  mcp_tools: string[];
  mcp_errors: string[];
  providers: ProviderStatus[];
}
