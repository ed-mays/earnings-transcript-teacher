/** Shared type definitions for transcript browser and metadata panel. */

export interface SynthesisInfo {
  overall_sentiment: string | null;
  executive_tone: string | null;
  analyst_sentiment: string | null;
}

export interface EvasionItem {
  analyst_concern: string;
  defensiveness_score: number;
  evasion_explanation: string;
}

export interface StrategicShift {
  prior_position: string;
  current_position: string;
  investor_significance: string;
}

export interface SpeakerInfo {
  name: string;
  role: string;
  title: string | null;
  firm: string | null;
}

export interface CallDetail {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
  synthesis: SynthesisInfo | null;
  keywords: string[];
  themes: string[];
  topics: string[][];
  evasion_analyses: EvasionItem[];
  strategic_shifts: StrategicShift[];
  speakers: SpeakerInfo[];
}

export interface SpanItem {
  speaker: string;
  section: string;
  text: string;
  sequence_order: number;
}

export interface SpansResponse {
  total: number;
  page: number;
  page_size: number;
  spans: SpanItem[];
}

export interface SearchResult {
  speaker: string;
  section: string;
  text: string;
  similarity: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}
