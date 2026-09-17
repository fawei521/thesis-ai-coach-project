# -*- coding: utf-8 -*-
import sys, csv, subprocess, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] if "tests" in str(__file__) else Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))
TD = ROOT / "tests" / "test-data"
import data_cleaner as DC
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

res=[]
def ck(n,c,e=""):
    res.append(c); print(("PASS " if c else "FAIL ")+n+("  "+str(e) if not c and e else ""))

random.seed(7)
# ---------- 1. 已预处理数字表：10道Likert + 性别文本 + 年级文本 + 2个多选0/1哑变量 + 1个填空文本 + 用时 ----------
headers=["用时(秒)"]+[f"Q{i}" for i in range(1,11)]+["性别","年级","常用工具___ChatGPT","常用工具___文心一言","开放建议"]
rows=[]
likert_idx=list(range(1,11))
for i in range(60):
    r=[str(random.randint(120,600))]
    if i<5:  # 5份长直线无效（Q全选3）
        r += ["3"]*10
    else:
        r += [str(random.randint(1,5)) for _ in range(10)]
    r += [random.choice(["男","女"]), random.choice(["大一","大二","大三"]),
          str(random.randint(0,1)), str(random.randint(0,1)),
          random.choice(["","希望题目少一点","界面可以更友好","没什么建议都挺好的","加油"])]
    rows.append(r)
p=TD/"_special_numeric.csv"
with open(p,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(headers); w.writerows(rows)

hdr,d=DC.read_csv(str(p))
guess=DC.guess_response_cols(hdr,d)
guess_names=[hdr[j] for j in guess]
ck("guess只含Q1-Q10", guess_names==[f"Q{i}" for i in range(1,11)], str(guess_names))
ck("guess排除0/1哑变量", "常用工具___ChatGPT" not in guess_names and "常用工具___文心一言" not in guess_names)
ck("guess排除文本列", "性别" not in guess_names and "开放建议" not in guess_names)
# 无scales清洗：应只抓约5份长直线，不被多选0/1列污染（不会大面积误杀）
valid,invalid=DC.detect_invalid(hdr,d)
ck("清洗保留约55份(±2)", abs(len(valid)-55)<=2, f"valid={len(valid)} invalid={len(invalid)}")

# 黄金对照：把多选0/1列也强行当作答列（模拟旧逻辑），无效数应 >= 新逻辑（证明旧逻辑受污染）
resp_old = guess + [hdr.index("常用工具___ChatGPT"), hdr.index("常用工具___文心一言")]
v2,i2=DC.detect_invalid(hdr,d, response_cols=resp_old)
ck("纳入哑变量改变/不优于结果", len(i2)>=len(invalid), f"old_invalid={len(i2)} new_invalid={len(invalid)}")

# ---------- 2. 问卷星原始表：测 wjx_preprocess 多选/填空识别 ----------
raw_headers=["序号","所用时间","1.我感到快乐【非常不同意..非常同意】","2.我常焦虑【非常不同意..非常同意】",
             "3.你的性别","4.你所在年级","5.你常用哪些AI工具（多选）","6.你对本课程的建议（填空）"]
raw=[]
opts=["非常不同意","不太同意","一般","比较同意","非常同意"]
for i in range(20):
    raw.append([str(i+1), f"{random.randint(1,4)}分{random.randint(0,59)}秒",
                random.choice(opts), random.choice(opts),
                random.choice(["男","女"]), random.choice(["大一","大二","大三","大四"]),
                random.choice(["ChatGPT┋文心一言","文心一言","ChatGPT┋豆包┋文心一言","豆包"]),
                random.choice(["希望多一些实践","老师讲得很好","无","建议增加案例","课堂互动再多点就好了"])])
rp=TD/"_special_raw.csv"
with open(rp,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(raw_headers); w.writerows(raw)
out=TD/"_special_std.csv"; rep=TD/"_special_report.txt"
r=subprocess.run([sys.executable,str(ROOT/"tools"/"wjx_preprocess.py"),str(rp),"--output",str(out),"--report",str(rep)],
                 capture_output=True,text=True,encoding="utf-8",errors="replace")
ck("预处理退出0",r.returncode==0,r.stderr[-300:])
rep_txt=rep.read_text(encoding="utf-8",errors="replace")
ck("报告含多选题分类","多选题" in rep_txt and "常用哪些AI" in rep_txt)
ck("报告含开放填空题","开放填空题" in rep_txt or "开放填空" in rep_txt)
ck("多选/填空不进量表提示","不要" in rep_txt and "scales.txt" in rep_txt)
ck("年级列入需人工编码","人工编码" in rep_txt and "年级" in rep_txt)
ck("控制台提示多选", "多选" in r.stdout)

# 清理
for f in [p,rp,out,rep]:
    if f.exists(): f.unlink()
for f in TD.glob("_special*"): f.unlink()
print(f"\n==== {sum(res)}/{len(res)} 通过 ====")
sys.exit(0 if all(res) else 1)
