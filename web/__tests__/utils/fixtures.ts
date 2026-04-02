import type {
  CallDetail,
  CallBrief,
  SignalStrip,
  SpansResponse,
  TakeawayItem,
  MisconceptionItem,
} from "@/components/transcript/types";

export const callBrief: CallBrief = {
  context_line: "Apple reported Q4 earnings beating analyst expectations.",
  bigger_picture: ["Strong services revenue growth", "iPhone demand resilient"],
  interpretation_questions: ["Will margin expansion continue?"],
};

export const signalStrip: SignalStrip = {
  overall_sentiment: "positive",
  executive_sentiment: "optimistic",
  analyst_sentiment: "bullish",
  evasion_level: "low",
  strategic_shift_flagged: false,
};

export const takeaways: TakeawayItem[] = [
  {
    takeaway: "Services hit record revenue",
    why_it_matters: "Higher-margin business expanding",
  },
];

export const misconceptions: MisconceptionItem[] = [
  {
    fact: "iPhone units declined",
    misinterpretation: "iPhone business is shrinking",
    correction: "Revenue per unit rose significantly",
  },
  {
    fact: "China revenue soft",
    misinterpretation: "Apple is losing China market",
    correction: "Competitive dynamics shifted, not lost share",
  },
];

export const callDetail: CallDetail = {
  ticker: "AAPL",
  company_name: "Apple Inc.",
  call_date: "2024-11-01",
  industry: "Technology",
  synthesis: {
    overall_sentiment: "positive",
    executive_tone: "confident",
    analyst_sentiment: "bullish",
  },
  keywords: ["services", "iPhone", "margin"],
  themes: ["services growth", "hardware resilience"],
  topics: [["services growth", "subscription"], ["hardware resilience"]],
  evasion_analyses: [],
  strategic_shifts: [],
  speakers: [
    { name: "Tim Cook", role: "executive", title: "CEO", firm: null },
    { name: "Luca Maestri", role: "executive", title: "CFO", firm: null },
  ],
  brief: callBrief,
  takeaways,
  misconceptions,
  signal_strip: signalStrip,
};

export const spansResponse: SpansResponse = {
  total: 2,
  page: 1,
  page_size: 50,
  spans: [
    {
      speaker: "Tim Cook",
      section: "prepared",
      text: "We are pleased to report record services revenue.",
      sequence_order: 1,
    },
    {
      speaker: "Analyst",
      section: "qa",
      text: "Can you elaborate on the China situation?",
      sequence_order: 2,
    },
  ],
};

/** Minimal CallSummary shape as returned by /api/calls */
export interface CallSummary {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
}

export const callSummaries: CallSummary[] = [
  { ticker: "AAPL", company_name: "Apple Inc.", call_date: "2024-11-01", industry: "Technology" },
  { ticker: "MSFT", company_name: "Microsoft Corp.", call_date: "2024-10-30", industry: "Technology" },
];
