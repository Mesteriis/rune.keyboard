"""Describe replay input drift without normalizing text or granting admission.

Even case/whitespace-only differences are not exact ownership evidence. These
categories explain why an evaluation row was refused, never repair that row.
"""
import re


def classify_input_change(expected, actual):
    if expected == actual:
        return 'UNCHANGED'
    left, right = re.findall(r'\S+', expected), re.findall(r'\S+', actual)
    if len(left) != len(right):
        return 'CONTENT_CHANGED'
    # Do not let expanding Unicode folds disguise an insertion/deletion.
    for before, after in zip(left, right, strict=True):
        if len(before) != len(after) or any(a != b and a.lower() != b.lower() for a, b in zip(before, after, strict=True)):
            return 'CONTENT_CHANGED'
    case_changed = left != right
    spacing_changed = re.sub(r'\S+', '\x00', expected) != re.sub(r'\S+', '\x00', actual)
    if case_changed and spacing_changed:
        return 'CASE_AND_WHITESPACE_RUNS'
    return 'CASE_ONLY' if case_changed else 'WHITESPACE_RUNS_ONLY'
