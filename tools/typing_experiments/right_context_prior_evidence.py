"""Audit a prior word from public replay snapshots; never runtime editor authority.

Android offsets are UTF-16 units. An undo root may include a Rune-owned leading
comma/space; only its unchanged leading boundary may surround the replaced word.
"""

def _bytes(text):
    return text.encode('utf-16-le')


def _units(text):
    return len(_bytes(text)) // 2


def previous_word_evidence(prefix, original, observation):
    result = dict(previous=original, owned=False, inputExact=False, reason='INVALID_SNAPSHOT')
    before, after = observation.get('beforeBoundary'), observation.get('afterBoundary')
    if not isinstance(before, dict) or not isinstance(after, dict):
        return result
    if not isinstance(before.get('text'), str) or not isinstance(after.get('text'), str):
        return result
    rendered = prefix + ' ' if prefix else ''
    exact = observation.get('inputChangedByTyping') is False and before['text'] == rendered + original and after['text'].startswith(rendered)
    result['inputExact'] = exact
    if not exact:
        return result | dict(reason='INPUT_OR_PREFIX_CHANGED')
    if not after['text'].endswith(' '):
        return result | dict(reason='NO_WORD_BOUNDARY')
    previous = after['text'][len(rendered):-1]
    result['previous'] = previous
    if not previous or any(char.isspace() for char in previous):
        return result | dict(reason='INVALID_PREVIOUS_WORD')
    try:
        if (type(before.get('caret')) is not int or type(after.get('caret')) is not int
                or before['caret'] != _units(before['text']) or after['caret'] != _units(after['text'])):
            return result | dict(reason='CARET_DIVERGENCE')
        old_state, new_state = observation.get('stateBeforeBoundary') or {}, observation.get('stateAfterBoundary') or {}
        if (old_state.get('enabled') is not True or new_state.get('enabled') is not True
                or type(old_state.get('sessionId')) is not int or old_state['sessionId'] != new_state.get('sessionId')
                or old_state.get('typedWord') != original):
            return result | dict(reason='PRIVATE_STATE_DIVERGENCE')
        old_context, new_context = old_state.get('contextText'), new_state.get('contextText')
        if (not isinstance(old_context, str) or not isinstance(new_context, str)
                or not old_context.endswith(original) or not new_context.endswith(previous+' ')
                or not before['text'].endswith(old_context) or not after['text'].endswith(new_context)):
            return result | dict(reason='PRIVATE_CONTEXT_DIVERGENCE')
        if previous == original:
            return result | dict(owned=after['text'] == before['text']+' ', reason=None if after['text'] == before['text']+' ' else 'NONLOCAL_BOUNDARY_CHANGE')
        edit = observation.get('autoEdit') or {}
        start, old, new = edit.get('committedStart'), edit.get('original'), edit.get('applied')
        if (type(start) is not int or start < 0 or not isinstance(old, str) or not isinstance(new, str)
                or edit.get('hasCorrectionCandidates') is not True
                or (edit.get('correctionGeneration') or {}).get('original') != original or not old.endswith(original)):
            return result | dict(reason='MISSING_PREVIOUS_EDIT')
        leading = old[:-len(original)]
        if new != leading + previous + ' ':
            return result | dict(reason='LEADING_BOUNDARY_CHANGED')
        old_bytes, new_bytes = _bytes(old), _bytes(new)
        if (start + len(old_bytes)//2 != before['caret'] or start + len(new_bytes)//2 != after['caret']
                or _bytes(before['text'])[2*start:2*start+len(old_bytes)] != old_bytes
                or _bytes(after['text'])[2*start:2*start+len(new_bytes)] != new_bytes):
            return result | dict(reason='STALE_PREVIOUS_EDIT')
        return result | dict(owned=True, reason=None)
    except UnicodeEncodeError:
        return result | dict(reason='INVALID_UTF16_TEXT')
