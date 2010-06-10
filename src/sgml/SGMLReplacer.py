"""Simple parser that handles only what's allowed in attribute values."""
__version__ = '$Revision: 1.14 $'

import re
import string


_entref_search = re.compile("&(#?([a-zA-Z0-9][-.a-zA-Z0-9]*));?").search
del re

_named_chars = {'#re' : '\r',
                '#rs' : '\n',
                '#space' : ' '}

for i in range(256):
    _named_chars["#" + `i`] = chr(i)

#  build a table suitable for string.translate()
_chartable = map(chr, range(256))
for i in range(256):
    if chr(i) in string.whitespace:
        _chartable[i] = " "
_chartable = string.joinfields(_chartable, '')


def replace(data, entities={}):
    """Perform general entity replacement on a string."""
    data = string.translate(data, _chartable)
    if '&' in data:
        value = None
        m = _entref_search(data)
        while m:
            ref, term = m.group(1, 2)
            pos = m.start()
            if entities.has_key(ref):
                value = entities[ref]
            elif _named_chars.has_key(string.lower(ref)):
                value = _named_chars[string.lower(ref)]
            if value is not None:
                data = data[:pos] + value + data[m.end():]
                pos = pos + len(value)
                value = None
            else:
                pos = m.end()
            m = _entref_search(data, pos)
    return data
