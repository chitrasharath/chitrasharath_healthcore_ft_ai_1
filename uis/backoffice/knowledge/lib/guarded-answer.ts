/** Detect guarded refusal / redirect answers for a subtle UI note. */

const SAFETY_CUES = [
  "I can't change or ignore my instructions",
  "I can't help with personal tasks unrelated to HealthCore",
  "For privacy (HIPAA / UK GDPR)",
  "I can't share that. I can help with",
  "By the way — I'm here for HealthCore questions",
] as const;

export function isGuardedAnswer(answer: string, sourcesLength: number): boolean {
  if (sourcesLength > 0) return false;
  return SAFETY_CUES.some((cue) => answer.includes(cue));
}
