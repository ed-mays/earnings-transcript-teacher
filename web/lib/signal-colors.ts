/** Single source of truth for domain color semantics. */

export interface EvasionStyle {
  bg: string;
  text: string;
  label: string;
  emoji: string;
}

export interface SentimentStyle {
  bg: string;
  text: string;
}

/** Maps an evasion level string to badge styling. */
export function getEvasionStyle(level: string): EvasionStyle {
  if (level === "high")
    return {
      bg: "bg-red-50 dark:bg-red-900/30",
      text: "text-red-700 dark:text-red-400",
      label: "High",
      emoji: "🔴",
    };
  if (level === "medium")
    return {
      bg: "bg-amber-50 dark:bg-amber-900/30",
      text: "text-amber-700 dark:text-amber-400",
      label: "Medium",
      emoji: "🟡",
    };
  return {
    bg: "bg-green-50 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
    label: "Low",
    emoji: "🟢",
  };
}

/** Maps a defensiveness score (1–10) to an evasion level string. */
export function evasionScoreToLevel(score: number): "low" | "medium" | "high" {
  if (score >= 8) return "high";
  if (score >= 5) return "medium";
  return "low";
}

/** Maps a sentiment string to badge styling. */
export function getSentimentStyle(sentiment: string): SentimentStyle {
  const lower = sentiment.toLowerCase();
  if (
    lower.includes("bullish") ||
    lower.includes("positive") ||
    lower.includes("optimistic")
  )
    return {
      bg: "bg-green-50 dark:bg-green-900/30",
      text: "text-green-700 dark:text-green-400",
    };
  if (
    lower.includes("bearish") ||
    lower.includes("negative") ||
    lower.includes("cautious")
  )
    return {
      bg: "bg-red-50 dark:bg-red-900/30",
      text: "text-red-700 dark:text-red-400",
    };
  return { bg: "bg-muted", text: "text-muted-foreground" };
}
