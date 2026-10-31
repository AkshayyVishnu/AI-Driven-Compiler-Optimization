/**
 * Rule-based line-level fix patterns for C/C++ issues.
 * applyRuleFix(type, lineContent) → fixed line string | null
 */

const RULES = {
  buffer_overflow: {
    pattern: /\bstrcpy\s*\(/,
    fix: (line) => line.replace(
      /\bstrcpy\s*\(\s*(\w+)\s*,\s*([^)]+)\)/,
      (_, dst, src) => `strncpy(${dst}, ${src.trim()}, sizeof(${dst})-1)`
    ),
  },
  unsafe_gets: {
    pattern: /\bgets\s*\(/,
    fix: (line) => line.replace(
      /\bgets\s*\(\s*(\w+)\s*\)/,
      (_, buf) => `fgets(${buf}, sizeof(${buf}), stdin)`
    ),
  },
  format_string: {
    pattern: /\bprintf\s*\(\s*\w+\s*\)/,
    fix: (line) => line.replace(
      /\bprintf\s*\(\s*(\w+)\s*\)/,
      (_, v) => `printf("%s", ${v})`
    ),
  },
  unsafe_sprintf: {
    pattern: /\bsprintf\s*\(/,
    fix: (line) => line.replace(
      /\bsprintf\s*\(\s*(\w+)\s*,/,
      (_, buf) => `snprintf(${buf}, sizeof(${buf}),`
    ),
  },
  unsafe_strcat: {
    pattern: /\bstrcat\s*\(/,
    fix: (line) => line.replace(
      /\bstrcat\s*\(\s*(\w+)\s*,\s*([^)]+)\)/,
      (_, dst, src) => `strncat(${dst}, ${src.trim()}, sizeof(${dst})-strlen(${dst})-1)`
    ),
  },
  unsafe_scanf: {
    pattern: /\bscanf\s*\(\s*"%s"/,
    fix: (line) => line.replace(/\bscanf\s*\(\s*"%s"/, 'scanf("%127s"'),
  },
  uninitialized_variable: {
    pattern: /^\s*(int|char|float|double|long|short)\s+\w+\s*;/,
    fix: (line) => line.replace(
      /\b(int|char|float|double|long|short)\s+(\w+)\s*;/,
      (_, type, name) => `${type} ${name} = 0;`
    ),
  },
  missing_semicolon: {
    pattern: /[^;{}/\s]$/,
    fix: (line) => line.trimEnd() + ';',
  },
  off_by_one: {
    pattern: /for\s*\([^;]+;\s*\w+\s*<=\s*\w+\s*;/,
    fix: (line) => line.replace(
      /(\w+)\s*<=\s*(\w+)(\s*;)/,
      (_, v, n, semi) => `${v} < ${n}${semi}`
    ),
  },
  hardcoded_credential: {
    pattern: /\b(password|api_key|secret|token)\s*=\s*"[^"]+"/i,
    fix: (line) => line.replace(/(=\s*)"[^"]+"/, '$1getenv("SECRET_KEY") /* TODO: use env var */'),
  },
  memory_leak: {
    pattern: /\bmalloc\s*\(/,
    fix: (line) => line.trimEnd() + ' /* FIX: ensure free() is called */',
  },
}

// Normalize incoming finding types to rule keys
const TYPE_ALIAS = {
  buffer_overflow_strcpy:  'buffer_overflow',
  unsafe_strcpy:           'buffer_overflow',
  strcpy_overflow:         'buffer_overflow',
  format_string_bug:       'format_string',
  format_string_vuln:      'format_string',
  printf_format:           'format_string',
  gets_unsafe:             'unsafe_gets',
  unsafe_input:            'unsafe_gets',
  sprintf_overflow:        'unsafe_sprintf',
  strcat_overflow:         'unsafe_strcat',
  scanf_unbounded:         'unsafe_scanf',
  unsafe_scanf_s:          'unsafe_scanf',
  unbounded_scanf:         'unsafe_scanf',
  uninitialized:           'uninitialized_variable',
  uninitialized_var:       'uninitialized_variable',
  syntax_error:            'missing_semicolon',
  semicolon_missing:       'missing_semicolon',
  off_by_one_error:        'off_by_one',
  loop_off_by_one:         'off_by_one',
  hardcoded_secret:        'hardcoded_credential',
  hardcoded_password:      'hardcoded_credential',
  credentials_exposure:    'hardcoded_credential',
}

export function applyRuleFix(findingType, lineContent) {
  const normalized = (findingType ?? '').toLowerCase().replace(/[\s-]/g, '_')
  const ruleKey    = TYPE_ALIAS[normalized] ?? normalized
  const rule       = RULES[ruleKey]

  if (rule && rule.pattern.test(lineContent)) {
    return rule.fix(lineContent)
  }

  // Fallback: try every rule in order
  for (const r of Object.values(RULES)) {
    if (r.pattern.test(lineContent)) {
      return r.fix(lineContent)
    }
  }
  return null
}

export function isRuleFixable(findingType) {
  const normalized = (findingType ?? '').toLowerCase().replace(/[\s-]/g, '_')
  const ruleKey    = TYPE_ALIAS[normalized] ?? normalized
  return ruleKey in RULES
}
