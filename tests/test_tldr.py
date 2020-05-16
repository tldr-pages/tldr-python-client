import sys
import io
import types
import unittest
import tldr


class TLDRTests(unittest.TestCase):
    def test_whole_page(self):
        with open("tests/data/gem.md", "rb") as f_original:
            with open("tests/data/gem_rendered", "rb") as f_rendered:
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                sys.stdout.buffer = types.SimpleNamespace()
                sys.stdout.buffer.write = lambda x: sys.stdout.write(x.decode('utf-8'))
                tldr.output(f_original)

                sys.stdout.seek(0)
                tldr_output = sys.stdout.read().encode("utf-8")
                sys.stdout = old_stdout

                correct_output = f_rendered.read()
                self.assertEqual(tldr_output, correct_output)
