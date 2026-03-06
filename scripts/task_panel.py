# -*- coding: utf-8 -*-
"""Lightweight local web task panel for report generation."""

from __future__ import annotations

import argparse
import html
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generate_report


DEFAULT_EXCEL = r"C:\Users\Oliver\Desktop\数禾工作\16_AI项目\月报自动化\Data\2月月报数据_输入ai_0304_完整.xlsx"
DEFAULT_PROFILE = "config/profiles/monthly_report_v2_full.yaml"
DEFAULT_OUTPUT_ROOT = "export/runs"


def _run_id_default() -> str:
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def _split_indicators(indicators: str | None) -> list[str] | None:
    if not indicators:
        return None
    out = [x.strip() for x in indicators.split(",") if x.strip()]
    return out or None


def build_run_request(form: dict[str, str]) -> dict:
    excel = form.get("excel", "").strip()
    profile = form.get("profile", "").strip()
    run_id = form.get("run_id", "").strip() or _run_id_default()
    output_root = form.get("output_root", "").strip() or DEFAULT_OUTPUT_ROOT
    indicators_text = form.get("indicators", "").strip()

    output_path = Path(output_root) / run_id / "ppt" / "report.pptx"
    return {
        "excel_path": excel,
        "profile_path": profile,
        "indicator_ids": _split_indicators(indicators_text),
        "output_path": str(output_path),
        "emit_manifest": True,
    }


def run_request(form: dict[str, str]) -> dict:
    req = build_run_request(form)
    return generate_report.main(**req)


def _render_page(message: str = "", result: dict | None = None, form_values: dict | None = None) -> str:
    form_values = form_values or {}
    fv = {
        "excel": form_values.get("excel", DEFAULT_EXCEL),
        "profile": form_values.get("profile", DEFAULT_PROFILE),
        "run_id": form_values.get("run_id", _run_id_default()),
        "output_root": form_values.get("output_root", DEFAULT_OUTPUT_ROOT),
        "indicators": form_values.get("indicators", ""),
    }
    msg_html = f"<p style='color:#b00020'>{html.escape(message)}</p>" if message else ""
    result_html = ""
    if result:
        result_html = (
            "<h3>结果</h3>"
            f"<p>指标数: {result.get('indicator_count', '')}</p>"
            f"<p>PPT: <code>{html.escape(str(result.get('ppt_path', '')))}</code></p>"
            f"<p>HTML: <code>{html.escape(str(result.get('combined_html_path', '')))}</code></p>"
            f"<p>Manifest: <code>{html.escape(str(result.get('manifest_path', '')))}</code></p>"
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>月报任务面板</title>
  <style>
    body {{ font-family: "Microsoft YaHei", sans-serif; margin: 24px auto; max-width: 900px; line-height: 1.5; }}
    label {{ display: block; margin-top: 12px; font-weight: 700; }}
    input, textarea {{ width: 100%; padding: 8px; box-sizing: border-box; }}
    button {{ margin-top: 16px; padding: 10px 16px; }}
    .box {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; background: #fafafa; }}
    code {{ background: #f1f3f5; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h2>月报自动化任务面板</h2>
  <div class="box">
    {msg_html}
    <form method="post">
      <label>Excel 路径</label>
      <input name="excel" value="{html.escape(fv['excel'])}" required />
      <label>Profile 路径</label>
      <input name="profile" value="{html.escape(fv['profile'])}" required />
      <label>Run ID</label>
      <input name="run_id" value="{html.escape(fv['run_id'])}" />
      <label>输出根目录</label>
      <input name="output_root" value="{html.escape(fv['output_root'])}" />
      <label>指标列表（可选，逗号分隔）</label>
      <textarea name="indicators" rows="2">{html.escape(fv['indicators'])}</textarea>
      <button type="submit">开始生成</button>
    </form>
  </div>
  <div class="box" style="margin-top:16px">{result_html}</div>
</body>
</html>"""


class TaskPanelHandler(BaseHTTPRequestHandler):
    def _send_html(self, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        self._send_html(_render_page())

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        q = parse_qs(raw)
        form = {k: v[0] if v else "" for k, v in q.items()}
        try:
            result = run_request(form)
            self._send_html(_render_page(result=result, form_values=form))
        except Exception as exc:  # pragma: no cover
            self._send_html(_render_page(message=str(exc), form_values=form))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start local task panel.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args(argv)


def main(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), TaskPanelHandler)
    print(f"Task panel running: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    main(host=args.host, port=args.port)
