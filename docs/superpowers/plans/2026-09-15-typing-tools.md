# Six typing tools

User-approved scope: local quality dashboard; shadow algorithm comparison; word-boundary suggestions;
user-defined abbreviations; completed-phrase review; visible explicit undo of autocorrection.
Base c6543e2 in existing isolated codex/morphology-style worktree.

## Constraints
- No raw conversation/profile uploads, no raw text in quality metrics or APK private artifacts.
- Quality/shadow explicitly enabled in settings; absent/malformed values off. No-undo is not correctness.
- Existing automatic qualification and editor ownership gates stay authoritative. New boundary,
  abbreviation and phrase changes are manual suggestions with exact current owned-text allowlists.
- Only current Rune-owned suffixes may change. No editor reads to obtain/reconstruct replacement spans.
- Sensitive/no-personalized-learning fields excluded. Session, language, layer, cursor/settings transitions
  invalidate suggestions and ephemeral shadow comparisons. Raw pending text stays memory-only and bounded.
- Counts, profile sizes, context length and work are bounded. Persistence is no_backup and async atomic.

## Tasks
1. Quality counters, latency histogram, shadow comparison and dashboard UI, metrics reset (worker).
2. Pure word split/join and finished phrase correction policies + tests (worker).
3. Bounded user abbreviation store and management UI + tests (worker).
4. Controller/service integration, suggestion variants, explicit visible undo, settings, ownership tests (parent).
5. Integration checks, independent review/fixes, documentation and APK (parent + reviewer).

## Preflight interfaces
| Tasks | Shared interface | Resolution |
|---|---|---|
|1/4|numeric metrics + ephemeral pair evaluation|worker owns quality APIs/UI; parent hooks acknowledged events and timings|
|2/4|owned text -> suffix suggestion|worker pure policies; parent owns mutations and privacy admission|
|3/4|token -> user expansion|worker store/management Activity; parent suggestion and settings navigation|
|1|counts vs correctness|explicit user feedback only; unobserved decisions remain unlabelled|
|2|boundaries and phrase grammar|bounded supported rules; no unrestricted rewrite or automatic application|
|3|user-defined content|bounded normalized key, expansion validation; language scoped; no shared preferences for content|
|4|IDs/undo lifetime|session+epoch+content binding, original exact span, no delayed unknown-region reads|
|5|claims|tests verify supported behavior, no unseen accuracy claim|
