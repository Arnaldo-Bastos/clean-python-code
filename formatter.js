'use strict';

/*
 * Clean Python Code
 * -----------------
 * A lightweight, dependency-free pretty-printer focused on the user's
 * reference style: vertical method chains, leading commas, and recursive
 * expansion of complex calls/collections while preserving Python blocks.
 */

const DEFAULTS = {
  outerIndent: 8,
  chainIndent: 5,
  argumentIndent: 9,
  maxInlineLength: 88,
  leadingComma: true,
  expandBooleanOperators: true,
  standaloneBaseIndent: 4
};

const LEADING_EXPRESSION_PREFIXES = [
  'return',
  'yield from',
  'yield',
  'raise',
  'await'
];

function sp(n) { return ' '.repeat(Math.max(0, n)); }
function trimRight(s) { return s.replace(/[ \t]+$/g, ''); }
function indentOf(s) { return (s.match(/^[ \t]*/) || [''])[0]; }

function scanPairs(source) {
  const stack = [];
  const map = new Map();
  let quote = null;
  let triple = false;
  let comment = false;

  for (let i = 0; i < source.length; i++) {
    const c = source[i], n = source[i + 1], n2 = source[i + 2];
    if (comment) { if (c === '\n') comment = false; continue; }
    if (quote) {
      if (triple) {
        if (c === quote && n === quote && n2 === quote) { quote = null; triple = false; i += 2; }
      } else if (c === '\\') {
        i++;
      } else if (c === quote) {
        quote = null;
      }
      continue;
    }
    if (c === '#') { comment = true; continue; }
    if ((c === 'r' || c === 'R' || c === 'f' || c === 'F' || c === 'u' || c === 'U' || c === 'b' || c === 'B') && (n === '\'' || n === '"')) {
      quote = n;
      triple = source[i + 2] === n && source[i + 3] === n;
      if (triple) i += 3; else i += 1;
      continue;
    }
    if (c === '\'' || c === '"') {
      quote = c;
      triple = n === c && n2 === c;
      if (triple) i += 2;
      continue;
    }
    if ('([{'.includes(c)) stack.push({ c, i });
    else if (')]}'.includes(c)) {
      const open = stack.pop();
      if (open) { map.set(open.i, i); map.set(i, open.i); }
    }
  }
  return map;
}

function topLevelCommaParts(source) {
  const map = scanPairs(source);
  const result = [];
  let start = 0;
  let i = 0;
  let quote = null, triple = false, comment = false;
  while (i < source.length) {
    const c = source[i], n = source[i + 1], n2 = source[i + 2];
    if (comment) { if (c === '\n') comment = false; i++; continue; }
    if (quote) {
      if (triple) { if (c === quote && n === quote && n2 === quote) { quote = null; triple = false; i += 3; } else i++; }
      else if (c === '\\') i += 2;
      else if (c === quote) { quote = null; i++; }
      else i++;
      continue;
    }
    if (c === '#') { comment = true; i++; continue; }
    if ((c === 'r' || c === 'R' || c === 'f' || c === 'F' || c === 'u' || c === 'U' || c === 'b' || c === 'B') && (n === '\'' || n === '"')) {
      quote = n; triple = n2 === n; i += triple ? 3 : 2; continue;
    }
    if (c === '\'' || c === '"') { quote = c; triple = n === c && n2 === c; i += triple ? 3 : 1; continue; }
    if (map.has(i) && '([{'.includes(c)) { i = map.get(i) + 1; continue; }
    if (c === ',') { result.push(source.slice(start, i)); start = i + 1; }
    i++;
  }
  result.push(source.slice(start));
  return result;
}

function hasTopLevelBoolean(source) {
  const map = scanPairs(source);
  let i = 0;
  while (i < source.length) {
    const c = source[i];
    if (map.has(i) && '([{'.includes(c)) { i = map.get(i) + 1; continue; }
    if (c === '&' || c === '|') return true;
    const tail = source.slice(i);
    if (/^(and|or)\b/.test(tail)) return true;
    i++;
  }
  return false;
}

function findTopLevelAssignment(source) {
  const map = scanPairs(source);
  let i = 0;
  while (i < source.length) {
    const c = source[i];
    if (map.has(i) && '([{'.includes(c)) { i = map.get(i) + 1; continue; }
    if (c === '=' && source[i - 1] !== '=' && source[i + 1] !== '=' && source[i - 1] !== '!' && source[i - 1] !== '<' && source[i - 1] !== '>') return i;
    i++;
  }
  return -1;
}

function findCall(source) {
  const s = source.trim();
  const open = s.indexOf('(');
  if (open < 0 || !s.endsWith(')')) return null;
  const map = scanPairs(s);
  if (map.get(s.length - 1) !== open) return null;
  return { head: s.slice(0, open).trim(), content: s.slice(open + 1, -1) };
}

const INLINE_SUFFIX_METHODS = new Set([
  'alias',
  'cast',
  'otherwise',
  'over',
  'asc',
  'desc'
]);

const CHAIN_PROPERTY_BREAKS = new Set([
  'builder',
  'read',
  'write'
]);

function splitChain(source) {
  const s = source.trim();
  const map = scanPairs(s);
  const pieces = [];
  let start = 0;
  let i = 0;
  let seenOperation = false;

  while (i < s.length) {
    if (map.has(i) && '([{'.includes(s[i])) {
      i = map.get(i) + 1;
      continue;
    }

    if (s[i] === '.' && /[A-Za-z_]/.test(s[i + 1] || '')) {
      let j = i + 1;
      while (j < s.length && /[A-Za-z0-9_]/.test(s[j])) j++;
      const member = s.slice(i + 1, j);

      if (INLINE_SUFFIX_METHODS.has(member) && s[j] === '(') {
        const close = map.get(j);
        if (close == null) return [s];
        // Terminal modifiers belong to the expression immediately before them.
        // If no chain split has happened yet, simply keep the suffix attached
        // to the base expression (e.g. F.when(...).otherwise(...)).
        if (pieces.length) {
          pieces[pieces.length - 1] += s.slice(i, close + 1);
          i = close + 1;
          start = close + 1;
          continue;
        }
        i = close + 1;
        continue;
      }

      if (s[j] === '(') {
        const close = map.get(j);
        if (close == null) return [s];

        let prev = i - 1;
        while (prev >= 0 && /\s/.test(s[prev])) prev--;
        const prefix = s.slice(start, i).trim();
        const previousSegment = prefix.split('.').pop().trim();

        // A method call after an already-computed expression is a new chain step.
        // The first call on a direct dataframe/expression remains on the same line.
        // Fluent builder/read/write properties are treated as the first visible
        // operation so calls after them start on their own aligned lines.
        const shouldSplit =
          (seenOperation && prefix.length > 0) ||
          (CHAIN_PROPERTY_BREAKS.has(previousSegment));

        if (shouldSplit) {
          if (prefix) pieces.push(prefix);
          pieces.push(s.slice(i, close + 1).trim());
          start = close + 1;
          seenOperation = true;
          i = close + 1;
          continue;
        }

        // Otherwise this is the first actual operation on the base expression.
        seenOperation = true;
      }
    }
    i++;
  }

  if (!pieces.length) return [s];
  if (start < s.length) {
    const rest = s.slice(start).trim();
    if (rest) pieces.push(rest);
  }

  // If there was never a split, this is just a single expression.
  return pieces.length ? pieces : [s];
}

function isChain(source) {
  const parts = splitChain(source);
  return parts.length > 1 && parts.slice(1).every(x => /^\.[A-Za-z_]\w*\s*\(/.test(x));
}

function outerCollection(source) {
  const s = source.trim();
  if (s.length < 2) return null;
  const open = s[0], close = s[s.length - 1];
  if (!(open === '[' && close === ']') && !(open === '{' && close === '}') && !(open === '(' && close === ')')) return null;
  const map = scanPairs(s);
  if (map.get(s.length - 1) !== 0) return null;
  return { open, close, content: s.slice(1, -1) };
}

function normalizeMemberAccess(value) {
  // Remove whitespace around member-access dots while preserving strings.
  // This keeps expressions such as df[col].value_counts().index intact even
  // when surrounding formatting has introduced continuation whitespace.
  let out = '';
  let quote = null;
  let triple = false;

  for (let i = 0; i < value.length; i++) {
    const c = value[i], n = value[i + 1], n2 = value[i + 2];
    if (quote) {
      out += c;
      if (triple) {
        if (c === quote && n === quote && n2 === quote) {
          out += n + n2;
          i += 2;
          quote = null;
          triple = false;
        }
      } else if (c === '\\') {
        if (i + 1 < value.length) out += value[++i];
      } else if (c === quote) {
        quote = null;
      }
      continue;
    }

    if (c === 'r' || c === 'R' || c === 'f' || c === 'F' || c === 'u' || c === 'U' || c === 'b' || c === 'B') {
      if (n === '\'' || n === '"') {
        quote = n;
        triple = value[i + 2] === n && value[i + 3] === n;
        out += c + n;
        i += 1;
        if (triple) { out += n + n; i += 2; }
        continue;
      }
    }

    if (c === '\'' || c === '"') {
      quote = c;
      triple = n === c && n2 === c;
      out += c;
      if (triple) { out += n + n; i += 2; }
      continue;
    }

    if (c === '.') {
      // Remove spaces immediately before/after a member-access dot.
      out = out.replace(/[ \t]+$/g, '');
      out += '.';
      while (i + 1 < value.length && /[ \t]/.test(value[i + 1])) i++;
      continue;
    }

    out += c;
  }
  return out;
}

function normalizeKeywordEquals(value) {
  const s = normalizeMemberAccess(value.trim());
  const map = scanPairs(s);
  for (let i = 0; i < s.length; i++) {
    if (map.has(i) && '([{'.includes(s[i])) { i = map.get(i); continue; }
    if (s[i] === '=' && s[i - 1] !== '=' && s[i + 1] !== '=' && s[i - 1] !== '!' && s[i - 1] !== '<' && s[i - 1] !== '>') {
      return normalizeMemberAccess(s.slice(0, i).trim() + ' = ' + s.slice(i + 1).trim());
    }
  }
  return normalizeMemberAccess(s);
}

function simpleInlineCollection(s) {
  const c = outerCollection(s);
  if (!c) return false;
  const items = topLevelCommaParts(c.content).map(x => x.trim()).filter(Boolean);
  if (!items.length) return true;
  if (c.open === '(') {
    // Tuples of scalar/simple expressions (including the long date tuples in
    // the reference examples) stay on one line.
    return items.every(x => !outerCollection(x) && !isChain(x) && !findCall(x) && !/[&|]/.test(x));
  }
  return s.length <= 42 && items.every(x => !outerCollection(x) && !isChain(x) && !findCall(x) && x.length <= 30);
}

function formatBoolean(value, indent, opts, ctx = {}) {
  if (!opts.expandBooleanOperators || !hasTopLevelBoolean(value)) return null;
  const map = scanPairs(value);
  const operands = [];
  const operators = [];
  let start = 0;
  let i = 0;
  while (i < value.length) {
    if (map.has(i) && '([{'.includes(value[i])) { i = map.get(i) + 1; continue; }
    let op = null;
    if (value[i] === '&' || value[i] === '|') op = value[i];
    else {
      const m = value.slice(i).match(/^(and|or)\b/);
      if (m) op = m[1];
    }
    if (op) {
      operands.push(value.slice(start, i).trim());
      operators.push(op);
      i += op.length;
      start = i;
      continue;
    }
    i++;
  }
  operands.push(value.slice(start).trim());
  if (operands.length < 2) return null;

  // Preserve the user's preferred behavior for short boolean conditions: each
  // operand is grouped, but the operator remains on the same logical line.
  const renderedOperands = operands.map(operand => '(' + operand.replace(/^\((.*)\)$/, '$1').trim() + ')');
  const multiline = Boolean(ctx.inCallArgument || ctx.forceMultiline) &&
    (renderedOperands.length > 1 || value.length > opts.maxInlineLength);

  if (!multiline) {
    let inline = renderedOperands[0];
    for (let j = 0; j < operators.length; j++) inline += ' ' + operators[j] + ' ' + renderedOperands[j + 1];
    return inline.trim();
  }

  const lines = [renderedOperands[0]];
  for (let j = 0; j < operators.length; j++) {
    lines.push(sp(indent) + operators[j] + ' ' + renderedOperands[j + 1]);
  }
  return lines.join('\n').trim();
}

function shouldExpandCall(head, args, content, opts, force = false) {
  if (force) return true;
  if (args.length > 1) return true;
  if (!content.trim()) return false;
  if (content.length > opts.maxInlineLength) return true;
  if (hasTopLevelBoolean(content)) return true;
  const arg = args[0] || '';
  const nestedCollection = outerCollection(arg.trim());
  const nestedCall = findCall(arg.trim());
  if (nestedCollection && !simpleInlineCollection(arg.trim())) return true;
  if (nestedCall && (isChain(arg.trim()) || topLevelCommaParts(nestedCall.content).length > 1 || nestedCall.content.length > 55)) return true;
  if (isChain(arg.trim())) return true;
  return false;
}

function formatCollection(s, baseIndent, opts, ctx = {}, depth = 0) {
  const c = outerCollection(s);
  if (!c) return s.trim();
  const items = topLevelCommaParts(c.content).map(x => x.trim()).filter(Boolean);
  if (!items.length) {
    if (ctx.forceCollectionExpand) return [c.open, sp(baseIndent) + c.close].join('\n');
    return c.open + c.close;
  }

  const force = Boolean(ctx.forceCollectionExpand);
  const dictLike = c.open === '{' && items.some(x => findTopLevelColon(x) >= 0);
  const shouldExpand = force || dictLike || (items.length > 1 && !simpleInlineCollection(s)) || items.some(x => isChain(x) || hasComplexNested(x));
  if (!shouldExpand) return normalizeCollectionInline(s);

  // The reference style uses a small visual offset after every opening
  // delimiter. Lists/dicts use +3 spaces for their items; a top-level list of
  // tuples uses +2 to match the examples exactly.
  let itemIndent = baseIndent + 2;
  if (ctx.nestedCallCollection) {
    itemIndent = c.open === '(' ? baseIndent + 4 : baseIndent + 3;
  }

  const lines = [c.open];
  items.forEach((item, idx) => {
    let normalizedItem = item;
    if (dictLike) {
      const colon = findTopLevelColon(item);
      if (colon >= 0) {
        const key = item.slice(0, colon).trim();
        const value = item.slice(colon + 1).trim();
        normalizedItem = key + ' : ' + formatExpression(value, itemIndent, opts, { inCollection: true }, depth + 1).trim();
      }
    }

    let rendered = dictLike
      ? normalizedItem
      : formatExpression(
        item,
        itemIndent,
        opts,
        {
          inCollection: true,
          forceCollectionExpand: items.length === 1 && Boolean(outerCollection(item))
        },
        depth + 1
      ).trim();
    const sub = rendered.split('\n');
    let first = sub[0];
    if (idx > 0 && opts.leadingComma) {
      first = ',' + first;
      // In dictionaries the key text is vertically aligned; the leading comma
      // sits one column before the key text.
      const tupleList = c.open === '[' && items.every(x => /^\(.*\)$/.test(x.trim()));
      lines.push(sp((dictLike || tupleList) ? itemIndent - 1 : itemIndent) + first);
    } else {
      lines.push(sp(itemIndent) + first);
    }
    for (const extra of sub.slice(1)) lines.push(extra);
  });

  // Every closing delimiter is vertically aligned with its matching opening
  // delimiter. This is one of the defining rules of the reference style.
  lines.push(sp(baseIndent) + c.close);
  return lines.join('\n');
}

function findTopLevelColon(source) {
  const map = scanPairs(source);
  for (let i = 0; i < source.length; i++) {
    if (map.has(i) && '([{'.includes(source[i])) { i = map.get(i); continue; }
    if (source[i] === ':') return i;
  }
  return -1;
}

function normalizeCollectionInline(s) {
  const c = outerCollection(s);
  if (!c) return s.trim();
  const items = topLevelCommaParts(c.content).map(x => x.trim()).filter(Boolean);
  if (c.open === '{') return '{' + items.join(', ') + '}';
  if (c.open === '[') {
    const stringOnly = items.every(x => /^(['"]).*\1$/.test(x));
    return '[' + items.join(stringOnly ? ', ' : ',') + ']';
  }
  return '(' + items.join(', ') + (items.length === 1 && /,$/.test(c.content) ? ',' : '') + ')';
}

function hasComplexNested(source) {
  const c = outerCollection(source);
  if (c) return !simpleInlineCollection(source);
  if (isChain(source)) return true;
  const call = findCall(source);
  if (call) return call.content.length > 50 || topLevelCommaParts(call.content).length > 1 || hasTopLevelBoolean(call.content);
  return false;
}

function formatCall(callSource, baseIndent, opts, ctx = {}, depth = 0) {
  const call = findCall(callSource);
  if (!call) return callSource.trim();
  const args = topLevelCommaParts(call.content).map(x => x.trim()).filter(Boolean);
  let expand = shouldExpandCall(call.head, args, call.content, opts, ctx.forceCallExpand);

  if (ctx.inCollection && !ctx.forceCallExpand) {
    const complexNested = args.some(a => {
      const c = outerCollection(a.trim());
      return c && !simpleInlineCollection(a.trim());
    });
    expand = call.content.length > opts.maxInlineLength || hasTopLevelBoolean(call.content) || complexNested;
  }

  if (!expand) {
    return normalizeMemberAccess(
      ctx.inCollection
        ? call.head + '(' + args.map(normalizeKeywordEquals).join(', ') + ')'
        : normalizeInlineCall(call.head, args)
    );
  }

  // `baseIndent` is the absolute column where the call head starts.
  // Therefore the opening parenthesis is at baseIndent + head.length and the
  // closing parenthesis must use exactly that same column.
  const openColumn = baseIndent + call.head.length;
  const argIndent = ctx.standalone
    ? openColumn + (ctx.standaloneArgOffset || 2)
    : openColumn + 3;

  const lines = [call.head + '('];

  args.forEach((arg, idx) => {
    const nested = outerCollection(arg.trim());
    const multilineBoolean = hasTopLevelBoolean(normalizeKeywordEquals(arg));

    // For nested collections, the examples use a smaller offset for list/dict
    // arguments and a wider offset for nested parenthesized expressions.
    let renderedBase = argIndent;
    if (nested) {
      renderedBase = nested.open === '(' ? openColumn + 3 : openColumn + 1;
    }

    let rendered = formatExpression(
      normalizeKeywordEquals(arg),
      renderedBase,
      opts,
      {
        inCallArgument: true,
        nestedCallCollection: Boolean(nested)
      },
      depth + 1
    ).trim();

    const sub = rendered.split('\n');
    let first = sub[0];
    if (idx > 0 && opts.leadingComma) first = ',' + first;
    lines.push(sp(renderedBase) + first);
    if (multilineBoolean && sub.length > 1) {
      for (const extra of sub.slice(1)) {
        lines.push(/^\s/.test(extra) ? extra : sp(renderedBase) + extra.trim());
      }
      return;
    }
    for (const extra of sub.slice(1)) lines.push(extra);
  });

  lines.push(sp(openColumn) + ')');
  return lines.join('\n');
}

function normalizeInlineCall(head, args) {
  if (!args.length) return head + '()';
  return head + '(' + args.join(', ') + ')';
}

function firstMemberDotOffset(source) {
  const s = source.trim();
  const map = scanPairs(s);
  for (let i = 0; i < s.length; i++) {
    if (map.has(i) && '([{'.includes(s[i])) { i = map.get(i); continue; }
    if (s[i] === '.' && /[A-Za-z_]/.test(s[i + 1] || '')) return i;
  }
  return 0;
}

function formatChain(source, baseIndent, opts, ctx = {}, depth = 0) {
  const parts = splitChain(source);
  if (parts.length < 2) return source.trim();
  const lines = [];
  const first = formatExpression(parts[0], baseIndent, opts, { inChainBase: true }, depth + 1).trim();
  const firstLines = first.split('\n');
  lines.push(firstLines[0]);
  for (const extra of firstLines.slice(1)) lines.push(extra);

  // Align every subsequent chain dot with the dot that introduces the first
  // method on the same line as the base object. This naturally gives:
  //   df.groupBy(...)
  //         .agg(...)
  //         .show(...)
  // while still giving:
  //   spark.table(...)
  //        .filter(...)
  //        .select(...)
  const methodIndent = baseIndent + firstMemberDotOffset(parts[0]);

  for (const p of parts.slice(1)) {
    const rendered = formatCall(p, methodIndent, opts, { inChainMethod: true }, depth + 1);
    const sub = rendered.split('\n');
    lines.push(sp(methodIndent) + sub[0].trimStart());
    lines.push(...sub.slice(1));
  }
  return lines.join('\n');
}

function formatExpression(expr, baseIndent, opts, ctx = {}, depth = 0) {
  const s = expr.trim();
  if (!s) return s;
  if (depth > 20) return s;

  const c = outerCollection(s);
  if (c) return formatCollection(s, baseIndent, opts, ctx, depth);

  if (isChain(s)) return formatChain(s, baseIndent, opts, ctx, depth);

  const bool = formatBoolean(s, baseIndent, opts, ctx);
  if (bool && !ctx.inCollection) return bool;

  const call = findCall(s);
  if (call) {
    return formatCall(s, baseIndent, opts, ctx, depth);
  }
  return normalizeKeywordEquals(s);
}

function splitLeadingExpressionPrefix(source) {
  const s = source.trim();
  for (const prefix of LEADING_EXPRESSION_PREFIXES) {
    if (s === prefix) {
      return { prefix, expression: '' };
    }
    if (s.startsWith(prefix + ' ')) {
      return {
        prefix,
        expression: s.slice(prefix.length).trim()
      };
    }
  }
  return null;
}

function formatPrefixedExpression(line, opts) {
  const indent = indentOf(line);
  const body = line.trim();
  const prefixed = splitLeadingExpressionPrefix(body);
  if (!prefixed || !prefixed.expression) return null;

  const prefixText = prefixed.prefix;
  const rhs = prefixed.expression;

  if (isChain(rhs)) {
    const parts = splitChain(rhs);
    const lines = [indent + prefixText + ' ('];
    const base = indent.length + opts.outerIndent;
    const first = formatExpression(parts[0], base, opts, {}, 0).split('\n');
    lines.push(...first.map((x, i) => i === 0 ? sp(base) + x.trimStart() : x));
    const methodIndent = base + firstMemberDotOffset(parts[0]);
    for (const p of parts.slice(1)) {
      const rendered = formatCall(p, methodIndent, opts, { inChainMethod: true }, 0).split('\n');
      lines.push(sp(methodIndent) + rendered[0].trimStart());
      lines.push(...rendered.slice(1));
    }
    lines.push(sp(Math.max(indent.length + prefixText.length + 1, base - 3)) + ')');
    return trimRight(lines.join('\n'));
  }

  const coll = outerCollection(rhs);
  if (coll && !simpleInlineCollection(rhs)) {
    const collectionColumn = indent.length + prefixText.length + 1;
    const rendered = formatCollection(rhs, collectionColumn, opts, { forceCollectionExpand: true }, 0).split('\n');
    rendered[0] = indent + prefixText + ' ' + rendered[0];
    return trimRight(rendered.join('\n'));
  }

  const call = findCall(rhs);
  const args = call ? topLevelCommaParts(call.content).map(x => x.trim()).filter(Boolean) : [];
  if (call && shouldExpandCall(call.head, args, call.content, opts, false)) {
    const rhsColumn = indent.length + prefixText.length + 1;
    const rendered = formatCall(rhs, rhsColumn, opts, {}, 0).split('\n');
    rendered[0] = indent + prefixText + ' ' + rendered[0];
    return trimRight(rendered.join('\n'));
  }

  return null;
}

function formatAssignment(line, opts) {
  const indent = indentOf(line);
  const body = line.trim();
  const eq = findTopLevelAssignment(body);
  if (eq < 0) return null;
  const lhs = body.slice(0, eq).trim() + ' =';
  const rhs = body.slice(eq + 1).trim();

  if (isChain(rhs)) {
    const parts = splitChain(rhs);
    const lines = [indent + lhs + ' ('];
    const base = indent.length + opts.outerIndent;
    const first = formatExpression(parts[0], base, opts, {}, 0).split('\n');
    lines.push(...first.map((x, i) => i === 0 ? sp(base) + x.trimStart() : x));
    const methodIndent = base + firstMemberDotOffset(parts[0]);
    for (const p of parts.slice(1)) {
      const rendered = formatCall(p, methodIndent, opts, { inChainMethod: true }, 0).split('\n');
      lines.push(sp(methodIndent) + rendered[0].trimStart());
      lines.push(...rendered.slice(1));
    }
    lines.push(sp(Math.max(indent.length + 1, base - 3)) + ')');
    return trimRight(lines.join('\n'));
  }

  const coll = outerCollection(rhs);
  if (coll && !simpleInlineCollection(rhs)) {
    const collectionColumn = indent.length + lhs.length + 1;
    const rendered = formatCollection(rhs, collectionColumn, opts, { forceCollectionExpand: true }, 0).split('\n');
    rendered[0] = indent + lhs + ' ' + rendered[0];
    return trimRight(rendered.join('\n'));
  }

  const call = findCall(rhs);
  if (call && shouldExpandCall(call.head, topLevelCommaParts(call.content).map(x => x.trim()).filter(Boolean), call.content, opts, false)) {
    // The RHS call remains on the assignment line. Compute its absolute column
    // from the actual text before it so nested delimiters align to reality.
    const rhsColumn = indent.length + lhs.length + 1;
    const rendered = formatCall(rhs, rhsColumn, opts, {}, 0).split('\n');
    rendered[0] = indent + lhs + ' ' + rendered[0];
    return trimRight(rendered.join('\n'));
  }
  return null;
}

function formatStandaloneExpression(line, opts) {
  const indent = indentOf(line);
  const body = line.trim();
  if (!isChain(body) && !findCall(body)) return null;

  if (isChain(body)) {
    const parts = splitChain(body);
    const lines = ['('];
    const base = indent.length + opts.standaloneBaseIndent;
    const first = formatExpression(parts[0], base, opts, {}, 0).split('\n');
    lines.push(...first.map(x => sp(base) + x.trimStart()));
    const methodIndent = base + firstMemberDotOffset(parts[0]);
    for (const p of parts.slice(1)) {
      const r = formatCall(p, methodIndent, opts, {}, 0).split('\n');
      lines.push(sp(methodIndent) + r[0].trimStart());
      lines.push(...r.slice(1));
    }
    lines.push(sp(indent.length) + ')');
    return trimRight(lines.join('\n'));
  }

  const call = findCall(body);
  const args = topLevelCommaParts(call.content).map(x => x.trim()).filter(Boolean);
  const outerArgumentChain = args.length === 1 && /\.[A-Za-z_]\w*\s*\(/.test(args[0] || '');
  if (shouldExpandCall(call.head, args, call.content, opts, false) || outerArgumentChain) {
    const standaloneArgOffset = indent.length > 0 ? 3 : 2;
    const rendered = formatCall(body, indent.length, opts, { standalone: true, standaloneArgOffset, forceCallExpand: true }, 0);
    return trimRight(indent + rendered);
  }
  return null;
}

const STRUCTURAL_RE = /^(async\s+def|def|class|for|while|if|elif|else|try|except|finally|with|match|case)\b/;

function logicalStatements(text) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let current = [];
  let depth = 0;
  let quote = null, triple = false, comment = false;

  function updateDepth(line) {
    for (let i = 0; i < line.length; i++) {
      const c = line[i], n = line[i + 1], n2 = line[i + 2];
      if (comment) { if (c === '\n') comment = false; continue; }
      if (quote) {
        if (triple) { if (c === quote && n === quote && n2 === quote) { quote = null; triple = false; i += 2; } }
        else if (c === '\\') i++;
        else if (c === quote) quote = null;
        continue;
      }
      if (c === '#') { comment = true; continue; }
      if (c === '\'' || c === '"') { quote = c; triple = n === c && n2 === c; if (triple) i += 2; continue; }
      if ('([{'.includes(c)) depth++;
      else if (')]}'.includes(c)) depth = Math.max(0, depth - 1);
    }
  }

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    const trimmed = line.trim();
    if (!current.length && !trimmed) { out.push({ type: 'blank', lines: [''] }); continue; }
    if (!current.length && trimmed.startsWith('#')) { out.push({ type: 'comment', lines: [line] }); continue; }
    current.push(line);
    updateDepth(line);
    const structural = depth === 0 && STRUCTURAL_RE.test(trimmed) && trimmed.endsWith(':');
    const nextTrimmed = li + 1 < lines.length ? lines[li + 1].trim() : '';
    const nextContinuesWithComma = depth === 0 && /^,/.test(nextTrimmed);
    const continued = depth > 0 || /\\\s*$/.test(line) || nextContinuesWithComma;
    if (structural || (!continued && depth === 0)) {
      out.push({ type: 'statement', lines: current });
      current = [];
    }
  }
  if (current.length) out.push({ type: 'statement', lines: current });
  return out;
}

function formatStatement(lines, opts) {
  if (lines.length === 1) {
    const line = lines[0];
    if (!line.trim()) return '';
    const assignment = formatAssignment(line, opts);
    if (assignment) return assignment;
    const prefixed = formatPrefixedExpression(line, opts);
    if (prefixed) return prefixed;
    const standalone = formatStandaloneExpression(line, opts);
    if (standalone) return standalone;
    return trimRight(line);
  }

  // Wrapped expressions (collections/calls/assignments) are re-parsed from a
  // whitespace-collapsed logical statement so an already partially formatted
  // selection is normalized rather than merely preserved line-by-line.
  if (!(STRUCTURAL_RE.test(lines[0].trim()) && lines[0].trim().endsWith(':'))) {
    const leading = indentOf(lines[0]);
    const joinedBody = lines.map(x => x.trim()).filter(Boolean).join(' ');
    let candidate = leading + joinedBody;
    const eq = findTopLevelAssignment(joinedBody);
    if (eq >= 0) {
      const lhs = joinedBody.slice(0, eq).trim() + ' =';
      const rhs = joinedBody.slice(eq + 1).trim();
      const wrapped = outerCollection(rhs);
      if (wrapped && wrapped.open === '(') {
        candidate = leading + lhs + ' ' + wrapped.content.trim();
      }
    }
    const a = formatAssignment(candidate, opts);
    if (a) return a;
    const p = formatPrefixedExpression(candidate, opts);
    if (p) return p;
    const e = formatStandaloneExpression(candidate, opts);
    if (e) return e;
  }

  // Keep Python block structure intact. For each physical body line, format the
  // statement using its existing indentation. This is essential for for/def/if/
  // try blocks and makes notebook selections safe to format.
  const result = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) { result.push(''); continue; }
    if (i === 0 && STRUCTURAL_RE.test(line.trim()) && line.trim().endsWith(':')) {
      result.push(trimRight(line));
      continue;
    }
    const a = formatAssignment(line, opts);
    if (a) result.push(a);
    else {
      const p = formatPrefixedExpression(line, opts);
      if (p) {
        result.push(p);
        continue;
      }
      const e = formatStandaloneExpression(line, opts);
      result.push(e || trimRight(line));
    }
  }
  return result.join('\n');
}

function notebookSourceToText(source) {
  if (typeof source === 'string') return source;
  if (Array.isArray(source)) return source.join('');
  return null;
}

function textToNotebookSource(text, preferArray) {
  if (!preferArray) return text;
  return text.match(/[^\n]*\n|[^\n]+/g) || [''];
}

function formatNotebookContent(text, options = {}) {
  let notebook;
  try {
    notebook = JSON.parse(text);
  } catch {
    throw new Error('Clean Python Code could not parse the selected .ipynb content as notebook JSON.');
  }

  if (!notebook || !Array.isArray(notebook.cells)) return text;
  const opts = { ...DEFAULTS, ...options };
  let changed = false;

  const formatted = {
    ...notebook,
    cells: notebook.cells.map(cell => {
      if (!cell || cell.cell_type !== 'code') return cell;
      const originalSource = notebookSourceToText(cell.source);
      if (originalSource == null) return cell;

      const nextSource = formatSelection(originalSource, opts);
      if (nextSource === originalSource) return cell;

      changed = true;
      return {
        ...cell,
        source: textToNotebookSource(nextSource, Array.isArray(cell.source))
      };
    })
  };

  return changed ? JSON.stringify(formatted, null, 2) + '\n' : text;
}

function formatAlreadyWrappedSelection(text, opts) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const nonBlank = lines.filter(x => x.trim() !== '');
  if (nonBlank.length < 2) return null;
  const first = nonBlank[0].trim();
  const last = nonBlank[nonBlank.length - 1].trim();

  // Assignment wrapper: `df = (` ... `)`
  const m = first.match(/^(.+?)\s*=\s*\($/);
  if (m && last === ')') {
    const leading = indentOf(nonBlank[0]);
    const inner = nonBlank.slice(1, -1).map(x => x.trim()).filter(Boolean).join(' ');
    const candidate = leading + m[1].trim() + ' = ' + inner;
    const formatted = formatAssignment(candidate, opts);
    if (formatted) return formatted;
  }

  // Standalone wrapper: `(` ... chain ... `)`
  if (first === '(' && last === ')') {
    const inner = nonBlank.slice(1, -1).map(x => x.trim()).filter(Boolean).join(' ');
    if (isChain(inner)) return formatStandaloneExpression(inner, opts);
  }
  return null;
}

function formatSelection(text, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const wrapped = formatAlreadyWrappedSelection(text, opts);
  if (wrapped !== null) return wrapped;
  const blocks = logicalStatements(text);
  const rendered = blocks.map(b => {
    if (b.type === 'blank' || b.type === 'comment') return b.lines.join('\n');
    return formatStatement(b.lines, opts);
  });
  return rendered.join('\n').replace(/\n{3,}/g, '\n\n');
}

module.exports = {
  formatNotebookContent,
  formatSelection,
  splitChain,
  topLevelCommaParts,
  scanPairs,
  outerCollection
};
