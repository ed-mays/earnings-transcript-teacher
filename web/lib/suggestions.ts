/** Derives up to 4 question-phrased starter topics from a call's themes and keywords. */
export function buildSuggestions(themes: string[], keywords: string[]): string[] {
  const suggestions: string[] = [];

  for (const theme of themes) {
    if (suggestions.length >= 4) break;
    suggestions.push(`Explain "${theme}" in simple terms`);
  }

  for (const keyword of keywords) {
    if (suggestions.length >= 4) break;
    suggestions.push(`What does "${keyword}" mean for investors?`);
  }

  return suggestions;
}
