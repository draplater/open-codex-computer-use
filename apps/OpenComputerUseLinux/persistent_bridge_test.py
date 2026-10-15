import io
import json
import unittest
from unittest import mock
from runtime_test import load_runtime


class ServeTests(unittest.TestCase):
    def test_multiple_requests_errors_and_eof_share_one_runtime(self):
        runtime = load_runtime()
        output = io.StringIO()
        with mock.patch.object(runtime, "perform_operation", side_effect=[{"ok": True, "text": "first"}, RuntimeError("bad action"), {"ok": True, "text": "last"}]) as action:
            runtime.serve(io.StringIO('{"tool":"first"}\nnot-json\n[]\n{"tool":"bad"}\n{"tool":"last"}\n'), output)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(responses), 5)
        self.assertEqual(action.call_count, 3)
        self.assertTrue(responses[0]["ok"])
        self.assertFalse(responses[1]["ok"])
        self.assertFalse(responses[2]["ok"])
        self.assertEqual(responses[3]["error"], "bad action")
        self.assertEqual(responses[4]["text"], "last")


if __name__ == "__main__":
    unittest.main()
