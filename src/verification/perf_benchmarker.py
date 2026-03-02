"""
Performance Benchmarker — Week 7

Compiles original and optimized code with -O0, runs each 5 times,
and reports average execution time and speedup percentage.

Requires g++ on PATH. Falls back gracefully if unavailable.
"""

import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_RUNS = 5  # number of timing runs per binary


@dataclass
class PerfResult:
    available: bool
    original_ms: float = 0.0
    optimized_ms: float = 0.0
    speedup_pct: float = 0.0
    error: Optional[str] = None

    def summary(self) -> str:
        if not self.available or self.error:
            return f"Perf benchmark skipped: {self.error}"
        direction = "faster" if self.speedup_pct >= 0 else "slower"
        return (
            f"Original: {self.original_ms:.2f} ms | "
            f"Optimized: {self.optimized_ms:.2f} ms | "
            f"Speedup: {abs(self.speedup_pct):.1f}% {direction}"
        )


class PerfBenchmarker:
    """
    Measures and compares runtime of original vs optimized C++ code.

    Usage
    -----
    bench = PerfBenchmarker()
    result = bench.benchmark(original_src, optimized_src)
    print(result.summary())
    """

    def __init__(self, compiler: str = "g++", timeout: int = 15, runs: int = _RUNS):
        self.compiler = compiler
        self.timeout  = timeout
        self.runs     = runs
        self._available = self._check_compiler()

    def benchmark(self, original_src: str, optimized_src: str) -> PerfResult:
        if not self._available:
            return PerfResult(
                available=False,
                error="g++ not found; performance benchmarking skipped.",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cpp = os.path.join(tmpdir, "original.cpp")
            opt_cpp  = os.path.join(tmpdir, "optimized.cpp")
            orig_bin = os.path.join(tmpdir, "original.exe")
            opt_bin  = os.path.join(tmpdir, "optimized.exe")

            for src, path in [(original_src, orig_cpp), (optimized_src, opt_cpp)]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(src)

            if not self._compile(orig_cpp, orig_bin):
                return PerfResult(available=True, error="Original compilation failed.")
            if not self._compile(opt_cpp, opt_bin):
                return PerfResult(available=True, error="Optimized compilation failed.")

            orig_ms = self._median_runtime_ms(orig_bin)
            opt_ms  = self._median_runtime_ms(opt_bin)

            if orig_ms > 0:
                speedup = (orig_ms - opt_ms) / orig_ms * 100.0
            else:
                speedup = 0.0

            return PerfResult(
                available=True,
                original_ms=orig_ms,
                optimized_ms=opt_ms,
                speedup_pct=speedup,
            )

    # ── Internals ─────────────────────────────────────────────────────────────

    def _compile(self, src: str, out: str) -> bool:
        try:
            proc = subprocess.run(
                [self.compiler, src, "-o", out, "-O0", "-w"],
                capture_output=True, timeout=self.timeout
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _median_runtime_ms(self, binary: str) -> float:
        times = []
        for _ in range(self.runs):
            try:
                t0 = time.perf_counter()
                subprocess.run(
                    [binary],
                    capture_output=True,
                    timeout=self.timeout
                )
                elapsed = (time.perf_counter() - t0) * 1000
                times.append(elapsed)
            except Exception:
                pass
        if not times:
            return 0.0
        times.sort()
        mid = len(times) // 2
        return times[mid]

    def _check_compiler(self) -> bool:
        try:
            subprocess.run([self.compiler, "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False
