#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 README.md 方案总览表格。数据来源：
  1) solutions/*/README.md 的 frontmatter（社区共建方案）
  2) solutions/links.json 的 entries（比赛成果登记，来自「提交成果链接」Issue）

表格写在 <!-- SOLUTIONS_INDEX_START --> 与 <!-- SOLUTIONS_INDEX_END --> 之间；
无内容时显示占位提示。除标记段外 README 内容一概不动。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
SOLUTIONS = os.path.join(ROOT, "solutions")
LINKS = os.path.join(SOLUTIONS, "links.json")

START = "<!-- SOLUTIONS_INDEX_START -->"
END = "<!-- SOLUTIONS_INDEX_END -->"


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
    # 来源 1：共建方案目录
    if os.path.isdir(SOLUTIONS):
        for name in sorted(os.listdir(SOLUTIONS)):
            d = os.path.join(SOLUTIONS, name)
            if not os.path.isdir(d) or name.startswith("."):
                continue
            rm = os.path.join(d, "README.md")
            meta = parse_frontmatter(rm) if os.path.isfile(rm) else {}
            rows.append({
                "team": meta.get("team") or name.split("-")[0],
                "solution": meta.get("solution") or (name.split("-", 1)[1] if "-" in name else name),
                "status": meta.get("status") or "—",
                "summary": meta.get("summary") or "",
                "repo": meta.get("repo") or "",
                "demo": meta.get("demo") or "",
                "dir": name, "link_type": "dir",
            })
    # 来源 2：比赛成果登记
    if os.path.isfile(LINKS):
        try:
            data = json.load(open(LINKS, encoding="utf-8"))
            for e in data.get("entries", []):
                rows.append({
                    "team": e.get("team", "?"),
                    "solution": e.get("solution", "?"),
                    "status": e.get("status", "—"),
                    "summary": e.get("summary", ""),
                    "repo": e.get("repo", ""),
                    "demo": e.get("demo", ""),
                    "dir": "", "link_type": "links",
                })
        except (json.JSONDecodeError, OSError):
            pass
    return rows


def render(rows):
    if not rows:
        return "> 暂无提交方案。比赛提交请 Fork 本仓库并开 [「提交成果链接」Issue](../../issues/new/choose)；赛后共建方案见 [solutions/ 指南](solutions/README.md)"
    lines = [
        "| 团队 | 方案 | 状态 | 简介 | 仓库/Demo |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        summary = (r["summary"] or "—").replace("|", "\\|")
        links = []
        if r["link_type"] == "dir":
            links.append(f"[solutions/{r['dir']}](solutions/{r['dir']})")
        elif r["repo"]:
            links.append(f"[Fork 仓库]({r['repo']})")
        if r["demo"]:
            links.append(f"[魔搭 Demo]({r['demo']})")
        cell = " · ".join(links) if links else "—"
        name = r["solution"]
        if r["repo"] and r["link_type"] == "links":
            name = f"[{name}]({r['repo']})"
        lines.append(f"| {r['team']} | {name} | {r['status']} | {summary} | {cell} |")
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
