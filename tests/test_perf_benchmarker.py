import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.verification.perf_benchmarker import PerfBenchmarker

pytestmark = pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not on PATH")

LOOP_BODY = "long s = 0; for (int i = 0; i < 2000000; i++) s += i; printf(\"%ld\\n\", s); return 0;"

NO_ARGS = f"#include <cstdio>\nint main() {{ {LOOP_BODY} }}\n"
ARGC_ARGV = f"#include <cstdio>\nint main(int argc, char** argv) {{ {LOOP_BODY} }}\n"
VOID_ARGS = f"#include <cstdio>\nint main(void) {{ {LOOP_BODY} }}\n"


@pytest.mark.parametrize("src", [NO_ARGS, ARGC_ARGV, VOID_ARGS], ids=["no_args", "argc_argv", "void"])
def test_benchmark_links_and_times(src):
    result = PerfBenchmarker(runs=3).benchmark(src, src)
    assert result.error is None
    assert result.original_ms > 0
    assert result.optimized_ms > 0


def test_short_program_has_nonzero_time():
    src = '#include <cstdio>\nint main() { printf("hi\\n"); return 0; }\n'
    result = PerfBenchmarker(runs=5).benchmark(src, src)
    assert result.error is None
    assert result.original_ms > 0


def test_user_macro_named_size_does_not_break_harness():
    src = (
        '#include <cstdio>\nusing namespace std;\n#define SIZE 5\n'
        'int main() { int a[SIZE]; for (int i = 0; i < SIZE; i++) a[i] = i; '
        'printf("%d\\n", a[4]); return 0; }\n'
    )
    result = PerfBenchmarker(runs=3).benchmark(src, src)
    assert result.error is None
    assert result.original_ms > 0
