import sys
import io
import unittest
import tldr


class TLDRTests(unittest.TestCase):
    def test_whole_page(self):
        with open("tests/data/gem.md", "rb") as f_original:
            with open("tests/data/gem_rendered", "rb") as f_rendered:
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                tldr.rows = 24
                tldr.columns = 80
                tldr.output(f_original)

                sys.stdout.seek(0)
                tldr_output = sys.stdout.read().encode("utf-8")

                sys.stdout = old_stdout

                correct_output = f_rendered.read()
                self.assertEqual(tldr_output, correct_output)
