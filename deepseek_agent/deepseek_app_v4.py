from __future__ import annotations

from http.server import ThreadingHTTPServer

import deepseek_app_v3 as base
from deepseek_client import is_configured


HOST = base.HOST
PORT = base.PORT
PROJECT_DIR = base.PROJECT_DIR


class Handler(base.Handler):
    server_version = "DeepSeekSchedulerAgent/4.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            html = (PROJECT_DIR / "static" / "agent_v3.html").read_text(encoding="utf-8")
            html = html.replace(
                "</head>",
                '<link rel="stylesheet" href="/export_tools.css"></head>',
                1,
            )
            toolbar = """<div class="export-bar">
              <div><span class="export-title">导出当前版本</span><span class="export-hint">Markdown 用于飞书文档，CSV 用于表格复核</span></div>
              <div class="export-actions"><button id="export-md" class="export-btn" type="button" disabled>导出 Markdown</button><button id="export-csv" class="export-btn" type="button" disabled>导出 CSV</button></div>
            </div>"""
            html = html.replace("</section>", toolbar + "</section>", 1)
            html = html.replace("</body>", '<script src="/export_tools.js"></script></body>', 1)
            self.send_bytes(html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/export_tools.js":
            self.send_bytes((PROJECT_DIR / "static" / "export_tools.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        if self.path == "/export_tools.css":
            self.send_bytes((PROJECT_DIR / "static" / "export_tools.css").read_bytes(), "text/css; charset=utf-8")
            return
        super().do_GET()


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DeepSeek 可解释排班 Agent：http://{HOST}:{PORT}")
    print("功能：从0排表 / 追加需求 / 只读解释 / Markdown与CSV导出")
    print("状态：" + ("API Key 已配置" if is_configured() else "未配置 Key，将使用有限降级能力"))
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
