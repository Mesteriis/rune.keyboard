# Complete API37 preview-policy run — 2026-09-06

131 application tests:127 PASS,3 optional-model assumptions,1 FAIL;834.793 seconds. Exact installed APK/source hashes are in input-receipt.json. The replacement preview-policy test passes inside this complete suite. Its normal-enabled/disabled/password-enabled phases observed4633/0/0 maximum changed pixels over bounded samples. It is not a frame-latency or continuous-absence result; earlier A/150ms failures remain in their original archives.

The sole failure is doubleSpaceUndoSurvivesBinderSelectionAcknowledgement: expected `a. `, observed `a  `. The test did not set its double-space preference. Content-free preference inspection after the complete run found double_space_period=false, mechanical_punctuation=false and autocorrection_mode=OFF. This is an after-run observation, not a failure-time snapshot or proof of the earlier state-transition cause. The follow-up fixture explicitly enables the tested gesture; its new execution belongs in a separate receipt.

This run uses the93b92f6 production APK before the command-dot product fix, raw fixture and rapid-touch additions. Source changes made while it ran are not attributed to its installed APK. Original failures are not erased by later passing runs.
