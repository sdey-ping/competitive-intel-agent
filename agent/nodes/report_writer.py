import time
from datetime import datetime
from agent.state import AgentState
from agent.tools.gdrive_tool import upload_report_to_drive
from db.database import save_report, save_diff_log


def report_writer_node(state: AgentState) -> AgentState:
    syntheses = state.get("syntheses", [])
    diffs = state.get("diffs", [])
    research_query = state.get("research_query", "General competitive overview")
    vendors = state.get("vendors", [])
    errors = state.get("errors", [])
    save_to_drive = state.get("save_to_drive", False)
    analysis_mode = state.get("analysis_mode", "strategic")
    target_feature = state.get("target_feature", "")

    diff_lookup = {d["vendor_name"]: d for d in diffs}

    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M")

    # ── Route to the correct report builder ───────────────────────────────────
    builder = {
        "feature_deep_dive": _build_feature_deep_dive_report,
        "landscape_scan":    _build_landscape_scan_report,
        "strategic":         _build_strategic_report,
        "battle_card":       _build_battle_card_report,
    }.get(analysis_mode, _build_strategic_report)

    report_markdown = builder(
        syntheses=syntheses,
        diffs=diffs,
        diff_lookup=diff_lookup,
        research_query=research_query,
        vendors=vendors,
        analysis_mode=analysis_mode,
        target_feature=target_feature,
        date_str=date_str,
        time_str=time_str,
        errors=errors,
    )

    # ── Persist ───────────────────────────────────────────────────────────────
    gdrive_link = ""
    drive_duration = 0.0

    if save_to_drive:
        drive_start = time.time()
        gdrive_label = ""
    else:
        gdrive_label = "__local_only__"

    report_id = save_report(
        research_query=research_query,
        vendors_covered=vendors,
        report_markdown=report_markdown,
        gdrive_link=gdrive_label,
    )
    for synthesis in syntheses:
        vendor_name = synthesis["vendor_name"]
        diff = diff_lookup.get(vendor_name, {})
        save_diff_log(
            report_id=report_id,
            vendor_name=vendor_name,
            previous_snapshot=diff.get("delta_summary", ""),
            new_snapshot=synthesis["raw_synthesis"],
            delta_summary=diff.get("delta_summary", ""),
        )

    if save_to_drive:
        date_file = now.strftime("%Y-%m-%d")
        filename = f"CompIntel — {date_file} — {research_query[:40]}"
        gdrive_link = upload_report_to_drive(report_markdown, filename)
        drive_duration = round(time.time() - drive_start, 1)

    return {
        **state,
        "final_report_markdown": report_markdown,
        "gdrive_link": gdrive_link,
        "drive_duration_seconds": drive_duration,
        "errors": errors,
        "current_step": "report_complete",
    }


# ── Report builders ────────────────────────────────────────────────────────────

def _header(research_query, date_str, time_str, vendors, mode_label, target_feature=""):
    feature_line = f"**Feature in Focus:** {target_feature}  \n" if target_feature else ""
    return [
        f"# Competitive Intelligence Report — {mode_label}",
        f"**Date:** {date_str} at {time_str}  ",
        f"**Research Focus:** {research_query}  ",
        feature_line,
        f"**Vendors Analyzed:** {', '.join(vendors)}",
        "",
        "---",
        "",
    ]


def _diff_section(diffs):
    lines = ["## 🔔 What's New Since Last Run", ""]
    if diffs:
        for diff in diffs:
            lines.append(f"### {diff['vendor_name']}")
            lines.append(diff["delta_summary"])
            lines.append("")
    else:
        lines.append("_First run — no previous snapshot to compare._")
        lines.append("")
    lines += ["---", ""]
    return lines


def _sources_section(synthesis: dict) -> list:
    """Build a Reference Sources markdown block for one vendor."""
    import re
    urls = synthesis.get("source_urls", [])
    if not urls:
        return []

    def _is_deep_link(entry: str) -> bool:
        m = re.search(r'https?://([^\s\)]+)', entry)
        if not m:
            return False
        full = m.group(0).rstrip(".,;)")
        path = full.split("//", 1)[-1]
        parts = path.split("/", 1)
        return len(parts) >= 2 and bool(parts[1].strip("/"))

    deep = [u for u in urls if _is_deep_link(u)]
    if not deep:
        return []

    lines = ["", "#### Reference Sources", ""]
    for entry in deep:
        if entry.startswith("["):
            lines.append(f"- {entry}")
        else:
            m = re.search(r'https?://([^\s\)]+)', entry)
            if m:
                url = m.group(0).rstrip(".,;)")
                path_parts = url.split("//", 1)[-1].split("/")
                label = " › ".join(p.replace("-", " ").replace("_", " ").title()
                                   for p in path_parts if p)[:80]
                lines.append(f"- [{label}]({url})")
    return lines


def _build_feature_deep_dive_report(syntheses, diffs, diff_lookup, research_query,
                                     vendors, analysis_mode, target_feature,
                                     date_str, time_str, errors, **_):
    lines = _header(research_query, date_str, time_str, vendors,
                    "🔬 Feature Deep Dive", target_feature)
    lines += _diff_section(diffs)

    for s in syntheses:
        lines += [
            f"## {s['vendor_name']}",
            "",
            "### Direct Answer",
            s.get("direct_answer", "_No data_"),
            "",
            "### What This Feature Does",
            s.get("recent_launches", "_No data_"),
            "",
            "### Who It's Built For",
            s.get("use_cases", "_No data_"),
            "",
            "### How It Fits Into Their Product Strategy",
            s.get("strategic_direction", "_No data_"),
            "",
            "### How It Compares to Our Product",
            s.get("gap_vs_your_product", "_No data_"),
            "",
            "### Watch Points",
            s.get("watch_points", "_No data_"),
        ]
        lines += _sources_section(s)
        lines += ["", "---", ""]
    if errors:
        lines += ["## ⚠️ Errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines)


def _build_landscape_scan_report(syntheses, diffs, diff_lookup, research_query,
                                  vendors, analysis_mode, target_feature,
                                  date_str, time_str, errors, **_):
    lines = _header(research_query, date_str, time_str, vendors, "📋 Landscape Scan")
    lines += _diff_section(diffs)

    for s in syntheses:
        lines += [
            f"## {s['vendor_name']}",
            "",
            "### Summary",
            s.get("direct_answer", "_No data_"),
            "",
            "### Recent Launches",
            s.get("recent_launches", "_No data_"),
            "",
            "### Signals & Themes",
            s.get("strategic_direction", "_No data_"),
            "",
            "### Gaps in Their Activity",
            s.get("gap_vs_your_product", "_No data_"),
        ]
        lines += _sources_section(s)
        lines += ["", "---", ""]
    if errors:
        lines += ["## ⚠️ Errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines)


def _build_strategic_report(syntheses, diffs, diff_lookup, research_query,
                             vendors, analysis_mode, target_feature,
                             date_str, time_str, errors, **_):
    lines = _header(research_query, date_str, time_str, vendors, "🧭 Strategic Analysis")
    lines += _diff_section(diffs)
    lines += ["## 📊 Full Intelligence by Vendor", ""]

    for s in syntheses:
        lines += [
            f"## {s['vendor_name']}",
            "",
            "### Direct Answer",
            s.get("direct_answer", "_No data_"),
            "",
            "### 🚀 Recent Feature Launches & Updates",
            s.get("recent_launches", "_No data_"),
            "",
            "### 🎯 Use Cases & Target Segments",
            s.get("use_cases", "_No data_"),
            "",
            "### ⚙️ Technical Architecture & Protocol Support",
            s.get("technical_details", "_No data_"),
            "",
            "### 🖥️ User Interface & UX",
            s.get("ui_ux", "_No data_"),
            "",
            "### 💰 Pricing & Packaging",
            s.get("pricing_signals", "_No data_"),
            "",
            "### 🧭 Strategic Direction",
            s.get("strategic_direction", "_No data_"),
            "",
            "### ⚔️ Gaps vs Your Product",
            s.get("gap_vs_your_product", "_No data_"),
            "",
            "### 👁️ Key Watch Points",
            s.get("watch_points", "_No data_"),
        ]
        lines += _sources_section(s)
        lines += ["", "---", ""]
    if errors:
        lines += ["## ⚠️ Errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines)


def _build_battle_card_report(syntheses, diffs, diff_lookup, research_query,
                               vendors, analysis_mode, target_feature,
                               date_str, time_str, errors, **_):
    lines = _header(research_query, date_str, time_str, vendors, "⚔️ Battle Card")
    lines += _diff_section(diffs)

    for s in syntheses:
        lines += [
            f"## {s['vendor_name']}",
            "",
            "### One-Line Answer",
            s.get("direct_answer", "_No data_"),
            "",
            "### ✅ Their Top 3 Strengths",
            s.get("recent_launches", "_No data_"),
            "",
            "### ❌ Their Top 3 Weaknesses",
            s.get("gap_vs_your_product", "_No data_"),
            "",
            "### 🏆 Where We Win",
            s.get("strategic_direction", "_No data_"),
            "",
            "### 💬 Common Objections & Responses",
            s.get("use_cases", "_No data_"),
            "",
            "### 💰 Pricing Summary",
            s.get("pricing_signals", "_No data_"),
            "",
            "### 🎯 One-Line Positioning",
            s.get("watch_points", "_No data_"),
        ]
        lines += _sources_section(s)
        lines += ["", "---", ""]
    if errors:
        lines += ["## ⚠️ Errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines)
