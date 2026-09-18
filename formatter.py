"""AST-directed layout. Python source is parsed, never imported or executed."""
import ast
import io
import json
import keyword
import sys
import tokenize
from bisect import bisect_left

DEFAULTS = dict(outerIndent=2, chainIndent=0, argumentIndent=2,
                maxInlineLength=88, leadingComma=False, expandBooleanOperators=True, arithmeticLayout='auto')
INLINE_SUFFIXES = {'alias', 'cast', 'otherwise', 'over', 'asc', 'desc',
                   'isNull', 'isNotNull', 'isin', 'contains', 'startswith', 'endswith',
                   'getItem', 'getField', 'eqNullSafe', 'between', 'rlike', 'like', 'substr'}
IGNORED = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.INDENT,
           tokenize.DEDENT, tokenize.NEWLINE, tokenize.NL}


def tokens(source):
    """Keep interpolated strings opaque while retaining their exact spelling.

    Python <=3.11 already emits f-strings as STRING. Python >=3.12 exposes
    FSTRING_START/MIDDLE/END, including nested interpolations. Group only those
    tokenizer-delimited spans; do not reconstruct or format their contents.
    """
    raw = tokenize.generate_tokens(io.StringIO(source).readline)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    fstart = getattr(tokenize, 'FSTRING_START', None)
    fend = getattr(tokenize, 'FSTRING_END', None)
    result = []
    for token in raw:
        if token.type == fstart:
            first = token
            depth = 1
            while depth:
                token = next(raw)
                if token.type == fstart:
                    depth += 1
                elif token.type == fend:
                    depth -= 1
            a = offsets[first.start[0] - 1] + first.start[1]
            b = offsets[token.end[0] - 1] + token.end[1]
            result.append(tokenize.TokenInfo(tokenize.STRING, source[a:b], first.start, token.end, first.line))
        elif token.type not in IGNORED:
            result.append(token)
    return result


def sanitize_unicode_whitespace(source):
    """Normalize problematic Unicode whitespace in Python code only.

    Non-ASCII whitespace copied from browsers, chat clients and rich text can
    look identical to a regular space while making Python reject the source
    (for example U+00A0 NO-BREAK SPACE). Replace those characters only when
    they occur outside STRING and COMMENT tokens, preserving literal/comment
    contents byte-for-byte.
    """
    if not any((ch.isspace() and ch not in ' \t\r\n\f\v') for ch in source):
        return source

    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    protected = []
    try:
        raw = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in raw:
            if tok.type not in (tokenize.STRING, tokenize.COMMENT):
                continue
            start = offsets[tok.start[0] - 1] + tok.start[1]
            end = offsets[tok.end[0] - 1] + tok.end[1]
            protected.append((start, end))
    except (tokenize.TokenError, IndentationError):
        # The parser will report genuinely malformed source later. Spans that
        # were tokenized successfully remain sufficient to protect completed
        # strings/comments before that point.
        pass

    chars = list(source)
    span_index = 0
    for i, ch in enumerate(chars):
        if not (ch.isspace() and ch not in ' \t\r\n\f\v'):
            continue
        while span_index < len(protected) and protected[span_index][1] <= i:
            span_index += 1
        inside_protected = (span_index < len(protected)
                            and protected[span_index][0] <= i < protected[span_index][1])
        if not inside_protected:
            chars[i] = ' '
    return ''.join(chars)


def tree(source):
    # The synthetic suite accepts a complete, indented selection without
    # dedenting (which could change the contents of multiline strings).
    significant = [line for line in source.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    prefix = 'if True:\n' if significant and significant[0][:1].isspace() else ''
    return ast.parse(prefix + source, type_comments=True), prefix


def signature(source):
    parsed = tree(source)[0]
    for node in ast.walk(parsed):
        if isinstance(node, ast.TypeIgnore):
            node.lineno = 0  # location is a field here, unlike other AST nodes
    return ast.dump(parsed, include_attributes=False)


def lexical_signature(source):
    # Parentheses may be added solely for implicit line continuation. All other
    # tokens, including comments, literal spelling and tuple commas, must match.
    return [(t.type, t.string) for t in tokens(source)
            if not (t.type == tokenize.OP and t.string in ('(', ')'))]


def walk(node):
    yield node
    # Treat literal strings (including f-strings) as opaque source.
    if isinstance(node, (ast.JoinedStr, ast.Constant)):
        return
    for child in ast.iter_child_nodes(node):
        yield from walk(child)


class Layout:
    def __init__(self, source, opts, indent, expanded=()):
        self.source, self.opts, self.indent = source, opts, indent
        self.expanded = expanded
        self.ts = tokens(source)
        self.lines = source.splitlines(keepends=True)
        self.line_offsets = [0]
        for line in self.lines:
            self.line_offsets.append(self.line_offsets[-1] + len(line))
        self.starts = [self.line_offsets[t.start[0] - 1] + t.start[1] for t in self.ts]
        self.ends = [self.line_offsets[t.end[0] - 1] + t.end[1] for t in self.ts]
        self.pairs, self.depth = {}, []
        stack = []
        for i, t in enumerate(self.ts):
            self.depth.append(len(stack))
            if t.type == tokenize.OP and t.string in '([{':
                stack.append(i)
            elif t.type == tokenize.OP and t.string in ')]}':
                j = stack.pop()
                self.pairs[i] = j
                self.pairs[j] = i
        self.breaks = {}  # token index -> (break kind, anchor token)
        self.chain_anchors = {}

    def position(self, line, byte_offset):
        return self.line_offsets[line - 1] + len(self.lines[line - 1].encode('utf-8')[:byte_offset].decode('utf-8'))

    def node_width(self, node):
        return self.position(node.end_lineno, node.end_col_offset) - self.position(node.lineno, node.col_offset)

    def start(self, node):
        return bisect_left(self.starts, self.position(node.lineno, node.col_offset))

    def end(self, node):
        return bisect_left(self.ends, self.position(node.end_lineno, node.end_col_offset))

    def enclosing(self, i):
        for j in range(i - 1, -1, -1):
            if j in self.pairs and j < i < self.pairs[j]:
                return j
        return None

    def expand(self, node, items):
        close = self.end(node)
        if close not in self.pairs or self.pairs[close] >= close or not items:
            return
        opening = self.pairs[close]
        if not isinstance(node, ast.Call) and opening != self.start(node):
            return  # an unparenthesized tuple may end in a nested collection
        if opening + 1 == close:
            return
        self.breaks[opening + 1] = ('item', opening)
        self.breaks[close] = ('close', opening)
        # AST item boundaries distinguish lambda parameters, generator targets,
        # dictionary entries, keyword arguments and actual argument separators.
        has_comments = any(t.type == tokenize.COMMENT for t in self.ts[opening + 1:close])
        for left, right in zip(items, items[1:]):
            lo, hi = self.end(left) + 1, self.start(right)
            comma = next((i for i in range(lo, hi) if self.ts[i].string == ','), None)
            if comma is not None:
                target = comma if self.opts['leadingComma'] and not has_comments else comma + 1
                self.breaks[target] = ('item', opening)

    def expand_dict(self, node):
        """Expand dictionary entries as key/value units, one entry per line."""
        close = self.end(node)
        opening = self.pairs.get(close)
        if opening is None or opening >= close or opening != self.start(node) or not node.values:
            return
        self.breaks[opening + 1] = ('item', opening)
        self.breaks[close] = ('close', opening)
        has_comments = any(t.type == tokenize.COMMENT for t in self.ts[opening + 1:close])
        entries = list(zip(node.keys, node.values))
        for (_, left_value), (right_key, right_value) in zip(entries, entries[1:]):
            right = right_key if right_key is not None else right_value
            lo, hi = self.end(left_value) + 1, self.start(right)
            comma = next((i for i in range(lo, hi) if self.ts[i].string == ','), None)
            if comma is not None:
                target = comma if self.opts['leadingComma'] and not has_comments else comma + 1
                self.breaks[target] = ('item', opening)

    def chain_dot(self, node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return None
        if node.func.attr in INLINE_SUFFIXES:
            return None
        base = node.func.value
        # A short modifier on a constructor/function result is not a fluent
        # dataframe pipeline. Keep col(...).method(...) on a single line.
        chain = (isinstance(base, ast.Call) and
                 (isinstance(base.func, ast.Attribute) or self.node_width(node) > self.opts['maxInlineLength']))
        chain = chain or (isinstance(base, ast.Attribute) and base.attr in {'builder', 'read', 'write'})
        if not chain:
            return None
        return next((i for i in range(self.end(base) + 1, self.end(node.func) + 1)
                     if self.ts[i].string == '.'), None)

    def comprehension(self, node, force=False):
        close = self.end(node)
        opening = self.pairs.get(close)
        if opening is None or opening >= close or self.start(node) != opening:
            return
        if (not force and self.node_width(node) <= self.opts['maxInlineLength']
                and not any(opening < i < close for i in self.breaks)
                and not any(t.type == tokenize.COMMENT for t in self.ts[opening + 1:close])):
            return
        self.breaks[opening + 1] = ('item', opening)
        self.breaks[close] = ('close', opening)
        previous = node.value if isinstance(node, ast.DictComp) else node.elt
        for generator in node.generators:
            # Clause boundaries come from the AST; token lookup is restricted
            # to the gap between the preceding expression and this target.
            start = next((i for i in range(self.end(previous) + 1, self.start(generator.target))
                          if self.ts[i].type == tokenize.NAME and self.ts[i].string == 'for'), None)
            if start is not None:
                if generator.is_async:
                    start = next(i for i in range(start - 1, self.end(previous), -1)
                                 if self.ts[i].type == tokenize.NAME and self.ts[i].string == 'async')
                self.breaks[start] = ('item', opening)
            previous = generator.iter
            for condition in generator.ifs:
                start = next((i for i in range(self.end(previous) + 1, self.start(condition))
                              if self.ts[i].type == tokenize.NAME and self.ts[i].string == 'if'), None)
                if start is not None:
                    self.breaks[start] = ('item', opening)
                previous = condition

    def is_outer_group(self, opening):
        return (self.depth[opening] == 0 and self.ts[opening].string == '('
                and opening not in self.call_openings)

    def outer_group_ancestor(self, token_index):
        current = token_index
        while current is not None:
            if current in self.pairs and self.is_outer_group(current):
                return current
            current = self.enclosing(current)
        return None

    def plan(self, root):
        self.call_openings = {self.pairs[self.end(node)] for node in walk(root)
                              if isinstance(node, ast.Call) and self.end(node) in self.pairs}
        self.arithmetic_groups = set()
        for expression in walk(root):
            if not isinstance(expression, ast.BinOp) or type(expression.op) not in ARITHMETIC:
                continue
            start, end = self.start(expression), self.end(expression)
            while (start > 0 and start - 1 not in self.call_openings
                   and self.ts[start - 1].string == '(' and self.pairs.get(start - 1) == end + 1):
                self.arithmetic_groups.add(start - 1)
                start, end = start - 1, end + 1
        for node in reversed(list(walk(root))):
            if isinstance(node, ast.Call):
                args = sorted([*node.args, *node.keywords], key=lambda x: (x.lineno, x.col_offset))
                # A chained Call's AST span includes every preceding operation.
                # Measure only this method and its arguments for layout.
                local_start = self.start(node)
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                    local_start = next((i for i in range(self.end(node.func.value) + 1, self.end(node.func) + 1)
                                        if self.ts[i].string == '.'), local_start)
                local_width = self.ends[self.end(node)] - self.starts[local_start]
                def argument_multiline(arg):
                    start, end = self.start(arg), self.end(arg)
                    while (start > 0 and start - 1 not in self.call_openings
                           and self.ts[start - 1].string == '('
                           and self.pairs.get(start - 1) == end + 1):
                        start, end = start - 1, end + 1
                    return arg.lineno != arg.end_lineno or any(start < i <= end for i in self.breaks)
                nested_argument = any(argument_multiline(arg) for arg in args)
                compact_suffix = isinstance(node.func, ast.Attribute) and node.func.attr in INLINE_SUFFIXES
                force_predicate = (isinstance(node.func, ast.Attribute)
                                   and node.func.attr in {'filter', 'where'}
                                   and any(isinstance(arg, (ast.BoolOp, ast.BinOp))
                                           and (isinstance(arg, ast.BoolOp)
                                                or isinstance(arg.op, (ast.BitAnd, ast.BitOr)))
                                           for arg in node.args))
                if ((len(args) > 2 and not compact_suffix) or ast.dump(node) in self.expanded
                        or local_width > self.opts['maxInlineLength']
                        or nested_argument or force_predicate):
                    self.expand(node, args)
                    # In a vertical argument list, expose the construction of
                    # unpacked projections rather than hiding it after '*['.
                    for arg in args:
                        if isinstance(arg, ast.Starred) and isinstance(arg.value, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                            self.comprehension(arg.value, force=True)
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                self.comprehension(node)
            elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                if (ast.dump(node) in self.expanded or
                        len(node.elts) > 1 and (isinstance(node, ast.List) or self.node_width(node) > self.opts['maxInlineLength'])
                        or any(self.start(node) < i < self.end(node) for i in self.breaks)):
                    self.expand(node, node.elts)
            elif isinstance(node, ast.Dict) and (len(node.values) > 1 or ast.dump(node) in self.expanded):
                self.expand_dict(node)
            elif self.opts['expandBooleanOperators'] and isinstance(node, (ast.BoolOp, ast.BinOp)):
                if isinstance(node, ast.BoolOp):
                    operands = node.values
                    op = 'and' if isinstance(node.op, ast.And) else 'or'
                elif isinstance(node.op, (ast.BitAnd, ast.BitOr)):
                    operands = [node.left, node.right]
                    op = '&' if isinstance(node.op, ast.BitAnd) else '|'
                else:
                    continue
                for left, right in zip(operands, operands[1:]):
                    i = next((i for i in range(self.end(left) + 1, self.start(right))
                              if self.ts[i].string == op), None)
                    if i is not None and self.enclosing(i) is not None:
                        self.breaks[i] = ('boolean', self.enclosing(i))

    def plan_chain_alignment(self, root):
        """Keep the first chain segment inline and align continuations to its dot.

        The anchor is the first top-level dot in the fluent expression. Dots
        nested inside call arguments are ignored.
        """
        planned = set()
        for node in walk(root):
            if not isinstance(node, ast.Call):
                continue
            dot = self.chain_dot(node)
            if dot is None or dot in planned:
                continue
            enclosing = self.enclosing(dot)
            if enclosing is None:
                continue
            start = self.start(node)
            first_dot = next(
                (i for i in range(start, dot)
                 if self.ts[i].string == '.' and self.enclosing(i) == enclosing),
                None
            )
            if first_dot is None:
                continue
            self.breaks[dot] = ('aligned_chain', first_dot)
            planned.add(dot)


    def plan_arithmetic(self, root):
        for expression in arithmetic_roots(root):
            if not expand_arithmetic(expression, self, self.opts):
                continue
            if self.opts['arithmeticLayout'] == 'expanded':
                nodes = [n for n in walk(expression) if isinstance(n, ast.BinOp) and type(n.op) in ARITHMETIC]
            else:
                # A long sum exposes its top-level terms. Products, quotients,
                # powers and parenthesized subexpressions stay intact as terms.
                nodes = [expression]
                left = expression.left
                while (isinstance(expression.op, (ast.Add, ast.Sub))
                       and isinstance(left, ast.BinOp) and isinstance(left.op, (ast.Add, ast.Sub))):
                    # Respect an explicit group around the left subexpression.
                    start, end = self.start(left), self.end(left)
                    if start > 0 and self.pairs.get(start - 1) == end + 1:
                        break
                    nodes.append(left)
                    left = left.left
            for node in nodes:
                operator = ARITHMETIC[type(node.op)]
                i = next((i for i in range(self.end(node.left) + 1, self.start(node.right))
                          if self.ts[i].string == operator), None)
                if i is not None and self.enclosing(i) is not None:
                    self.breaks[i] = ('boolean', self.enclosing(i))

    def plan_delimiter_alignment(self):
        """Align matching delimiters and expose directly nested groups.

        Expansion itself is still decided by the AST/layout rules.  This pass
        only propagates multiline layout through a *directly nested opener*:
        when a group starts with another delimiter and that child is multiline,
        the parent is made multiline too.  This gives the intended visual
        hierarchy::

            (
                [
                    {
                    }
                ]
            )

        without making unrelated calls multiline merely because a descendant
        somewhere inside their arguments is multiline.
        """
        multiline = set()

        def mark_existing():
            for close, opening in self.pairs.items():
                if close <= opening:
                    continue
                if (self.breaks.get(opening + 1, (None,))[0] in ('item', 'outer')
                        or self.breaks.get(close, (None,))[0] == 'close'):
                    multiline.add(opening)

        mark_existing()
        for opening, close in sorted(self.pairs.items(), reverse=True):
            if opening >= close or opening in self.call_openings:
                continue
            child = opening + 1
            if (any(opening < i < close for i in self.breaks)
                    or child < close and self.ts[child].string in ('(', '[', '{')
                    and child not in self.call_openings and opening not in self.arithmetic_groups):
                self.breaks[child] = ('item', opening)
                self.breaks[close] = ('close', opening)
                multiline.add(opening)

        changed = True
        while changed:
            changed = False
            # Inspect every pair, not only pairs already known to be multiline:
            # a compact parent may contain a directly nested multiline child.
            for opening in sorted(self.pairs):
                close = self.pairs.get(opening)
                if close is None or close <= opening:
                    continue
                child = opening + 1
                if child >= close or self.ts[child].type != tokenize.OP or self.ts[child].string not in '([{':
                    continue
                child_close = self.pairs.get(child)
                if child_close not in self.pairs or child not in multiline:
                    continue

                # A group containing a directly nested multiline opener must
                # itself become multiline, even when it has only one element.
                if opening not in multiline:
                    self.breaks[opening + 1] = ('item', opening)
                    multiline.add(opening)
                    changed = True

                # Child opener starts a new hierarchy level.
                if self.breaks.get(child) != ('item', opening):
                    self.breaks[child] = ('item', opening)
                    changed = True

        for opening in multiline:
            close = self.pairs.get(opening)
            if close is not None:
                # A grouping delimiter that introduces a nested collection gets
                # its own hierarchy line. A *call* delimiter is different: the
                # function/method name and its opening '(' must stay together:
                #
                #     winners.append(
                #         { ... }
                #     )
                #
                # When the whole call is wrapped in an outer grouping pair, that
                # outer pair provides the vertical level above the call.
                parent = self.enclosing(opening)
                if opening not in self.call_openings:
                    # Keep a top-level collection opener attached to the
                    # expression that introduces it (`x = [` / `x = {`).
                    # Only a delimiter nested inside an already-multiline
                    # hierarchy gets its own opener line. This distinction is
                    # essential: the hierarchy is about *nested* delimiters,
                    # not about moving every []/{} onto a new line.
                    parent_is_multiline = parent in multiline if parent is not None else False
                    if parent_is_multiline and opening == parent + 1:
                        self.breaks.setdefault(opening, ('open', parent))
                    elif parent is None and opening > 0 and self.ts[opening - 1].string in {'=', ':=', 'return', 'yield', 'raise'}:
                        # Keep an RHS/grouping opener attached to the expression
                        # introducer: `value = (` rather than moving `(` to a
                        # separate line.
                        if self.breaks.get(opening, (None,))[0] == 'open':
                            self.breaks.pop(opening, None)
                    # The contents of this hierarchy level begin one argument
                    # indentation to the right of its opening delimiter.
                    self.breaks.setdefault(opening + 1, ('item', opening))
                else:
                    # Keep `name(` together. Its first argument already has its
                    # own break when the call is multiline.
                    self.breaks.pop(opening, None)
                self.breaks[close] = ('close', opening)

    def plan_comments(self):
        # Comments stay in token order, attached to the same preceding/following
        # code. Delimiters containing comments use trailing separators, so a
        # comma never has to cross a section comment to lead the next item.
        for i, t in enumerate(self.ts):
            if t.type != tokenize.COMMENT:
                continue
            anchor = self.enclosing(i)
            if anchor is None:
                continue
            inline = i > 0 and self.ts[i - 1].end[0] == t.start[0]
            if inline:
                self.breaks.pop(i, None)
            else:
                self.breaks[i] = ('item', anchor)
            if i + 1 < len(self.ts):
                kind = 'close' if self.pairs.get(i + 1) == anchor else 'item'
                self.breaks.setdefault(i + 1, (kind, anchor))

    def render(self):
        dict_colons = set()
        for node in walk(ast.parse(self.source, type_comments=True)):
            if isinstance(node, (ast.Dict, ast.DictComp)):
                entries = zip(node.keys, node.values) if isinstance(node, ast.Dict) else [(node.key, node.value)]
                for key, value in entries:
                    if key is not None:
                        colon = next((j for j in range(self.end(key) + 1, self.start(value))
                                      if self.ts[j].string == ':'), None)
                        if colon is not None:
                            dict_colons.add(colon)

        result, rendered_positions, rendered_line_indents = '', {}, {}
        current_col = self.indent
        current_line_indent = self.indent

        def set_line_start(target):
            nonlocal current_col, current_line_indent
            current_col = target
            current_line_indent = target

        for i, t in enumerate(self.ts):
            gap = self.source[self.ends[i - 1]:self.starts[i]] if i else ''
            if i in dict_colons and '\n' not in gap:
                gap = ''

            if i in self.breaks:
                kind, anchor = self.breaks[i]
                base = rendered_positions.get(anchor, self.indent)
                if kind == 'close':
                    target = base
                elif kind == 'aligned_chain':
                    target = base + self.opts['chainIndent']
                elif kind == 'outer':
                    target = base + self.opts['outerIndent']
                elif anchor is None:
                    target = self.indent
                elif anchor is not None and self.is_outer_group(anchor):
                    target = base + self.opts['outerIndent']
                else:
                    target = base + self.opts['argumentIndent']

                gap = ('' if i == 0 else '\n') + ' ' * target
                set_line_start(target)
            elif '\n' in gap:
                tail = gap.rsplit('\n', 1)[-1]
                target = len(tail.expandtabs(8))
                gap = '\n' + tail
                set_line_start(target)
            else:
                current_col += len(gap)

            rendered_positions[i] = current_col
            rendered_line_indents[i] = current_line_indent
            result += gap + t.string

            if '\n' in t.string:
                current_col = len(t.string.rsplit('\n', 1)[-1])
                current_line_indent = 0
            else:
                current_col += len(t.string)
        return result


def canonical(source):
    ts = tokens(source)
    result = ''
    unary = False
    for i, t in enumerate(ts):
        prev = ts[i - 1] if i else None
        current_unary = (t.string in ('+', '-', '~', '*', '**') and
                         (prev is None or (prev.type == tokenize.OP and prev.string not in (')', ']', '}'))
                          or prev.string in ('return', 'yield', 'else', 'in', 'and', 'or', 'not')))
        gap = ' ' if i else ''
        if prev:
            if t.string in (')', ']', '}', ',', ':', ';', '.') or prev.string in ('(', '[', '{', '.') or unary:
                gap = ''
            if t.string == '(' and (prev.type == tokenize.NAME and not keyword.iskeyword(prev.string)
                                     or prev.string in (')', ']')):
                gap = ''
            if t.string == '[' and (prev.type in (tokenize.NAME, tokenize.STRING) and not keyword.iskeyword(prev.string)
                                     or prev.string in (')', ']')):
                gap = ''
            if t.string == '.' and prev.type == tokenize.NUMBER:
                gap = ' '
        if t.type == tokenize.COMMENT:
            inline = prev is not None and prev.end[0] == t.start[0]
            gap = '  ' if inline else '\n'
        if prev and prev.type == tokenize.COMMENT:
            gap = '\n'
        result += gap + t.string
        unary = current_unary
    return result


ARITHMETIC = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
              ast.FloorDiv: '//', ast.Mod: '%', ast.Pow: '**', ast.MatMult: '@'}


def complex_arithmetic(node):
    if not isinstance(node, ast.BinOp) or type(node.op) not in ARITHMETIC:
        return False
    nodes = list(walk(node))
    return (sum(isinstance(n, ast.BinOp) and type(n.op) in ARITHMETIC for n in nodes) > 1
            and any(isinstance(n, (ast.Name, ast.Call, ast.Attribute, ast.Subscript)) for n in nodes))


def arithmetic_roots(root):
    """Maximal connected arithmetic trees; calculations inside calls are separate."""
    parents = {child: parent for parent in walk(root) for child in ast.iter_child_nodes(parent)}
    for node in walk(root):
        if not isinstance(node, ast.BinOp) or type(node.op) not in ARITHMETIC:
            continue
        parent = parents.get(node)
        if not isinstance(parent, ast.BinOp) or type(parent.op) not in ARITHMETIC:
            yield node


def expand_arithmetic(node, layout, opts):
    mode = opts['arithmeticLayout']
    if mode == 'compact':
        return False
    if mode == 'expanded':
        return complex_arithmetic(node)
    # AST-derived width ignores cosmetic grouping added by previous formatting.
    # unparse is used ONLY to measure: output still comes from original tokens.
    return len(ast.unparse(node)) > opts['maxInlineLength']


def boolean_operands(node):
    if isinstance(node, ast.BoolOp):
        return node.values
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr)):
        # Flatten the left spine for layout only; never reassociate the AST.
        if isinstance(node.left, ast.BinOp) and type(node.left.op) is type(node.op):
            return [*boolean_operands(node.left), node.right]
        return [node.left, node.right]
    return []


def _group_boolean_operands(source, root, opts):
    """Use matching token pairs and UTF-8-aware AST spans, never character guesses."""
    probe = Layout(source, opts, 0)
    spans = set()
    operands = []
    if opts['expandBooleanOperators']:
        for node in walk(root):
            operands.extend(boolean_operands(node))
    for node in arithmetic_roots(root):
        if expand_arithmetic(node, probe, opts):
            operands.append(node)
            if opts['arithmeticLayout'] == 'expanded':
                operands.extend(n for n in walk(node) if isinstance(n, ast.BinOp))
    for operand in operands:
        start, end = probe.start(operand), probe.end(operand)
        if (start > 0 and probe.ts[start - 1].string == '('
                and probe.pairs.get(start - 1) == end + 1):
            continue
        spans.add((probe.starts[start], probe.ends[end]))
    inserts = [(start, '(') for start, end in spans] + [(end, ')') for start, end in spans]
    for at, text in sorted(inserts, reverse=True):
        source = source[:at] + text + source[at:]
    return source


def original_expansion(source, opts):
    probe = Layout(source, opts, 0)
    root = ast.parse(source, type_comments=True)
    expanded = set()
    for node in walk(root):
        if not isinstance(node, (ast.Call, ast.List, ast.Tuple, ast.Set, ast.Dict)):
            continue
        close = probe.end(node)
        opening = probe.pairs.get(close)
        if opening is not None and opening < close and (isinstance(node, ast.Call) or opening == probe.start(node)):
            if probe.ts[opening].start[0] != probe.ts[close].start[0]:
                expanded.add(ast.dump(node))
    return expanded


def format_statement(source, opts, indent):
    expanded = original_expansion(source, opts)
    flat = canonical(source)
    root = ast.parse(flat, type_comments=True)
    flat = _group_boolean_operands(flat, root, opts)
    root = ast.parse(flat, type_comments=True)
    # Plan first, then add only the grouping needed for legal continuation.
    # Every reparse invalidates AST positions; no node survives a source edit.
    layout = Layout(flat, opts, indent, expanded)
    layout.plan(root)
    stmt = root.body[0]
    value = getattr(stmt, 'value', None)
    if isinstance(value, ast.expr):
        needs_wrapper = any(layout.chain_dot(n) is not None and layout.depth[layout.chain_dot(n)] == 0
                            for n in walk(value))
        needs_wrapper = needs_wrapper or bool(opts['expandBooleanOperators'] and boolean_operands(value))
        start, end = layout.start(value), layout.end(value)
        if needs_wrapper and layout.depth[start] == 0:
            a, b = layout.starts[start], layout.ends[end]
            flat = flat[:a] + '(' + flat[a:b] + ')' + flat[b:]
            root = ast.parse(flat, type_comments=True)
            layout = Layout(flat, opts, indent, expanded)
            layout.plan(root)
    # Layout is a monotone structural plan: child expansion propagates to
    # containing calls/tuples before rendering, rather than changing on pass two.
    for _ in range(len(layout.ts) + 1):
        previous = dict(layout.breaks)
        layout.plan(root)
        layout.plan_chain_alignment(root)
        layout.plan_arithmetic(root)
        layout.plan_comments()
        layout.plan_delimiter_alignment()
        layout.plan_comments()
        if layout.breaks == previous:
            break
    else:
        raise ValueError('Layout planning did not converge; edit refused.')
    rendered = layout.render()
    if signature(flat) != signature(rendered):
        raise ValueError('Statement AST changed; edit refused.')
    if lexical_signature(source) != lexical_signature(rendered):
        raise ValueError('Source tokens changed; edit refused.')
    return rendered


def format_source(source, options=None):
    source = sanitize_unicode_whitespace(source)
    opts = dict(DEFAULTS)
    opts.update({k: v for k, v in (options or {}).items() if k in DEFAULTS})
    for key in ('outerIndent', 'chainIndent', 'argumentIndent', 'maxInlineLength'):
        if type(opts[key]) is not int or not 0 <= opts[key] <= 1000:
            raise ValueError('Invalid formatting option: ' + key)
    if opts['arithmeticLayout'] not in ('auto', 'compact', 'expanded'):
        raise ValueError('Invalid formatting option: arithmeticLayout')
    parsed, prefix = tree(source)
    lines = (prefix + source).splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    def position(line, byte):
        return starts[line - 1] + len(lines[line - 1].encode('utf-8')[:byte].decode('utf-8')) - len(prefix)

    edits = []
    supported = (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr, ast.Return, ast.Raise)
    for node in ast.walk(parsed):
        if not isinstance(node, supported) or node.lineno <= bool(prefix):
            continue
        a, b = position(node.lineno, node.col_offset), position(node.end_lineno, node.end_col_offset)
        before = lines[node.lineno - 1][:len(lines[node.lineno - 1].encode('utf-8')[:node.col_offset].decode('utf-8'))]
        after = lines[node.end_lineno - 1][len(lines[node.end_lineno - 1].encode('utf-8')[:node.end_col_offset].decode('utf-8')):]
        # Keep inline suites and semicolon statements intact. An external
        # trailing comment is part of the formatting fragment so it remains
        # attached to the closing line of this same statement.
        if before.strip() or '\t' in before:
            continue
        if after.lstrip().startswith('#'):
            b += len(after.rstrip('\r\n'))
        elif after.strip():
            continue
        fragment = source[a:b]
        formatted = format_statement(fragment, opts, len(before))
        edits.append((a, b, formatted))
    result = source
    for a, b, replacement in sorted(edits, reverse=True):
        result = result[:a] + replacement + result[b:]
    if signature(source) != signature(result) or lexical_signature(source) != lexical_signature(result):
        raise ValueError('AST or token validation failed; original code preserved.')
    if '\r\n' in source and '\n' not in source.replace('\r\n', ''):
        result = result.replace('\r\n', '\n').replace('\n', '\r\n')
    return result


def handle(request):
    if request.get('action') == 'validate':
        before = sanitize_unicode_whitespace(request['before'])
        after = sanitize_unicode_whitespace(request['after'])
        if signature(before) != signature(after):
            raise ValueError('Document AST changed; original code preserved.')
        if lexical_signature(before) != lexical_signature(after):
            raise ValueError('Document tokens changed; original code preserved.')
        return dict(ok=True)
    source = request['source']
    formatted = format_source(source, request.get('options'))
    if format_source(formatted, request.get('options')) != formatted:
        raise ValueError('Formatting did not stabilize; original code preserved.')
    if 'document' in request:
        start, end = request['start'], request['end']
        # Offsets from VS Code use UTF-16 code units, not Python code points.
        raw = request['document'].encode('utf-16-le')
        before = raw[:start * 2].decode('utf-16-le')
        selected = raw[start * 2:end * 2].decode('utf-16-le')
        after = raw[end * 2:].decode('utf-16-le')
        if selected != source:
            raise ValueError('Selection does not match document; edit refused.')
        handle(dict(action='validate', before=request['document'], after=before + formatted + after))
    return dict(ok=True, formatted=formatted)


def main():
    try:
        # Node sends UTF-8 JSON. Redirected Windows stdin otherwise uses the
        # system code page even when the source and VS Code document are UTF-8.
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
        if sys.version_info < (3, 9):
            raise ValueError('Python 3.9 or newer is required.')
        request = json.load(sys.stdin)
        print(json.dumps(handle(request), ensure_ascii=True))
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError, RecursionError) as exc:
        print(json.dumps(dict(ok=False, error=str(exc))))
    except Exception as exc:
        print(json.dumps(dict(ok=False, error='Formatter failed safely: ' + type(exc).__name__)))


if __name__ == '__main__':
    main()
