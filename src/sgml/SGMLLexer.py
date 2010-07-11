"""A lexer for SGML, using derived classes as parser and DTD.

This module provides a transparent interface allowing the use of
alternate lexical analyzers without modifying higher levels of SGML
or HTML support.
"""
__version__ = "$Revision: 1.45 $"

#  These constants are not used in this module, but are provided to
#  allow other modules to know about the concrete syntax we support.

COM = "--"                              # comment start or end
CRO = "&#"                              # character reference open
REFC = ";"                              # reference close
DSO = "["                               # declaration subset open
DSC = "]"                               # declaration subset close
ERO = "&"                               # entity reference open
LIT = '"'                               # literal start or end
LITA = "'"                              # literal start or end (alternative)
MDO = "<!"                              # markup declaration open
MDC = ">"                               # markup declaration close
MSC = "]]"                              # marked section close
NET = "/"                               # null end tag
PIO = "<?"                              # processing instruciton open
PIC = ">"                               # processing instruction close
STAGO = "<"                             # start tag open
ETAGO = "</"                            # end tag open
TAGC = ">"                              # tag close
VI = "="                                # value indicator

whitespace = '\\t\\n\x0b\x0c\\r '

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).

import re
import string

try:
    class SGMLError(Exception):
        pass
except TypeError:
    class SGMLError:
        pass


# SGML lexer base class -- find tags and call handler functions.
# Usage: p = SGMLLexer(); p.feed(data); ...; p.close().
# The data between tags is passed to the parser by calling
# self.lex_data() with some data as argument (the data may be split up
# in arbutrary chunks).  Entity references are passed by calling
# self.lex_entityref() with the entity reference as argument.


class SGMLLexerBase:
    #  This is a "dummy" base class which provides documentation on the
    #  lexer API; this can be used by tools which can extract missing
    #  method documentation from base classes.

    def feed(self, input_data):
        """Feed some data to the parser.

        input_data
            Input data to be fed to the scanner.  An empty string
            indicates end-of-input.

        Call this as often as you want, with as little or as much text
        as you want (may include '\n').
        """
        pass

    def close(self):
        """Terminate the input stream.

        If any data remains unparsed or any events have not been
        dispatched, they must be forced to do so by this method before
        returning.
        """
        pass

    def line(self):
        """Return the current line number if known.
        """

    def normalize(self, norm):
        """Control normalization of name tokens.

        norm
            Boolean indicating new setting of case normalization.

        If `norm' is true, names tokens will be converted to lower
        case before being based to the `lex_*()' interfaces described
        below.  Otherwise, names will be reported in the case in which
        they are found in the input stream.  Tokens which are affected
        include tag names, attribute names, and named character
        references.  Note that general entity references are not
        affected.

        A boolean indicating the previous value is returned.
        """
        pass

    def reset(self):
        """Attempt to reset the lexical analyzer.
        """
        pass

    def restrict(self, strict):
        """Control recognition of particular constructs.
        """
        pass

    #  The rest of the methods of this class are intended to be overridden
    #  by parser subclasses interested in different events on the input
    #  stream.  They are called by the implementation of the lexer object.

    def lex_data(self, data_string):
        """Process data characters.
        """
        pass

    def lex_starttag(self, tagname, attributes):
        """Process a start tag and attributes.

        tagname
            General identifier of the start tag encountered.

        attributes
            Dictionary of the attribute/value pairs found in the document
            source.

        The general identifier and attribute names are normalized to
        lower case if only if normalization is enabled; all attribute
        values are strings.  Attribute values coded as string literals
        using either LIT or LITA quoting will have the surrounding
        quotation marks removed.  Attributes with no value specified
        in the document source will have a value of `None' in the
        dictionary passed to this method.
        """
        pass

    def lex_endtag(self, tagname):
        """Process an end tag.

        tagname
            General identifier of the end tag found.
        """
        pass

    def lex_charref(self, ordinal, terminator):
        """Process a numeric character reference.
        """
        pass

    def lex_namedcharref(self, refname, terminator):
        """Process a named character reference.
        """
        pass

    def lex_entityref(self, refname, terminator):
        """Process a general entity reference.
        """
        pass

    def lex_pi(self, pi_data):
        """Process a processing instruction.
        """
        pass

    def lex_comment(self, comment_string):
        """Process a comment string.

        If a markup declaration consists entirely of comments, each comment
        is passed to this method in sequence.  The parser has no way of
        knowing whether multiple comments received in sequence are part of
        a single markup declaration or originated in multiple declarations.
        Empty comments ('<!>') are ignored.  Comments embedded in other
        markup declarations are not handled via this method.
        """
        pass

    def lex_declaration(self, declaration_info):
        """Process a markup declaration other than a comment.

        declaration_info
            List of strings.  The first string will be the name of the
            declaration (doctype, etc.), followed by each additional
            name, nametoken, quoted literal, or comment in the
            declaration.

        Literals and comments will include the quotation marks or
        comment delimiters to allow the client to process each
        correctly.  Normalization of names and nametokens will be
        handled as for general identifiers.
        """
        pass

    def lex_error(self, error_string):
        """Process an error packet.

        error_string
            String which describes a lexical error in the input stream.

        Values passed to this method may be affected by the current
        scanning mode.  Further callbacks may show symptoms described
        by the error described by `error_string'.
        """
        pass

    def lex_limitation(self, limit_string):
        """Process a limitation packet.

        limit_string
            String which describes a lexical limitation in the current
            scanning mode.

        Further callbacks may show symptoms determined by the limitation
        described by `limit_string'.
        """
        pass


class SGMLLexer(SGMLLexerBase):
    entitydefs = {}
    _in_parse = 0
    _finish_parse = 0

    def __init__(self):
        self.reset()

    def strict_p(self):
        return self._strict

    def cleanup(self):
        pass

    rawdata = ''
    def reset(self):
        self.stack = []
        self.lasttag = '???'
        self.nomoretags = 0
        self.literal = 0
        self._normfunc = lambda s: s
        self._strict = 0

    def close(self):
        if not self._in_parse:
            self.goahead(1)
            self.cleanup()
        else:
            self._finish_parse = 1

    def line(self):
        return None

    def feed(self, data):
        self.rawdata = self.rawdata + data
        if not self._in_parse:
            self._in_parse = 1
            self.goahead(0)
            self._in_parse = 0
            if self._finish_parse:
                self.cleanup()

    def normalize(self, norm):
        prev = ((self._normfunc is string.lower) and 1) or 0
        self._normfunc = (norm and string.lower) or (lambda s: s)
        return prev

    def restrict(self, constrain):
        prev = not self._strict
        self._strict = not ((constrain and 1) or 0)
        return prev

    def setliteral(self, tag):
        self.literal = 1
        re = "%s%s[%s]*%s" % (ETAGO, tag, whitespace, TAGC)
        if self._normfunc is string.lower:
            self._lit_etag_re = re.compile(re, re.IGNORECASE)
        else:
            self._lit_etag_re = re.compile(re)

    def setnomoretags(self):
        self.nomoretags = 1

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        #print "goahead", self.rawdata
        i = 0
        n = len(self.rawdata)
        while i < n:
            rawdata = self.rawdata  # pick up any appended data
            n = len(rawdata)
            if self.nomoretags:
                self.lex_data(rawdata[i:n])
                i = n
                break
            if self.literal:
                match = self._lit_etag_re.search(rawdata, i)
                if match:
                    pos = match.start()
                    # found end
                    self.lex_data(rawdata[i:pos])
                    i = pos + len(match.group(0))
                    self.literal = 0
                    continue
                else:
                    pos = string.rfind(rawdata, "<", i)
                    if pos >= 0:
                        self.lex_data(rawdata[i:pos])
                        i = pos
                break
            # pick up self._finish_parse as soon as possible:
            end = end or self._finish_parse
            match = interesting.search(rawdata, i)
            if match: j = match.start()
            else: j = n
            if i < j: self.lex_data(rawdata[i:j])
            i = j
            if i == n: break
            #print "interesting", j, i
            if rawdata[i] == '<':
                #print "<", self.literal, rawdata[i:20]
                if starttagopen.match(rawdata, i):
                    #print "open"
                    if self.literal:
                        self.lex_data(rawdata[i])
                        i = i+1
                        continue
                    #print "parse_starttag", self.parse_starttag
                    k = self.parse_starttag(i)
                    if k < 0: break
                    i = k
                    continue
                if endtagopen.match(rawdata, i):
                    k = self.parse_endtag(i)
                    if k < 0: break
                    i = k
                    self.literal = 0
                    continue
                if commentopen.match(rawdata, i):
                    if self.literal:
                        self.lex_data(rawdata[i])
                        i = i+1
                        continue
                    k = self.parse_comment(i, end)
                    if k < 0: break
                    i = i + k
                    continue
                match = processinginstruction.match(rawdata, i)
                if match:
                    k = match.start()
                    #  Processing instruction:
                    if self._strict:
                        self.lex_pi(match.group(1))
                        i = match.end()
                    else:
                        self.lex_data(rawdata[i])
                        i = i + 1
                    continue
                match = special.match(rawdata, i)
                if match:
                    k = match.start()
                    if k-i == 3:
                        self.lex_declaration([])
                        i = i + 3
                        continue
                    if self._strict:
                        if rawdata[i+2] in string.letters:
                            k = self.parse_declaration(i)
                            if k > -1:
                                i = i + k
                        else:
                            self.lex_data('<!')
                            i = i + 2
                    else:
                        #  Pretend it's data:
                        if self.literal:
                            self.lex_data(rawdata[i])
                            k = 1
                        i = match.end()
                    continue
            elif rawdata[i] == '&':
                charref = (self._strict and legalcharref) or simplecharref
                match = charref.match(rawdata, i)
                if match:
                    k = match.end()
                    if rawdata[k-1] not in ';\n':
                        k = k-1
                        terminator = ''
                    else:
                        terminator = rawdata[k-1]
                    name = match.group(1)[:-1]
                    postchar = ''
                    if terminator == '\n' and not self._strict:
                        postchar = '\n'
                        terminator = ''
                    if name[0] in '0123456789':
                        #  Character reference:
                        try:
                            self.lex_charref(string.atoi(name), terminator)
                        except ValueError:
                            self.lex_data("&#%s%s" % (name, terminator))
                    else:
                        #  Named character reference:
                        self.lex_namedcharref(self._normfunc(name),
                                              terminator)
                    if postchar:
                        self.lex_data(postchar)
                    i = k
                    continue
                match = entityref.match(rawdata, i)
                if match:
                    k = match.end()
                    #  General entity reference:
                    #k = i+k
                    if rawdata[k-1] not in ';\n':
                        k = k-1
                        terminator = ''
                    else:
                        terminator = rawdata[k-1]
                    name = match.group(1)
                    self.lex_entityref(name, terminator)
                    i = k
                    continue
            else:
                raise RuntimeError, 'neither < nor & ??'
            # We get here only if incomplete matches but
            # nothing else
            match = incomplete.match(rawdata, i)
            if not match:
                self.lex_data(rawdata[i])
                i = i+1
                continue
            k = match.end()
            j = k
            if j == n:
                break # Really incomplete
            self.lex_data(rawdata[i:j])
            i = j
        # end while
        if (end or self._finish_parse) and i < n:
            self.lex_data(self.rawdata[i:n])
            i = n
        self.rawdata = self.rawdata[i:]

    # Internal -- parse comment, return length or -1 if not terminated
    def parse_comment(self, i, end):
        #print "parse comment"
        rawdata = self.rawdata
        if rawdata[i:i+4] <> (MDO + COM):
            raise RuntimeError, 'unexpected call to parse_comment'
        if self._strict:
            # stricter parsing; this requires legal SGML:
            pos = i + len(MDO)
            datalength = len(rawdata)
            comments = []
            while (pos < datalength) and rawdata[pos] != MDC:
                matchlength, comment = comment_match(rawdata, pos)
                if matchlength >= 0:
                    pos = pos + matchlength
                    comments.append(comment)
                elif end:
                    self.lex_error("unexpected end of data in comment")
                    comments.append(rawdata[pos+2:])
                    pos = datalength
                elif rawdata[pos] != "-":
                    self.lex_error("illegal character in"
                                   " markup declaration: "
                                   + `rawdata[pos]`)
                    pos = pos + 1
                else:
                    return -1
            map(self.lex_comment, comments)
            return pos + len(MDC) - i
        # not strict
        match = commentclose.search(rawdata, i+4)
        if not match:
            if end:
                if MDC in rawdata[i:]:
                    j = string.find(rawdata, MDC, i)
                    self.lex_comment(rawdata[i+4: j])
                    return j + len(MDC) - i
                self.lex_comment(rawdata[i+4:])
                return len(rawdata) - i
            return -1
        j = match.start()
        self.lex_comment(rawdata[i+4: j])
        match = commentclose.match(rawdata, j)
        if match:
            j = match.start()
        return j - i

    # Internal -- handle starttag, return length or -1 if not terminated
    def parse_starttag(self, i):
        rawdata = self.rawdata
        #print "parse_starttag", rawdata
        if self._strict and shorttagopen.match(rawdata, i):
            # SGML shorthand: <tag/data/ == <tag>data</tag>
            # XXX Can data contain &... (entity or char refs)? ... yes
            # XXX Can data contain < or > (tag characters)? ... > yes,
            #                               < not as delimiter-in-context
            # XXX Can there be whitespace before the first /? ... no
            match = shorttag.match(rawdata, i)
            if not match:
                self.lex_data(rawdata[i])
                return i + 1
            k = match.end()
            tag, data = match.group(1, 2)
            tag = self._normfunc(tag)
            self.lex_starttag(tag, {})
            self.lex_data(data)     # should scan for entity refs
            self.lex_endtag(tag)
            return k
        # XXX The following should skip matching quotes (' or ")
        match = endbracket.search(rawdata, i+1)
        if not match:
            return -1
        j = match.start(0)
        #print "parse_starttag endbracket", j
        # Now parse the data between i+1 and j into a tag and attrs
        if rawdata[i:i+2] == '<>':
            #  Semantics of the empty tag are handled by lex_starttag():
            if self._strict:
                self.lex_starttag('', {})
            else:
                self.lex_data('<>')
            return i + 2

        #print "tagfind start", i+1
        match = tagfind.match(rawdata, i+1)     # matches just the GI
        if not match:
            raise RuntimeError, 'unexpected call to parse_starttag'
        k = match.end(0)
        #print "tagfind end", k
        tag = self._normfunc(rawdata[i+1:k])
        #print "tag", tag
        # pull recognizable attributes
        attrs = {}
        while k < j:
            match = attrfind.match(rawdata, k)
            if not match: break
            l = match.start(0)
            k = k + l
            # Break out the name[/value] pair:
            attrname, rest, attrvalue = match.group(1, 2, 3)
            if not rest:
                attrvalue = None    # was:  = attrname
            elif attrvalue[:1] == LITA == attrvalue[-1:] or \
                 attrvalue[:1] == LIT == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
                if '&' in attrvalue:
                    from SGMLReplacer import replace
                    attrvalue = replace(attrvalue, self.entitydefs)
            attrs[self._normfunc(attrname)] = attrvalue
            k = match.end(0)
        # close the start-tag
        xx = tagend.match(rawdata, k)
        if not xx:
            #  something vile
            endchars = self._strict and "<>/" or "<>"
            while 1:
                try:
                    while rawdata[k] in string.whitespace:
                        k = k + 1
                except IndexError:
                    return -1
                if rawdata[k] not in endchars:
                    self.lex_error("bad character in tag")
                    k = k + 1
                else:
                    break
            if not self._strict:
                if rawdata[k] == '<':
                    self.lex_limitation("unclosed start tag not supported")
                elif rawdata[k] == '/':
                    self.lex_limitation("NET-enabling start tags"
                                        " not supported")
        else:
            k = k + len(xx.group(0)) - 1
        #
        #  Vicious hack to allow XML-style empty tags, like "<hr />".
        #  We don't require the space, but appearantly it's significant
        #  on Netscape Navigator.  Only in non-strict mode.
        #
        c = rawdata[k]
        if c == '/' and not self._strict:
            if rawdata[k:k+2] == "/>":
                # using XML empty-tag hack
                self.lex_starttag(tag, attrs)
                self.lex_endtag(tag)
                return k + 2
            else:
                self.lex_starttag(tag, attrs)
                return k + 1
        if c in '>/':
            k = k + 1
        self.lex_starttag(tag, attrs)
        return k

    # Internal -- parse endtag
    def parse_endtag(self, i):
        rawdata = self.rawdata
        if rawdata[i+2] in '<>':
            if rawdata[i+2] == '<' and not self._strict:
                self.lex_limitation("unclosed end tags not supported")
                self.lex_data(ETAGO)
                return i + 2
            self.lex_endtag('')
            return i + 2 + (rawdata[i+2] == TAGC)
        match = endtag.match(rawdata, i)
        if not match:
            return -1
        j = match.end(0)-1
        #j = i + j - 1
        if rawdata[j] == TAGC:
            j = j + 1
        self.lex_endtag(self._normfunc(match.group(1)))
        return j

    def parse_declaration(self, start):
        #  This only gets used in "strict" mode.
        rawdata = self.rawdata
        i = start
        #  Markup declaration, possibly illegal:
        strs = []
        i = i + 2
        match = md_name.match(rawdata, i)
        k = match.start()
        strs.append(self._normfunc(match.group(1)))
        i = i + k
        end_target = '>'
        while k > 0:
            #  Have to check the comment pattern first so we don't get
            #  confused and think this is a name that starts with '--':
            if rawdata[i] == '[':
                self.lex_limitation("declaration subset not supported")
                end_target = ']>'
                break
            k, comment = comment_match(rawdata, i)
            if k > 0:
                strs.append(comment)
                i = i + k
                continue
            match = md_string.match(rawdata, i)
            if match:
                k = match.start()
                strs.append(match.group(1))
                i = i + k
                continue
            match = md_name.match(rawdata, i)
            if match:
                k = match.start()
                s = match.group(1)
                try:
                    strs.append(string.atoi(s))
                except string.atoi_error:
                    strs.append(self._normfunc(s))
                i = i + k
                continue
        k = string.find(rawdata, end_target, i)
        if end_target == ']>':
            if k < 0:
                k = string.find(rawdata, '>', i)
            else:
                k = k + 1
        if k >= 0:
            i = k + 1
        else:
            return -1
        self.lex_declaration(strs)
        return i - start


# Regular expressions used for parsing:
OPTIONAL_WHITESPACE = "[%s]*" % whitespace
interesting = re.compile('[&<]')
incomplete = re.compile('&([a-zA-Z][a-zA-Z0-9]*|'
                           '#[0-9]*)?|'
                           '<([a-zA-Z][^<>]*|'
                           '/([a-zA-Z][^<>]*)?|'
                           '![^<>]*)?')

entityref = re.compile(ERO + '([a-zA-Z][-.a-zA-Z0-9]*)[^-.a-zA-Z0-9]')
simplecharref = re.compile(CRO + '([0-9]+[^0-9])')
legalcharref \
    = re.compile(CRO + '([0-9]+[^0-9]|[a-zA-Z.-]+[^a-zA-Z.-])')
processinginstruction = re.compile('<\\?([^>]*)' + PIC)

starttagopen = re.compile(STAGO + '[>a-zA-Z]')
shorttagopen = re.compile(STAGO + '[a-zA-Z][-.a-zA-Z0-9]*'
                             + OPTIONAL_WHITESPACE + NET)
shorttag = re.compile(STAGO + '([a-zA-Z][-.a-zA-Z0-9]*)'
                         + OPTIONAL_WHITESPACE + NET + '([^/]*)' + NET)
endtagopen = re.compile(ETAGO + '[<>a-zA-Z]')
endbracket = re.compile('[<>]')
endtag = re.compile(ETAGO +
                       '([a-zA-Z][-.a-zA-Z0-9]*)'
                       '([^-.<>a-zA-Z0-9]?[^<>]*)[<>]')
special = re.compile(MDO + '[^>]*' + MDC)
markupdeclaration = re.compile(MDO +
                                  '(([-.a-zA-Z0-9]+|'
                                  + LIT + '[^"]*' + LIT + '|'
                                  + LITA + "[^']*" + LITA + '|'
                                  + COM + '([^-]|-[^-])*' + COM
                                  + ')' + OPTIONAL_WHITESPACE
                                  + ')*' + MDC)
md_name = re.compile('([^>%s\'"]+)' % whitespace
                        + OPTIONAL_WHITESPACE)
md_string = re.compile('("[^"]*"|\'[^\']*\')' + OPTIONAL_WHITESPACE)
commentopen = re.compile(MDO + COM)
commentclose = re.compile(COM + OPTIONAL_WHITESPACE + MDC)
tagfind = re.compile('[a-zA-Z][-_.a-zA-Z0-9]*')
attrfind = re.compile(
    # comma is for compatibility
    ('[%s,]*([_a-zA-Z][-:.a-zA-Z_0-9]*)' % whitespace)
    + '(' + OPTIONAL_WHITESPACE + VI + OPTIONAL_WHITESPACE # VI
    + '(' + LITA + "[^']*" + LITA
    + '|' + LIT + '[^"]*' + LIT
    + '|[\-~a-zA-Z0-9,./:+*%?!\\(\\)_#=]*))?')
tagend = re.compile(OPTIONAL_WHITESPACE + '[<>/]')

# used below in comment_match()
comment_start = re.compile(COM + '([^-]*)-(.|\\n)')
comment_segment = re.compile('([^-]*)-(.|\\n)')
comment_whitespace = re.compile(OPTIONAL_WHITESPACE)

del re

def comment_match(rawdata, start):
    """Match a legal SGML comment.

    rawdata
        Data buffer, as a string.

    start
        Starting index into buffer.  This should point to the `<'
        character of the Markup Declaration Open.

    Analyzes SGML comments using very simple regular expressions to
    ensure that the limits of the regular expression package are not
    exceeded.  Very long comments with embedded hyphens which cross
    buffer boundaries can easily generate problems with less-than-
    ideal RE implementations.

    Returns the number of characters to consume from the input buffer
    (*not* including the first `start' characters!) and the text of
    comment located.  If no comment was identified, returns -1 and
    an empty string.
    """
    matcher = comment_start.match(rawdata, start)
    if not matcher or matcher.start() < 0:
        return -1, ''
    pos = start
    comment = ''
    matchlength = m.start()
    while matchlength >= 0:
        if matcher.group(2) == "-":
            # skip any whitespace
            ws = comment_whitespace.match(rawdata, pos + matchlength)
            if ws:
                ws = ws.start()
            else:
                ws = 0
            pos = pos + matchlength + ws
            return pos - start, comment + matcher.group(1)
        # only a partial match
        comment = "%s%s-%s" % (comment,
                               matcher.group(1), matcher.group(2))
        pos = pos + matchlength
        matcher = comment_segment.match(rawdata, pos)
        if not matcher:
            matchlength = -1
        else:
            matchlength = matcher.start()
    return -1, ''
