import sys
import io
import types
import unittest
import tldr
import pytest
from mock import patch


class TLDRTests(unittest.TestCase):
    def test_whole_page(self):
        with open("tests/data/gem.md", "rb") as f_original:
            with open("tests/data/gem_rendered", "rb") as f_rendered:
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                sys.stdout.buffer = types.SimpleNamespace()
                sys.stdout.buffer.write = lambda x: sys.stdout.write(x.decode("utf-8"))
                tldr.output(f_original)

                sys.stdout.seek(0)
                tldr_output = sys.stdout.read().encode("utf-8")
                sys.stdout = old_stdout

                correct_output = f_rendered.read()
                self.assertEqual(tldr_output, correct_output)

    def test_error_message(self):
        testargs = ["tldr", "73eb6f19cd6f"]
        with patch.object(sys, "argv", testargs):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                tldr.main()
            correct_output = "`73eb6f19cd6f` documentation is not available. Consider contributing Pull Request to https://github.com/tldr-pages/tldr"  # noqa
            print("Test {}".format(pytest_wrapped_e))
            assert pytest_wrapped_e.type == SystemExit
            assert str(pytest_wrapped_e.value) == correct_output
