/**
 * Lightweight regex-based syntax + logic checker for C/C++ code.
 * Returns finding objects compatible with the securityFindings schema.
 */

function checkLine(line, i) {
  const trimmed  = line.trim()
  const lineNum  = i + 1
  const findings = []

  // Skip blank lines, preprocessor directives, comments
  if (!trimmed) return findings
  if (trimmed.startsWith('#') || trimmed.startsWith('//') ||
      trimmed.startsWith('/*') || trimmed.startsWith('*')) return findings

  // ── Missing semicolons ────────────────────────────────────────────────────
  // Lines that start like a statement/declaration but don't end with ; { } , : \
  const STMT_START = /^(int|char|float|double|long|short|unsigned|const|auto|return|delete|free\s*\(|printf\s*\(|scanf\s*\(|gets\s*\(|strcpy|strcat|sprintf|snprintf|[a-zA-Z_]\w*\s*[\[=(])/
  const VALID_END  = /[;{},:)\\]$/
  if (STMT_START.test(trimmed) && !VALID_END.test(trimmed)) {
    findings.push({
      line:        lineNum,
      type:        'missing_semicolon',
      description: 'Missing semicolon at end of statement',
      severity:    'medium',
      fixable:     true,
      category:    'syntax',
    })
  }

  // ── Uninitialized scalar variables ────────────────────────────────────────
  // Matches: int foo; char bar; (but NOT int foo = 0; or int foo, bar;)
  if (/^\s*(int|char|float|double|long|short)\s+[a-zA-Z_]\w*\s*;/.test(line)) {
    findings.push({
      line:        lineNum,
      type:        'uninitialized_variable',
      description: 'Variable declared but not initialized — may hold garbage value',
      severity:    'medium',
      fixable:     true,
      category:    'logic',
    })
  }

  // ── Off-by-one (i <= n in for loop) ──────────────────────────────────────
  if (/for\s*\([^;]+;\s*\w+\s*<=\s*\w+\s*;/.test(line)) {
    findings.push({
      line:        lineNum,
      type:        'off_by_one',
      description: 'Loop condition uses <= which likely causes off-by-one out-of-bounds access',
      severity:    'medium',
      fixable:     true,
      category:    'logic',
    })
  }

  // ── Division by literal zero ──────────────────────────────────────────────
  if (/\/\s*0\b/.test(line)) {
    findings.push({
      line:        lineNum,
      type:        'division_by_zero',
      description: 'Division by literal zero — undefined behavior',
      severity:    'high',
      fixable:     false,
      category:    'logic',
    })
  }

  // ── malloc without adjacent free (potential memory leak) ─────────────────
  if (/\bmalloc\s*\(/.test(line) && !/\bfree\b/.test(line)) {
    findings.push({
      line:        lineNum,
      type:        'memory_leak',
      description: 'malloc() called — ensure a matching free() is present to avoid memory leak',
      severity:    'low',
      fixable:     true,
      category:    'logic',
    })
  }

  return findings
}

export function runSyntaxCheck(code) {
  if (!code) return []
  const lines    = code.split('\n')
  const findings = []
  for (let i = 0; i < lines.length; i++) {
    findings.push(...checkLine(lines[i], i))
  }
  return findings
}
