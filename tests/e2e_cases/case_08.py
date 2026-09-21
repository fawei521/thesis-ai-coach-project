# -*- coding: utf-8 -*-
"""v1.65 GB/T 7714-2015 参考文献格式化工具（详见 e2e-test 测试64）----
full_e2e.py 顺序片段 8/14（原第 1287–1374 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.65 GB/T 7714-2015 参考文献格式化工具（详见 e2e-test 测试64）----
    rf_tool = "tools/reference_formatter.py"
    rf_src = tx(rf_tool)
    check("参考文献工具纯标准库", all(s in rf_src for s in ["import csv", "import re"])
          and "pandas" not in rf_src and "requests" not in rf_src)
    check("菜单第16项参考文献", "【16/" in menu and "reference_formatter.py" in menu and "GB/T 7714" in menu)
    # 菜单标签：编号须 1..N 连续、分母须统一等于项数。
    # 不把 N 硬编码进断言：硬编码会让每次加菜单项都要改一批 "全部20项制" 式断言，是维护地雷。
    labels = re.findall(r"【(\d+)/(\d+)】", menu)
    check("菜单标签编号连续且分母等于项数",
          bool(labels) and {d for _, d in labels} == {str(len(labels))}
          and sorted(int(n) for n, _ in labels) == list(range(1, len(labels) + 1)),
          "项数=%d 分母=%s" % (len(labels), sorted({d for _, d in labels})))
    MENU_N = len(labels)
    # v1.80：v1.77 交付的两件工具接进菜单（工具在命令行能跑不等于学生用得到，进菜单才算交付）
    check("菜单第21项排PPT且声明不代写",
          "【21/" in menu and "outline_to_ppt.py" in menu and "一个字也不替你写" in menu)
    check("菜单第22项补齐工作区且带只检查模式",
          "【22/" in menu and "setup_workspace.py" in menu and '"--check"' in menu)
    check("写作指南接线参考文献工具", "reference_formatter.py" in tx("workflows/writing-guide.md"))
    check("START登记参考文献工具", "reference_formatter.py" in st)
    v65 = new_tmp("v165refs")

    def wcsv65(name, header, rows, enc="utf-8-sig"):
        p65 = v65 / name
        with open(p65, "w", encoding=enc, newline="") as f65:
            w65 = csv.writer(f65)
            w65.writerow(header)
            for row65 in rows:
                w65.writerow(row65)
        return p65

    tpl = v65 / "tpl.csv"
    r = run([rf_tool, "--save-template", str(tpl)])
    check("v165模板生成", r.returncode == 0 and tpl.exists()
          and "类型" in tpl.read_text(encoding="utf-8-sig"))
    r = run([rf_tool, str(tpl)])
    tpl_out = v65 / "tpl_参考文献.txt"
    tpl_txt = tpl_out.read_text(encoding="utf-8") if tpl_out.exists() else ""
    check("v165模板回填著录", r.returncode == 0 and tpl_out.exists() and "[1]" in tpl_txt and "[4]" in tpl_txt)
    check("v165中文期刊四人截等",
          "张三, 李四, 王五, 等. 示例：中文期刊论文怎么著录[J]. 心理科学, 2025, 48(3): 123-130." in tpl_txt)
    check("v165英文GB姓全大写",
          "HENSELER J, RINGLE C M, SINKOVICS R R" in tpl_txt and "DOI:10.1108" in tpl_txt)
    check("v165学位论文著录", "示例学位论文题名[D]. 北京: 某某大学, 2024." in tpl_txt)
    check("v165电子资源著录", "[EB/OL]. (2026-01-01)[" in tpl_txt and "https://example.org/notice" in tpl_txt)
    jp = wcsv65("jp.csv", ["类型", "作者", "题名", "年份", "刊名/论文集/报纸", "卷", "期", "页码", "DOI"],
                [["期刊", "Wang, Y., Li, M., Chen, X., Zhao, L.", "APA four authors test",
                  "2025", "Some Journal", "10", "2", "1-9", "10.1/a"]])
    r = run([rf_tool, str(jp)])
    jtxt = (v65 / "jp_参考文献.txt").read_text(encoding="utf-8")
    check("v165APA四作者截et al", r.returncode == 0 and "WANG Y, LI M, CHEN X, et al" in jtxt)
    op = wcsv65("op.csv", ["序号", "标题", "作者", "原文出处"],
                [[1, "李四. 大学生AI情感依赖与心理健康的关系研究. 心理科学, , 48(3): 123-130", "张三,李四",
                  "张三,李四. 大学生AI情感依赖与心理健康的关系研究. 心理科学, 2025, 48(3): 123-130."]])
    r = run([rf_tool, str(op)])
    otxt = (v65 / "op_参考文献.txt").read_text(encoding="utf-8")
    check("v165整理表出处还原",
          "大学生AI情感依赖与心理健康的关系研究[J]. 心理科学, 2025, 48(3): 123-130." in otxt
          and "心理科学, , 48" not in otxt)
    gp = wcsv65("gp.csv", ["类型", "作者", "题名", "年份", "刊名/论文集/报纸"],
                [["期刊", "Jörg Henseler, Christian M. Ringle", "A title", "2025", "Some Journal"]])
    r = run([rf_tool, str(gp), "--fullwidth", "--no-number", "--name-case", "2025",
             "-o", str(v65 / "fw.txt")])
    fwtxt = (v65 / "fw.txt").read_text(encoding="utf-8")
    check("v165全角无编号2025口径", r.returncode == 0 and "Henseler J, Ringle C M" in fwtxt
          and "．" in fwtxt and "[1]" not in fwtxt)
    kp = wcsv65("kp.csv", ["类型", "作者", "题名", "年份", "刊名/论文集/报纸", "卷", "期"],
                [["期刊", "张三", "GBK编码测试", "2024", "心理学报", "56", "2"]], enc="gbk")
    r = run([rf_tool, str(kp)])
    check("v165GBK输入", r.returncode == 0
          and "GBK编码测试" in (v65 / "kp_参考文献.txt").read_text(encoding="utf-8"))
    ep = wcsv65("ep.csv", ["标题", "作者", "年份"], [])
    r = run([rf_tool, str(ep)])
    check("v165空表硬失败", r.returncode != 0 and "没有任何题录" in (r.stdout or ""))
    np_ = wcsv65("np.csv", ["作者", "年份"], [["张三", "2025"]])
    r = run([rf_tool, str(np_)])
    check("v165无题名列硬失败", r.returncode != 0 and "没找到题名列" in (r.stdout or ""))
    up = wcsv65("up.csv", ["标题", "作者"], [["神秘文献", "张三"]])
    r = run([rf_tool, str(up)])
    check("v165不可判类型硬失败", r.returncode != 0 and "无法判断文献类型" in (r.stdout or ""))
    r = run([rf_tool, str(v65 / "nope.csv")])
    check("v165文件不存在硬失败", r.returncode != 0 and "文件不存在" in (r.stdout or ""))
    r = run([rf_tool])
    check("v165无参数硬失败", r.returncode != 0 and "题录 CSV" in (r.stdout or ""))
    check("v165红线声明不生成文献", "不生成文献" in rf_src)


