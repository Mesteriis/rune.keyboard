"""Compile the production guard: no model, Android device, or flag regex oracle."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HEADER = (Path(__file__).resolve().parents[2] /
          "runtime-llama/src/main/cpp/RequireOptimization.h")


class OptimizationGuardTest(unittest.TestCase):
    def compile(self, flags, succeeds):
        for language, name in (("c", "cc"), ("c++", "c++")):
            with self.subTest(language=language, flags=flags):
                compiler = shutil.which(name)
                self.assertIsNotNone(compiler, f"Required host compiler is missing: {name}")
                with tempfile.TemporaryDirectory() as directory:
                    result = subprocess.run(
                        [compiler, "-x", language, *flags, "-include", str(HEADER),
                         "-c", "-", "-o", str(Path(directory) / "fixture.o")],
                        input="int rune_optimization_fixture(void) { return 0; }\n",
                        text=True, capture_output=True, timeout=30, check=False,
                    )
                if succeeds:
                    self.assertEqual(0, result.returncode, result.stderr)
                else:
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("Rune native runtime requires optimized compilation", result.stderr)

    def test_debug_symbols_and_release_optimization_are_allowed(self):
        self.compile(["-g", "-O2"], succeeds=True)
        self.compile(["-O2", "-DNDEBUG"], succeeds=True)

    def test_missing_optimization_is_rejected(self):
        self.compile(["-g"], succeeds=False)

    def test_explicit_unoptimized_build_is_rejected(self):
        self.compile(["-O0"], succeeds=False)

    def test_later_override_cannot_silently_disable_optimization(self):
        self.compile(["-O2", "-O0"], succeeds=False)


if __name__ == "__main__":
    unittest.main()
