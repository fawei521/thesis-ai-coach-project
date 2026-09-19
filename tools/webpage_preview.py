#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页本地预览器（纯 Python 标准库，无需安装任何东西）

用途：把学生做好的网页（或任何 HTML 文件）在本机跑起来，用浏览器打开看效果；
      也可以用手机看（需显式加 --lan，且手机与电脑连同一个 WiFi）。

用法：
  python tools/webpage_preview.py                      # 预览 我的工作区/04-网页/
  python tools/webpage_preview.py 我的工作区/04-网页      # 指定目录
  python tools/webpage_preview.py --list               # 只列出可预览的网页，不启动
  python tools/webpage_preview.py --port 8080          # 换端口
  python tools/webpage_preview.py --no-open            # 不自动打开浏览器
  python tools/webpage_preview.py --lan                # 允许局域网访问（手机可看，注意提示）

安全设计（重要）：
  - **只读**：只响应 GET/HEAD，不提供任何上传、写入、删除能力。
  - **不越界**：请求路径被限制在指定目录内，`..` 之类的穿越会被拒绝。
  - **默认只绑本机** 127.0.0.1；要手机看必须显式加 --lan，并会打印风险提示。
  - 不做任何联网上传，不收集任何数据。

特性：目录下有 index.html 自动作为首页；中文目录列表与中文 404 提示；
      端口被占用时自动往后找可用端口；按 Ctrl+C 停止。
"""
import argparse
import html
import io
import os
import posixpath
import socket
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到特殊字符会 UnicodeEncodeError 崩溃。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "我的工作区" / "04-网页"


def find_html(root: Path):
    """列出目录下所有 .html/.htm 文件（按路径排序）。"""
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".html", ".htm"):
            out.append(p)
    return out


class Handler(SimpleHTTPRequestHandler):
    """只读、限根、中文提示的静态文件处理器。"""

    server_version = "ThesisCoachPreview/1.0"

    # 文本类显式声明 charset=utf-8：学生的网页/CSV/文本都是 UTF-8，
    # 不声明时浏览器会按本地编码猜，中文容易变乱码。
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".svg": "image/svg+xml; charset=utf-8",
    }

    def __init__(self, *a, directory=None, **kw):
        super().__init__(*a, directory=str(directory), **kw)

    # ---- 安全：把请求路径规范化并锁在 root 内 ----
    def translate_path(self, path):
        path = urllib.parse.urlparse(path).path
        path = urllib.parse.unquote(path, errors="surrogatepass")
        # Windows 上反斜杠也是路径分隔符，先统一成 "/"，
        # 否则 "..\..\x" 这种会被当成单个文件名绕过下面的 ".." 过滤
        # （虽然末尾的 relative_to 兜底仍会拦住，但统一后行为跨平台一致、更可读）
        path = path.replace("\\", "/")
        path = posixpath.normpath(path)
        parts = [p for p in path.split("/") if p and p not in (".", "..")]
        result = Path(self.directory).resolve()
        for part in parts:
            result = result / part
        # 双保险：规范化后必须仍在根目录内
        try:
            result.resolve().relative_to(Path(self.directory).resolve())
        except ValueError:
            return str(Path(self.directory) / "__forbidden__")
        return str(result)

    def list_directory(self, path):
        """中文目录列表。"""
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            self.send_error(404, "Directory not found")
            return None
        shown = []
        for name in entries:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                shown.append((name + "/", name))
            elif name.lower().endswith((".html", ".htm", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".json", ".txt", ".csv")):
                shown.append((name, name))
        title = os.path.basename(path) or "网页预览"
        rows = "\n".join(
            '<li><a href="%s">%s</a></li>' % (
                urllib.parse.quote(link), html.escape(display))
            for link, display in shown)
        body = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} · 本地预览</title>
<style>
body{{font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif;
background:#F5F1E8;color:#1A1A1A;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.8}}
h1{{font-size:20px;color:#1B4332;border-bottom:2px solid #E0D8C8;padding-bottom:10px}}
p.hint{{color:#888;font-size:13px}}
ul{{list-style:none;padding:0}}
li{{background:#fff;margin:8px 0;padding:12px 16px;border-radius:8px;
box-shadow:0 1px 3px rgba(27,67,50,.08)}}
a{{color:#2D6A4F;text-decoration:none;font-weight:500}}
a:hover{{color:#C2410C}}
</style></head><body>
<h1>📁 {html.escape(title)}</h1>
<p class="hint">本地预览 · 这个页面由 tools/webpage_preview.py 生成，只在本机/本局域网可见，不会上传到任何地方。</p>
<ul>{rows or '<li>（这个目录下还没有可预览的文件）</li>'}</ul>
<p class="hint">按 <b>Ctrl+C</b>（关闭运行窗口）即可停止预览。</p>
</body></html>"""
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return io.BytesIO(data)

    def send_error(self, code, message=None, explain=None):
        """中文错误页。"""
        if code == 404:
            page = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
                    "<title>找不到这个文件</title></head>"
                    "<body style=\"font-family:'Microsoft YaHei',sans-serif;background:#F5F1E8;"
                    "color:#1A1A1A;max-width:640px;margin:60px auto;padding:0 20px;line-height:1.9\">"
                    "<h1 style='color:#C2410C;font-size:20px'>找不到这个文件</h1>"
                    "<p>预览器只提供<b>指定目录之内</b>的文件。请确认文件名和路径是否正确。</p>"
                    "<p><a href='/' style='color:#2D6A4F'>← 回到目录列表</a></p>"
                    "</body></html>").encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        """只打印被访问的文件名，不刷屏。"""
        try:
            sys.stdout.write("  访问: %s\n" % (args[0] if args else ""))
        except Exception:
            pass


def lan_ips():
    """尽量列出本机局域网 IPv4 地址。"""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips


def main():
    ap = argparse.ArgumentParser(
        description="网页本地预览器（只读、不上传、纯标准库）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", nargs="?", default=None,
                    help="要预览的目录（默认 我的工作区/04-网页）")
    ap.add_argument("--port", type=int, default=8000, help="端口，默认 8000（被占用会自动往后找）")
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--lan", action="store_true",
                    help="允许局域网访问（手机可看）；注意同网络的人也能访问这个目录")
    ap.add_argument("--list", action="store_true", help="只列出可预览的网页，不启动服务器")
    args = ap.parse_args()

    target = Path(args.directory).expanduser() if args.directory else DEFAULT_DIR
    if not target.is_absolute():
        target = (ROOT / target).resolve()
    else:
        target = target.resolve()

    if not target.exists():
        print("=" * 60)
        print("找不到要预览的目录：%s" % target)
        print("")
        print("你可以：")
        print("  1) 先把网页放进  我的工作区/04-网页/  （推荐，跟工具分开）")
        print("  2) 或直接指定目录：python tools/webpage_preview.py 你的目录")
        print("=" * 60)
        return 1
    if target.is_file():
        target = target.parent

    pages = find_html(target)
    if args.list:
        print("可预览的网页（目录：%s）：" % target)
        if not pages:
            print("  （没有找到 .html / .htm 文件）")
        for p in pages:
            print("  %s" % p.relative_to(target))
        return 0

    if not pages:
        print("提示：%s 里暂时没有 .html / .htm 文件。" % target)
        print("      仍会启动预览器，放好网页后刷新浏览器即可看到。")

    bind = "0.0.0.0" if args.lan else "127.0.0.1"
    httpd = None
    port = args.port
    for candidate in range(args.port, args.port + 20):
        try:
            httpd = HTTPServer((bind, candidate), lambda *a, **k: Handler(*a, directory=target, **k))
            port = candidate
            break
        except OSError as e:
            if candidate == args.port:
                print("端口 %d 被占用（%s），自动往后找…" % (candidate, e.strerror or e))
    if httpd is None:
        print("从 %d 起连续 20 个端口都被占用了，请用 --port 指定别的端口。" % args.port)
        return 1

    url = "http://127.0.0.1:%d/" % port
    print("=" * 60)
    print("网页预览已启动")
    print("=" * 60)
    print("预览目录：%s" % target)
    print("  找到 %d 个网页" % len(pages))
    print("")
    print("本机访问（浏览器打开这个地址）：")
    print("  %s" % url)
    if args.lan:
        print("")
        print("局域网访问（手机与电脑连同一个 WiFi）：")
        for ip in lan_ips():
            print("  http://%s:%d/" % (ip, port))
        print("")
        print("⚠️ 提醒：--lan 会让同一网络下的人也能访问这个目录里的文件。")
        print("   预览完就按 Ctrl+C 关掉；里面的数据请自行确认可以给别人看。")
    print("")
    print("按 Ctrl+C 停止预览。")
    print("=" * 60)

    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n预览已停止。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
