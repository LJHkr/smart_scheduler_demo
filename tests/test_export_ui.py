import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "deepseek_agent"))

from deepseek_app_v4 import Handler  # noqa: E402


class ExportUiTests(unittest.TestCase):
    def test_export_buttons_and_assets_are_served(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            page = urllib.request.urlopen(base + "/", timeout=3).read().decode("utf-8")
            script = urllib.request.urlopen(base + "/export_tools.js", timeout=3).read().decode("utf-8")
            self.assertIn('id="export-md"', page)
            self.assertIn('id="export-csv"', page)
            self.assertIn("buildMarkdown", script)
            self.assertIn("buildCsv", script)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
