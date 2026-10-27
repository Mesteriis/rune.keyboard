"""Experimental source-v4: a letter/initial is not a proved nominal subject.

The frozen source-v3 and all its checks remain unchanged. True nominative
pronouns such as "я" keep their reading; longer names/acronyms are not banned.
"""
from right_context_continuation_features import scan_continuation
from right_context_continuation_source import ContinuationSourceScope
from right_context_subject_evidence import SubjectEvidenceLexicon


def nominal_surface_refusal(right_context, lexicon):
    words = scan_continuation(right_context).words
    if not words or len(words[0]) != 1:
        return None
    tags = SubjectEvidenceLexicon(lexicon).analyses(words[0])
    if any(a.pos == 'NPRO' and a.case == 'nomn' for a in tags):
        return None
    return 'SINGLE_LETTER_NOMINAL_UNPROVEN'


class SurfaceAwareContinuationSource:
    VERSION = 4

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.previous = ContinuationSourceScope(lexicon)

    def precondition_refusal(self, *, left_context, **arguments):
        refused = self.previous.precondition_refusal(left_context=left_context, **arguments)
        if refused:
            return refused
        return nominal_surface_refusal(arguments['right_context'], self.lexicon)

    def refusal(self, *, left_context, **arguments):
        refused = self.previous.refusal(left_context=left_context, **arguments)
        if refused:
            return refused
        return nominal_surface_refusal(arguments['right_context'], self.lexicon)
