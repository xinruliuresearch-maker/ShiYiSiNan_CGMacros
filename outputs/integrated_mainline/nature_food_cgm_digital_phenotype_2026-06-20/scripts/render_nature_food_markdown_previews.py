"""Render Nature Food markdown documents into local HTML previews.

The Codex/editor preview can show raw Markdown when a rendered viewer is not
available. This script creates explicit HTML files so the user can open a
rendered preview directly in the browser.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(r"D:\ai for science")
PACKAGE = ROOT / "results" / "nature_food_p0_publication_lift_2026_06_18"
DOCS = PACKAGE / "docs"
TABLES = PACKAGE / "tables"
FIGURES = PACKAGE / "figures"
LEGENDS = PACKAGE / "figure_legends"
PREVIEW = PACKAGE / "preview"
PREVIEW.mkdir(parents=True, exist_ok=True)


DOC_ORDER = [
    "NatureFood_next_tasks_to_publication_zh_2026_06_18.md",
    "NatureFood_next_stage_completion_report_zh.md",
    "NatureFood_presubmission_enquiry_v1.0.md",
    "NatureFood_150_word_abstract_v1.0.md",
    "NatureFood_analysis_manuscript_skeleton_v0.1.md",
    "Reviewer_risk_response_memo_v1.0.md",
    "Aim1_claim_guardrails.md",
    "Aim2_Aim3_phase_bridge_guardrails.md",
    "Aim4_bridge_cohort_pilot_synopsis.md",
    "nature_food_next_stage_task_design_zh.md",
    "p0_claim_hierarchy_and_abstract_zh.md",
    "p0_completion_report_zh.md",
    "aim2_matrix_adjudication_protocol.md",
    "aim3_digital_phenotype_framing_zh.md",
]

LEGEND_ORDER = [
    "NatureFood_figure_legends_v0.1.md",
]

TABLE_ORDER = [
    "NatureFood_next_tasks_to_publication_matrix_2026_06_18.csv",
    "NatureFood_publication_decision_gates_2026_06_18.csv",
    "NatureFood_route_decision_memo.csv",
    "Aim1_source_proxy_to_DEHP_and_metabolic_anchor.csv",
    "Aim1_food_plasticizer_panel_literature_extraction_schema.csv",
    "Aim2_Aim3_CGMacros_phase_bridge_dataset.csv",
    "Aim2_Aim3_CGMacros_phase_bridge_models.csv",
    "nature_food_next_stage_task_matrix.csv",
    "nature_food_decision_gates.csv",
    "p0_claim_hierarchy.csv",
    "p0_aim1_food_system_exposure_matrix.csv",
    "p0_food_plasticizer_measurement_panel.csv",
    "p0_food_plasticizer_sampling_frame_96.csv",
    "p0_six_display_item_plan.csv",
    "p0_reviewer_risk_memo.csv",
    "p0_aim2_cgmacros_phase_map_feasibility.csv",
    "p0_aim2_cgmacros_phase_map_assignment.csv",
    "p0_aim3_digital_phenotype_evidence.csv",
    "p0_software_reproducibility_audit.csv",
]

FIGURE_ORDER = [
    "Figure1_integrated_architecture.png",
    "Figure2_population_exposure_anchor.png",
    "Figure3_meal_expression_layer.png",
    "Figure4_meal_redesign_phase_compatibility.png",
    "Figure5_cgm_digital_phenotype_validation.png",
    "Figure6_bridge_cohort_workflow.png",
]


CSS = """
:root {
  color-scheme: light;
  --bg: #f7f6f2;
  --paper: #fffefa;
  --ink: #1f2724;
  --muted: #5d6762;
  --line: #dad7cf;
  --accent: #1f6f64;
  --accent-soft: #dfeeea;
  --warn: #8b4d12;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "Noto Sans SC", "Microsoft YaHei", Arial, sans-serif;
  color: var(--ink);
  background: var(--bg);
  line-height: 1.65;
}
.layout {
  display: grid;
  grid-template-columns: minmax(230px, 300px) minmax(0, 1fr);
  min-height: 100vh;
}
aside {
  border-right: 1px solid var(--line);
  background: #f0eee7;
  padding: 24px 18px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}
aside h1 {
  font-size: 18px;
  margin: 0 0 12px;
  line-height: 1.25;
}
aside p {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 13px;
}
aside a {
  display: block;
  color: var(--ink);
  text-decoration: none;
  padding: 7px 8px;
  border-radius: 6px;
  font-size: 14px;
}
aside a:hover { background: var(--accent-soft); color: var(--accent); }
main {
  padding: 34px min(7vw, 80px) 80px;
}
article {
  max-width: 980px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 36px min(6vw, 64px);
  box-shadow: 0 12px 40px rgba(31, 39, 36, 0.08);
}
h1, h2, h3, h4 {
  line-height: 1.25;
  letter-spacing: 0;
}
h1 {
  font-size: 30px;
  margin: 0 0 24px;
}
h2 {
  font-size: 23px;
  margin: 34px 0 12px;
  border-top: 1px solid var(--line);
  padding-top: 24px;
}
h3 {
  font-size: 18px;
  margin: 24px 0 10px;
  color: var(--accent);
}
h4 { font-size: 15px; margin: 18px 0 8px; }
p { margin: 10px 0; }
ul, ol { margin: 8px 0 16px 22px; padding: 0; }
li { margin: 4px 0; }
code {
  font-family: Consolas, "SFMono-Regular", Menlo, monospace;
  background: #ece8df;
  border: 1px solid #ded7c9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.92em;
}
pre {
  overflow: auto;
  background: #202824;
  color: #f5f2e9;
  border-radius: 8px;
  padding: 16px;
}
pre code { background: transparent; border: 0; padding: 0; color: inherit; }
blockquote {
  margin: 18px 0;
  padding: 10px 16px;
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  color: #233d38;
}
.source-path {
  color: var(--muted);
  font-size: 12px;
  margin: -14px 0 24px;
}
.table-wrap {
  overflow-x: auto;
  margin: 18px 0 34px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  border: 1px solid var(--line);
  padding: 7px 9px;
  vertical-align: top;
}
th { background: #ede9de; text-align: left; }
tr:nth-child(even) td { background: #fbfaf6; }
.figure-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 26px;
}
.figure-card {
  border-top: 1px solid var(--line);
  padding-top: 22px;
}
.figure-card:first-child {
  border-top: 0;
  padding-top: 0;
}
.figure-card img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
}
.figure-card h2 {
  border-top: 0;
  padding-top: 0;
  margin-top: 0;
}
.badge {
  display: inline-block;
  font-size: 12px;
  color: var(--warn);
  background: #f7eadc;
  border: 1px solid #ebd1b6;
  border-radius: 999px;
  padding: 2px 8px;
  margin-left: 8px;
}
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  aside { position: static; height: auto; }
  main { padding: 20px; }
  article { padding: 24px 18px; }
}
"""


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_markdown(text: str) -> str:
    html_lines: list[str] = []
    list_stack: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def close_lists() -> None:
        while list_stack:
            html_lines.append(f"</{list_stack.pop()}>")

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                html_lines.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_lists()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            close_lists()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            close_lists()
            level = len(heading.group(1))
            content = inline_md(heading.group(2))
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue

        if stripped.startswith(">"):
            close_lists()
            html_lines.append(f"<blockquote>{inline_md(stripped.lstrip('> ').strip())}</blockquote>")
            continue

        unordered = re.match(r"^[-*]\s+(.*)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if unordered or ordered:
            tag = "ul" if unordered else "ol"
            if not list_stack or list_stack[-1] != tag:
                close_lists()
                html_lines.append(f"<{tag}>")
                list_stack.append(tag)
            content = unordered.group(1) if unordered else ordered.group(1)
            html_lines.append(f"<li>{inline_md(content)}</li>")
            continue

        close_lists()
        html_lines.append(f"<p>{inline_md(stripped)}</p>")

    if in_code:
        html_lines.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    close_lists()
    return "\n".join(html_lines)


def page_shell(title: str, body: str, nav: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="layout">
    <aside>
      <h1>Nature Food 渲染预览</h1>
      <p>这些页面由 Markdown、CSV 和主图文件生成，用于阅读、审稿前检查和投稿材料整理。</p>
      {nav}
    </aside>
    <main>
      {body}
    </main>
  </div>
</body>
</html>"""


def render_doc(path: Path, nav: str) -> Path:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    content = render_markdown(text)
    body = f"""<article>
<div class="source-path">Source: {html.escape(str(path))}</div>
{content}
</article>"""
    out = PREVIEW / f"{path.stem}.html"
    out.write_text(page_shell(title, body, nav), encoding="utf-8")
    return out


def render_table(path: Path, nav: str) -> Path:
    df = pd.read_csv(path)
    title = path.stem
    table_html = df.to_html(index=False, escape=True, classes="data-table")
    body = f"""<article>
<h1>{html.escape(title)}<span class="badge">{len(df)} rows</span></h1>
<div class="source-path">Source: {html.escape(str(path))}</div>
<div class="table-wrap">{table_html}</div>
</article>"""
    out = PREVIEW / f"{path.stem}.html"
    out.write_text(page_shell(title, body, nav), encoding="utf-8")
    return out


def render_figure_gallery(paths: list[Path], nav: str) -> Path:
    cards = []
    for path in paths:
        pdf_path = path.with_suffix(".pdf")
        pdf_link = ""
        if pdf_path.exists():
            pdf_link = f' | <a href="../figures/{html.escape(pdf_path.name)}">PDF</a>'
        cards.append(
            f"""<section class="figure-card">
<h2>{html.escape(path.stem.replace("_", " "))}</h2>
<div class="source-path">Source: {html.escape(str(path))}{pdf_link}</div>
<img src="../figures/{html.escape(path.name)}" alt="{html.escape(path.stem)}">
</section>"""
        )
    body = f"""<article>
<h1>Nature Food 六张主图预览<span class="badge">{len(paths)} figures</span></h1>
<p>以下为当前版本的六张主文图 PNG 渲染；对应 PDF 已同步输出，可用于后续投稿排版和矢量编辑。</p>
<div class="figure-grid">
{''.join(cards)}
</div>
</article>"""
    out = PREVIEW / "nature_food_main_figures.html"
    out.write_text(page_shell("Nature Food main figures", body, nav), encoding="utf-8")
    return out


def main() -> None:
    docs = [DOCS / name for name in DOC_ORDER if (DOCS / name).exists()]
    docs.extend([LEGENDS / name for name in LEGEND_ORDER if (LEGENDS / name).exists()])
    tables = [TABLES / name for name in TABLE_ORDER if (TABLES / name).exists()]
    figures = [FIGURES / name for name in FIGURE_ORDER if (FIGURES / name).exists()]
    nav_lines = ["<h4>主图</h4>"]
    if figures:
        nav_lines.append('<a href="nature_food_main_figures.html">六张主图预览</a>')
    nav_lines.append("<h4>文档</h4>")
    for path in docs:
        nav_lines.append(f'<a href="{path.stem}.html">{html.escape(path.name)}</a>')
    nav_lines.append("<h4>表格</h4>")
    for path in tables:
        nav_lines.append(f'<a href="{path.stem}.html">{html.escape(path.name)}</a>')
    nav = "\n".join(nav_lines)

    rendered = []
    if figures:
        rendered.append(str(render_figure_gallery(figures, nav)))
    for path in docs:
        rendered.append(str(render_doc(path, nav)))
    for path in tables:
        rendered.append(str(render_table(path, nav)))

    cards = []
    if figures:
        cards.append('<li><a href="nature_food_main_figures.html">六张主图预览</a></li>')
    for path in docs:
        cards.append(f'<li><a href="{path.stem}.html">{html.escape(path.name)}</a></li>')
    for path in tables:
        cards.append(f'<li><a href="{path.stem}.html">{html.escape(path.name)}</a></li>')

    index_body = f"""<article>
<h1>Nature Food P0/P1 渲染预览入口</h1>
<p>打开左侧链接或下面列表查看渲染后的文档、表格和六张主图。这个入口解决编辑器只显示 Markdown 源码的问题。</p>
<ul>
{''.join(cards)}
</ul>
</article>"""
    index_path = PREVIEW / "index.html"
    index_path.write_text(page_shell("Nature Food rendered preview", index_body, nav), encoding="utf-8")

    manifest = {
        "created": "2026-06-18",
        "preview_root": str(PREVIEW),
        "index": str(index_path),
        "rendered_files": rendered,
    }
    (PREVIEW / "preview_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote rendered preview index to {index_path}")


if __name__ == "__main__":
    main()
