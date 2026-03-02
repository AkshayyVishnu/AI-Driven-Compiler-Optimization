"""
Z3 SMT Verifier — Week 7 (optional)

Uses the Z3 theorem prover to check semantic equivalence of simple
arithmetic/logical C++ expressions.

Gracefully degrades if z3-solver is not installed.
Install with: pip install z3-solver
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Z3Result:
    status: str          # "PROVEN_EQUIVALENT" | "COUNTEREXAMPLE_FOUND" | "UNKNOWN" | "SKIPPED"
    counterexample: Optional[str] = None
    explanation: str = ""


class Z3Verifier:
    """
    Lightweight Z3-based equivalence checker.

    Checks simple arithmetic equivalence of single-expression functions.
    Returns SKIPPED gracefully if z3 is not installed or code is too complex.

    Usage
    -----
    verifier = Z3Verifier()
    result = verifier.verify(original_src, optimized_src)
    print(result.status)  # "PROVEN_EQUIVALENT", "COUNTEREXAMPLE_FOUND", "UNKNOWN", "SKIPPED"
    """

    def __init__(self):
        self._z3 = self._try_import_z3()

    def verify(self, original_src: str, optimized_src: str) -> Z3Result:
        """
        Attempt to formally verify equivalence.

        Extracts return expressions from simple functions and uses Z3 to
        prove they are always equal.
        """
        if self._z3 is None:
            return Z3Result(
                status="SKIPPED",
                explanation="z3-solver not installed. Run: pip install z3-solver",
            )

        orig_expr = self._extract_return_expr(original_src)
        opt_expr  = self._extract_return_expr(optimized_src)

        if orig_expr is None or opt_expr is None:
            return Z3Result(
                status="UNKNOWN",
                explanation="Could not extract simple return expression for Z3 verification.",
            )

        return self._check_equivalence(orig_expr, opt_expr)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _check_equivalence(self, expr1: str, expr2: str) -> Z3Result:
        z3 = self._z3
        try:
            # Declare generic integer variables
            vars_found = set(re.findall(r'\b([a-zA-Z_]\w*)\b', expr1 + " " + expr2))
            # Filter out C++ keywords / numbers
            cpp_kw = {'int', 'return', 'double', 'float', 'char', 'long', 'if',
                      'else', 'for', 'while', 'void', 'bool', 'true', 'false'}
            var_names = [v for v in vars_found if v not in cpp_kw]

            ctx   = {}
            solver = z3.Solver()
            for v in var_names:
                ctx[v] = z3.Int(v)

            # Safely evaluate both expressions in the Z3 context
            e1 = eval(expr1, {"__builtins__": {}}, ctx)  # noqa: S307
            e2 = eval(expr2, {"__builtins__": {}}, ctx)  # noqa: S307

            # Check: is there any assignment where they differ?
            solver.add(e1 != e2)
            result = solver.check()

            if result == z3.unsat:
                return Z3Result(
                    status="PROVEN_EQUIVALENT",
                    explanation=f"Z3 proved '{expr1}' ≡ '{expr2}' for all inputs.",
                )
            elif result == z3.sat:
                model = solver.model()
                ce    = str(model)
                return Z3Result(
                    status="COUNTEREXAMPLE_FOUND",
                    counterexample=ce,
                    explanation=f"Expressions differ: counterexample = {ce}",
                )
            else:
                return Z3Result(
                    status="UNKNOWN",
                    explanation="Z3 returned unknown (possible timeout or complexity limit).",
                )
        except Exception as exc:
            logger.warning(f"Z3 verification error: {exc}")
            return Z3Result(
                status="UNKNOWN",
                explanation=f"Z3 verification failed: {exc}",
            )

    def _extract_return_expr(self, src: str) -> Optional[str]:
        """
        Extract the expression from a simple `return <expr>;` statement.
        Only works for functions with a single return.
        """
        matches = re.findall(r'\breturn\s+([^;{]+)\s*;', src)
        if len(matches) == 1:
            return matches[0].strip()
        return None

    def _try_import_z3(self):
        try:
            import z3  # type: ignore
            logger.info("z3-solver available.")
            return z3
        except ImportError:
            logger.info("z3-solver not installed; Z3 verification will be skipped.")
            return None

    def is_available(self) -> bool:
        return self._z3 is not None
