#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 solutions/*/README.md 的 frontmatter 元信息，重建 README.md 中的方案总览表格。

表格写在 <!-- SOLUTIONS_INDEX_START --> 与 <!-- SOLUTIONS_INDEX_END --> 标记之间；
无方案时显示占位提示。除标记段外的 README 内容一概不动。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
SOLUTIONS = os.path.join(ROOT, "solutions")

START = "<!-- SOLUTIONS_INDEX_START -->"
END = "<!-- SOLUTIONS_INDEX_END -->"

FIELDS = {"team": "团队", "solution": "方案", "status": "状态", "summary": "简介", "repo": "独立仓库"}


def parse_frontmatter(path):
    meta = {}
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return meta
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return meta
    for line in m.group(1).splitlines():
        kv = re.match(r"^([a-zA-Z_]+)\s*:\s*(.+?)\s*$", line)
        if kv:
            meta[kv.group(1).lower()] = kv.group(2)
    return meta


def collect():
    rows = []
    if not os.path.isdir(SOLUTIONS):
        return rows
    for name in sorted(os.listdir(SOLUTIONS)):
        d = os.path.join(SOLUTIONS, name)
        rm = os.path.join(d, "README.md")
        if not os.path.isdir(d) or name.startswith("."):
            continue
        meta = parse_frontmatter(rm) if os.path.isfile(rm) else {}
        slug = name
        rows.append({
            "dir": slug,
            "team": meta.get("team") or slug.split("-")[0],
            "solution": meta.get("solution") or (slug.split("-", 1)[1] if "-" in slug else slug),
            "status": meta.get("status") or "—",
            "summary": meta.get("summary") or "",
            "repo": meta.get("repo") or "",
        })
    return rows


def render(rows):
    if not rows:
        return "> 暂无提交方案。第一个方案从这里开始 → 阅读 [solutions/ 提交指南](solutions/README.md)"
    lines = [
        "| 团队 | 方案 | 状态 | 简介 | 目录 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        link = f"[solutions/{r['dir']}](solutions/{r['dir']})" if r["status"] != "已迁出" else f"已迁出 → [{r['repo']}]({r['repo']})" if r["repo"] else "已迁出"
        name_cell = r["solution"] if not r["repo"] or r["status"] != "已迁出" else f"[{r['solution']}]({r['repo']})"
        summary = r["summary"].replace("|", "\\|")
        lines.append(f"| {r['team']} | {name_cell} | {r['status']} | {summary} | {link} |")
    return "\n".join(lines)


def main():
    if not os.path.isfile(README):
        print("README.md not found", file=sys.stderr)
        sys.exit(1)
    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        print("index markers missing; skip", file=sys.stderr)
        sys.exit(0)
    block = START + "\n" + render(collect()) + "\n" + END
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README index updated")
    else:
        print("index up to date")


if __name__ == "__main__":
    main()
