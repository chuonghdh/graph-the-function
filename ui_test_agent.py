"""Tác tử kiểm thử giao diện: khởi động Streamlit, điều khiển trình duyệt bằng Playwright, chụp ảnh.

Script làm ba việc:

1. Khởi động ``streamlit run app.py`` ở cổng riêng và chờ server sẵn sàng.
2. Mở Chromium (headless), nhập các hàm 2D và 3D vào ô động, bật làm nổi bật, rồi chụp ảnh
   màn hình ở từng trạng thái, cả màn hình máy tính lẫn điện thoại.
3. Chạy kiểm tra tự động trên DOM: chồng chữ giữa các phần tử, tràn chiều ngang, nền không tối,
   và lỗi JavaScript trong console. Kết quả ghi vào ``ui_artifacts/report.json``.

Ảnh chụp để đọc bằng mắt (vision review) được lưu trong ``ui_artifacts/``. Script không gọi mô hình
thị giác; người đánh giá ảnh đọc các file PNG và ghi nhận lỗi bố cục vào báo cáo.

Chạy: ``python ui_test_agent.py``. Thoát với mã 1 nếu có lỗi tự động phát hiện được.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "ui_artifacts"
PORT = 8510
URL = f"http://localhost:{PORT}"
DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}

OVERLAP_JS = """
() => {
  const sel = 'p, h1, h2, h3, h4, label, button, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"]';
  const nodes = [...document.querySelectorAll(sel)].filter(el => {
    const r = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && style.visibility !== 'hidden'
      && el.innerText && el.innerText.trim().length > 0
      && !el.closest('.js-plotly-plot');
  });
  const boxes = nodes.map(el => ({el, r: el.getBoundingClientRect(), t: el.innerText.trim().slice(0, 40)}));
  const issues = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (w <= 2 || h <= 2) continue;
      const area = w * h;
      const smaller = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
      if (smaller > 0 && area / smaller > 0.3) issues.push(`chồng chữ: "${a.t}" và "${b.t}"`);
    }
  }
  return issues.slice(0, 20);
}
"""

ANNOTATION_OVERLAP_JS = """
() => {
  const nodes = [...document.querySelectorAll('.js-plotly-plot .annotation .annotation-text-g')];
  const boxes = nodes.map(n => ({r: n.getBoundingClientRect(), t: n.textContent.slice(0, 18)}))
    .filter(b => b.r.width > 0 && b.r.height > 0);
  const issues = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i].r, b = boxes[j].r;
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 3 && h > 3) issues.push(`chú thích chồng nhau: "${boxes[i].t}" và "${boxes[j].t}"`);
    }
  }
  return issues.slice(0, 20);
}
"""

LAYOUT_JS = """
() => {
  const issues = [];
  const doc = document.documentElement;
  if (doc.scrollWidth > doc.clientWidth + 1) {
    issues.push(`tràn ngang trang: scrollWidth=${doc.scrollWidth} > clientWidth=${doc.clientWidth}`);
  }
  const app = document.querySelector('.stApp');
  if (app) {
    const bg = getComputedStyle(app).backgroundColor;
    const m = bg.match(/\\d+/g);
    if (m) {
      const lum = (0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]) / 255;
      if (lum > 0.15) issues.push(`nền không tối: ${bg}`);
    }
  }
  const badge = document.querySelector('.mode-badge');
  if (badge) {
    const r = badge.getBoundingClientRect();
    if (r.right > window.innerWidth + 1) issues.push('badge tràn khỏi màn hình bên phải');
  }
  return issues;
}
"""


@dataclass
class ScenarioReport:
    """Kết quả một kịch bản: ảnh đã chụp và các lỗi tự động phát hiện."""

    name: str
    screenshot: str
    issues: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)


def start_streamlit() -> subprocess.Popen[bytes]:
    """Khởi động Streamlit ở cổng riêng và chờ đến khi server sẵn sàng."""
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
         "--server.port", str(PORT), "--server.headless", "true"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2) as response:
                if response.status == 200:
                    return process
        except OSError:
            time.sleep(1)
    process.kill()
    raise RuntimeError("Streamlit không khởi động được trong 60 giây.")


def wait_ready(page: Page) -> None:
    """Chờ giao diện Streamlit tải xong, rồi chờ Plotly vẽ xong chú thích.

    Chú thích của Plotly được vẽ sau khi biểu đồ hiện, nên chụp ảnh sớm sẽ thiếu nhãn.
    """
    page.wait_for_selector("text=Vẽ đồ thị hàm số", timeout=60_000)
    page.wait_for_function(
        "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')",
        timeout=60_000,
    )
    time.sleep(1.0)
    page.wait_for_function(
        "() => { const plots = document.querySelectorAll('.js-plotly-plot'); return plots.length === 0 "
        "|| document.querySelectorAll('.js-plotly-plot .annotation').length >= 0; }",
        timeout=30_000,
    )
    time.sleep(1.5)


def set_equation(page: Page, position: int, text: str) -> None:
    """Điền một phương trình vào ô thứ ``position`` (từ 1) và xác nhận bằng Enter."""
    box = page.get_by_role("textbox", name=f"Phương trình f{position}")
    box.fill(text)
    box.press("Enter")
    wait_ready(page)


def add_slots(page: Page, count: int) -> None:
    """Bấm nút thêm hàm số ``count`` lần."""
    for _ in range(count):
        page.get_by_role("button", name="➕ Thêm hàm số").click()
        wait_ready(page)


def run_checks(page: Page, console: list[str]) -> tuple[list[str], list[str]]:
    """Chạy kiểm tra tự động trên trang hiện tại.

    Returns:
        Cặp ``(issues, console_errors)``.
    """
    issues = page.evaluate(OVERLAP_JS) + page.evaluate(ANNOTATION_OVERLAP_JS) + page.evaluate(LAYOUT_JS)
    return issues, list(console)


def capture(page: Page, name: str, console: list[str]) -> ScenarioReport:
    """Chụp ảnh và chạy kiểm tra cho một trạng thái."""
    path = ARTIFACTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    issues, errors = run_checks(page, console)
    console.clear()
    return ScenarioReport(name=name, screenshot=str(path.relative_to(ROOT)), issues=issues, console_errors=errors)


def open_page(browser: Browser, viewport: dict[str, int], console: list[str]) -> Page:
    """Mở trang mới với viewport cho trước và ghi lại lỗi console."""
    page = browser.new_page(viewport=viewport)
    page.on("console", lambda msg: console.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console.append(str(exc)))
    page.goto(URL)
    wait_ready(page)
    return page


def run_scenarios(browser: Browser) -> list[ScenarioReport]:
    """Chạy các kịch bản chính và trả về báo cáo từng kịch bản."""
    reports: list[ScenarioReport] = []
    console: list[str] = []

    page = open_page(browser, DESKTOP, console)
    reports.append(capture(page, "01_default_2d", console))

    add_slots(page, 2)
    set_equation(page, 3, "|x| - 2")
    set_equation(page, 4, "e**(-x**2)")
    reports.append(capture(page, "02_four_functions_2d", console))

    set_equation(page, 1, "x^2/9 + y^2/4 = 1")
    set_equation(page, 2, "sin(pi*x)")
    reports.append(capture(page, "03_implicit_and_pi_2d", console))

    set_equation(page, 1, "x^2 + y^2 + z^2 = 16")
    set_equation(page, 2, "z = x + y")
    set_equation(page, 3, "x^2 + y^2 = 4")
    set_equation(page, 4, "sin(pi*x)")
    reports.append(capture(page, "04_mixed_3d", console))

    checkbox = page.get_by_role("checkbox", name="Làm nổi bật f1 ∩ f2")
    if checkbox.count():
        checkbox.first.check(force=True)
        wait_ready(page)
    reports.append(capture(page, "05_3d_highlight_pair", console))
    page.close()

    mobile = open_page(browser, MOBILE, console)
    reports.append(capture(mobile, "06_mobile_2d", console))
    mobile.close()
    return reports


def main() -> int:
    """Điểm vào: chạy toàn bộ kịch bản, ghi báo cáo, và trả về mã thoát."""
    ARTIFACTS.mkdir(exist_ok=True)
    server = start_streamlit()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                reports = run_scenarios(browser)
            finally:
                browser.close()
    finally:
        server.terminate()
        server.wait(timeout=20)

    report_path = ARTIFACTS / "report.json"
    report_path.write_text(json.dumps([asdict(r) for r in reports], ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [r for r in reports if r.issues or r.console_errors]
    for r in reports:
        status = "LỖI" if r.issues or r.console_errors else "ok"
        print(f"[{status}] {r.name} -> {r.screenshot}")
        for issue in r.issues + r.console_errors:
            print(f"    - {issue}")
    print(f"\nBáo cáo: {report_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
