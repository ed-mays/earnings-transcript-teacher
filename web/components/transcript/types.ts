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
  question_topic: string | null;
  analyst_name: string | null;
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

export interface TakeawayItem {
  takeaway: string;
  why_it_matters: string;
}

export interface MisconceptionItem {
  fact: string;
  misinterpretation: string;
  correction: string;
}

export interface CallBrief {
  context_line: string;
  bigger_picture: string[];
  interpretation_questions: string[];
}

export interface SignalStrip {
  overall_sentiment: string | null;
  executive_sentiment: string | null;
  analyst_sentiment: string | null;
  evasion_level: string | null;
  strategic_shift_flagged: boolean;
}

export interface TopicInfo {
  label: string;
  terms: string[];
  summary: string;
}

export interface NewsItem {
  headline: string;
  url: string;
  source: string;
  date: string;
  summary: string;
}

export interface Competitor {
  name: string;
  ticker: string;
  description: string;
  mentioned_in_transcript: boolean;
}

export interface CallDetail {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
  synthesis: SynthesisInfo | null;
  keywords: string[];
  themes: string[];
  topics: TopicInfo[];
  evasion_analyses: EvasionItem[];
  strategic_shifts: StrategicShift[];
  speakers: SpeakerInfo[];
  brief: CallBrief | null;
  takeaways: TakeawayItem[];
  misconceptions: MisconceptionItem[];
  signal_strip: SignalStrip | null;
  news_items: NewsItem[];
  competitors: Competitor[];
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
