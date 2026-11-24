# U11: current product replay on disclosed EWT annotations

The current model-free controller was replayed twice on 351 English positions
from the already disclosed, pinned UD English EWT source. The input generator
requires whole-sentence reconstruction to match the source exactly, rejects
sentences with multiword/decimal token IDs, and limits the prefix to at most
128 characters of simple ASCII words with at least two preceding words. It
excludes 2,828 sentences with non-integer token IDs and one unaligned sentence.
This conservative subset is neither representative of the full corpus nor an
independent holdout. Its source annotations have not been independently
adjudicated. Only the five label-free fields were sent to the controller; the
host retained correction labels separately. Model calls: zero.

The subset contains 186 single-edit `CorrectForm` positions (136 train, 26 dev,
24 test). Rune preserved the original at all 186 boundaries. The annotated
target was present in the recorded full-token alternatives for 89 positions;
this does not mean it was visible or safe to apply. Boundary diagnostics were:

| Diagnostic reason | Positions |
| --- | ---: |
| `ORIGINAL_VALID` | 82 |
| `SERVICE_REFUSED` | 97 |
| `NOT_QUALIFIED` | 6 |
| `LOCAL_SEARCH_EMPTY` | 1 |

The replay deliberately has no model service, so `SERVICE_REFUSED` is a
model-free test condition, not a measured production outage. Likewise,
`ORIGINAL_VALID` identifies a protection decision; it does not prove that a
particular annotation should override that protection.

The remaining 165 test positions are unknown words without `CorrectForm` and
not equal to the previously used annotated train/dev words. Rune preserved 164
and made one case-only automatic change, reported by `CANONICAL_CASE`. Absence
of an annotation is not a verified correct-word label, so this is not a
false-change estimate. Immediate Backspace restored the pre-boundary text for
all 351 positions in the host editor simulation. This does not establish
Android timing or physical-device behavior.

The [aggregate receipt](2026-11-03-u11-ewt-product-replay.json) contains no
source sentences or tokens. The two controller projections were identical after
the established timing exclusions. The private source-aligned inputs, labels and raw observations were used only
in owner-only `build/` directories and removed after aggregation.
Before replay, 533 exact input/annotated-target contexts were registered in the
control ledger; a further 945 observed candidate contexts were registered
afterwards, of which 505 were new beyond existing exclusions. Hashes of public
text are unsalted and do not anonymize it. These additions do not establish
English family completeness or permit independent qualification. No product
policy, model, APK or phone was changed.

Validation: 11 replay/report/registration tests passed in the checkout and in a
staged source archive without `build/`; both registry checks passed there too.
Twenty-five preparation tests, six public control-ledger tests, four EWT control
registration tests and the isolated historical text/neighbor checks passed.
A second source extraction reproduced both label-free inputs and host-only
labels byte for byte. Hosted CI was not run.
