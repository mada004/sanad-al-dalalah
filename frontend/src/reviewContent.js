// Frontend mock adapter only. Keep the agreed response fields unchanged.
// The current mock suggestions include editorial instructions; extract wording
// only for known mock formats, never infer religious content or a new ruling.
export function getImprovement(claim) {
  const suggestion = claim.suggestion?.trim();
  if (!suggestion || suggestion.startsWith('يمكن إبقاء الصياغة:')) return null;
  const marker = 'ويمكن الاكتفاء بعبارة:';
  return suggestion.includes(marker)
    ? suggestion.split(marker)[1].trim()
    : suggestion;
}

// Mock full-content assembly: replace exact matches with accepted suggestions.
// Preserve all unmatched input and avoid replacing inside earlier improvements.
export function buildImprovedContent(original, claims, decisions) {
  let parts = [{ text: original, changed: false }];
  let applied = 0;
  let unmatched = 0;
  claims.forEach((claim, index) => {
    const suggestion = getImprovement(claim);
    if (decisions[index] !== 'improved' || !suggestion) return;
    let found = false;
    parts = parts.flatMap((part) => {
      if (part.changed || !claim.claim || !part.text.includes(claim.claim)) return [part];
      found = true;
      const pieces = part.text.split(claim.claim);
      return pieces.flatMap((text, position) => position === 0
        ? [{ text, changed: false }]
        : [{ text: suggestion, changed: true }, { text, changed: false }]);
    });
    if (found) applied += 1;
    else unmatched += 1;
  });
  return { parts, text: parts.map((part) => part.text).join(''), applied, unmatched };
}
