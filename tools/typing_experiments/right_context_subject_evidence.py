"""A conservative nominal-cue view, separate from dictionary word protection.

A PREP/CONJ/PRCL surface may have letter-name or other nominal homographs. A
completed bare function word does not thereby identify a following subject.
The underlying lexicon and its known-word/target certificates are unchanged.
"""
from right_context_grammar_features import RightContextGrammarFeatures

VERSION = 2
_FUNCTION_PARTS = frozenset(('PREP','CONJ','PRCL'))


class SubjectEvidenceLexicon:
    def __init__(self, lexicon):
        self.lexicon = lexicon

    def analyses(self, word):
        tags = tuple(self.lexicon.analyses(word))
        if any(a.pos in _FUNCTION_PARTS for a in tags):
            return tuple(a for a in tags if a.pos not in {'NOUN','NPRO'})
        return tags


class ReliableRightContextGrammarFeatures(RightContextGrammarFeatures):
    """Same ordered evidence fields, with function-word nominal cues excluded.

    This view belongs to source admission version 2. It does not silently
    replace the features used to train or score an already frozen model.
    """
    def __init__(self, lexicon):
        super().__init__(SubjectEvidenceLexicon(lexicon))
