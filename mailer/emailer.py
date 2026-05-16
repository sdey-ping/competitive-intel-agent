"""
emailer.py — Executive-grade HTML email for competitive intelligence reports.

Parses the report markdown into semantic blocks (meta, diff, vendor sections)
and renders each with a fully inline-styled, email-client-safe HTML template.
All styles are inline — no class-based CSS — so Gmail, Outlook, and Apple Mail
all render correctly.
"""

import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config.settings import GMAIL_SENDER, GMAIL_APP_PASSWORD

# Accent colors for vendor header bands — rotate through these
_VENDOR_COLORS = ["#1a56db", "#047857", "#7c3aed", "#b45309", "#be123c"]

# H2 patterns that are structural (not vendor names)
_DIFF_H2_SIGNALS   = ["what's new", "🔔"]
_SKIP_H2_SIGNALS   = ["full intelligence", "📊", "⚠️", "errors"]

_FAINT_MARKERS = [
    "not directly relevant to this research focus",
    "not found in available sources",
    "not applicable",
    "no data retrieved",
]


# ── Public API ─────────────────────────────────────────────────────────────────

def send_report_email(recipients: list[str], report_markdown: str, gdrive_link: str = "") -> dict:
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        return {"success": False, "error": "Gmail credentials not configured in .env"}

    subject = f"Competitive Intelligence Report — {datetime.now().strftime('%B %d, %Y')}"
    html_body = _markdown_to_html(report_markdown, gdrive_link)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"]    = GMAIL_SENDER
                msg["To"]      = recipient
                msg.attach(MIMEText(report_markdown, "plain"))
                msg.attach(MIMEText(html_body, "html"))
                server.sendmail(GMAIL_SENDER, recipient, msg.as_string())
        return {"success": True}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Gmail authentication failed. Use an App Password, not your account password.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Markdown helpers ───────────────────────────────────────────────────────────

def _inline(text: str) -> str:
    """Inline markdown → HTML with fully inline styles (no class refs)."""
    text = re.sub(
        r'`([^`]+)`',
        r'<code style="background:#f1f5f9;padding:2px 6px;border-radius:3px;'
        r'font-family:Consolas,monospace;font-size:12px;color:#0f172a">\1</code>',
        text,
    )
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="font-weight:700;color:#0f172a">\1</strong>', text)
    text = re.sub(r'(?<!\w)\*([^*\n]+?)\*(?!\w)', r'<em style="color:#64748b">\1</em>', text)
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" style="color:#1a56db;text-decoration:none;font-weight:500">\1</a>',
        text,
    )
    text = re.sub(
        r'(?<!["\(>])(https?://[^\s<>"]+)',
        r'<a href="\1" style="color:#1a56db;text-decoration:none">\1</a>',
        text,
    )
    return text


def _render_lines(lines: list[str]) -> str:
    """Convert a list of text lines to HTML paragraphs and lists."""
    parts  = []
    in_ul  = False
    in_ol  = False

    def close_list():
        nonlocal in_ul, in_ol
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False

    P  = "margin:5px 0;font-size:13.5px;line-height:1.65;color:#334155"
    LI = "margin:3px 0;font-size:13.5px;line-height:1.65;color:#334155"

    for line in lines:
        s = line.strip()
        if not s:
            close_list()
            continue
        if re.match(r'^[-*] ', line):
            if in_ol:
                close_list()
            if not in_ul:
                parts.append('<ul style="margin:6px 0;padding-left:20px">')
                in_ul = True
            parts.append(f'<li style="{LI}">{_inline(s[2:])}</li>')
        elif re.match(r'^\d+\. ', line):
            if in_ul:
                close_list()
            if not in_ol:
                parts.append('<ol style="margin:6px 0;padding-left:20px">')
                in_ol = True
            content = re.sub(r'^\d+\. ', '', s)
            parts.append(f'<li style="{LI}">{_inline(content)}</li>')
        else:
            close_list()
            parts.append(f'<p style="{P}">{_inline(s)}</p>')

    close_list()
    return "".join(parts)


def _render_source_pills(lines: list[str]) -> str:
    """Render reference source lines as compact clickable pills."""
    links = []
    for line in lines:
        s = line.strip()
        if not s or s.upper().startswith("RULES") or s.upper().startswith("NO SPECIFIC"):
            continue
        m = re.match(r'^[-*]?\s*\[([^\]]+)\]\((https?://[^\)]+)\)', s)
        if m:
            links.append((m.group(1)[:65], m.group(2).rstrip(".,;)")))
        else:
            m2 = re.search(r'(https?://\S+)', s)
            if m2:
                url = m2.group(1).rstrip(".,;)")
                parts = url.split("//", 1)[-1].split("/")
                label = " › ".join(p.replace("-", " ").replace("_", " ").title()
                                   for p in parts if p)[:65]
                links.append((label, url))
    if not links:
        return ""

    pills = "".join(
        f'<a href="{url}" style="display:inline-block;margin:3px 4px 3px 0;padding:4px 12px;'
        f'background:#eff6ff;border:1px solid #bfdbfe;border-radius:20px;font-size:11.5px;'
        f'color:#1a56db;text-decoration:none;font-weight:500;white-space:nowrap">{title}</a>'
        for title, url in links
    )
    return (
        '<div style="padding:14px 20px;background:#f8faff;border-top:1px solid #dbeafe">'
        '<p style="margin:0 0 8px;font-size:10px;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#94a3b8">📎 Reference Sources</p>'
        f'<div style="line-height:2.2">{pills}</div>'
        '</div>'
    )


# ── Semantic parser ────────────────────────────────────────────────────────────

def _parse_blocks(markdown: str) -> dict:
    """
    Parse the report markdown into:
      meta          — date, research, vendors, feature, title
      diff_vendors  — [{name, lines}] from the What's New section
      vendor_sections — [{name, subsections: [{heading, lines}]}]
    """
    lines = markdown.split("\n")

    meta = {"title": "", "date": "", "research": "", "vendors": "", "feature": ""}
    diff_vendors: list    = []
    vendor_sections: list = []

    state               = "preamble"
    cur_diff_vendor     = None
    cur_diff_lines: list = []
    cur_vendor          = None
    cur_sub_heading     = None
    cur_sub_lines: list  = []

    def _flush_diff():
        nonlocal cur_diff_vendor, cur_diff_lines
        if cur_diff_vendor is not None:
            diff_vendors.append({"name": cur_diff_vendor, "lines": cur_diff_lines})
            cur_diff_vendor = None
            cur_diff_lines  = []

    def _flush_sub():
        nonlocal cur_sub_heading, cur_sub_lines
        if cur_vendor is not None and cur_sub_heading is not None:
            cur_vendor["subsections"].append(
                {"heading": cur_sub_heading, "lines": cur_sub_lines[:]}
            )
        cur_sub_heading = None
        cur_sub_lines   = []

    def _flush_vendor():
        nonlocal cur_vendor
        _flush_sub()
        if cur_vendor is not None:
            vendor_sections.append(cur_vendor)
            cur_vendor = None

    for line in lines:
        # Meta extraction (runs regardless of state)
        if line.startswith("# "):
            meta["title"] = line[2:].strip(); continue
        if line.startswith("**Date:**"):
            meta["date"] = re.sub(r'\*\*Date:\*\*\s*', '', line).strip().rstrip("  "); continue
        if line.startswith("**Research Focus:**"):
            meta["research"] = re.sub(r'\*\*Research Focus:\*\*\s*', '', line).strip().rstrip("  "); continue
        if line.startswith("**Vendors Analyzed:**"):
            meta["vendors"] = re.sub(r'\*\*Vendors Analyzed:\*\*\s*', '', line).strip(); continue
        if line.startswith("**Feature in Focus:**"):
            meta["feature"] = re.sub(r'\*\*Feature in Focus:\*\*\s*', '', line).strip().rstrip("  "); continue
        if line.strip() == "---":
            continue

        # H2 — route by type
        if line.startswith("## "):
            heading = line[3:].strip()
            _flush_diff()
            _flush_vendor()
            lower = heading.lower()
            if any(s in lower for s in _DIFF_H2_SIGNALS) or any(s in heading for s in ["🔔"]):
                state = "diff"
            elif any(s in lower for s in _SKIP_H2_SIGNALS) or any(s in heading for s in ["📊", "⚠️"]):
                state = "skip"
            else:
                state      = "vendor"
                cur_vendor = {"name": heading, "subsections": []}
            continue

        # H3
        if line.startswith("### "):
            heading = line[4:].strip()
            if state == "diff":
                _flush_diff()
                cur_diff_vendor = heading
                cur_diff_lines  = []
            elif state == "vendor":
                _flush_sub()
                cur_sub_heading = heading
                cur_sub_lines   = []
            continue

        # H4
        if line.startswith("#### "):
            heading = line[5:].strip()
            if state == "vendor":
                _flush_sub()
                cur_sub_heading = heading
                cur_sub_lines   = []
            continue

        # Content
        if state == "diff" and cur_diff_vendor is not None:
            cur_diff_lines.append(line)
        elif state == "vendor" and cur_vendor is not None and cur_sub_heading is not None:
            cur_sub_lines.append(line)

    _flush_diff()
    _flush_vendor()
    return {"meta": meta, "diff_vendors": diff_vendors, "vendor_sections": vendor_sections}


# ── Section renderers ──────────────────────────────────────────────────────────

def _html_header(meta: dict) -> str:
    # Extract mode label from title (everything after the dash)
    title = meta.get("title", "")
    mode_label = re.sub(r'^Competitive Intelligence Report\s*[—\-]\s*', '', title).strip()
    if not mode_label:
        mode_label = "Competitive Intelligence Report"

    research = meta.get("research", "")
    date_str = meta.get("date", "")
    vendors  = meta.get("vendors", "")
    feature  = meta.get("feature", "")

    vendor_pills = ""
    if vendors:
        for v in [x.strip() for x in vendors.split(",")]:
            vendor_pills += (
                f'<span style="display:inline-block;background:rgba(255,255,255,0.12);'
                f'border:1px solid rgba(255,255,255,0.2);border-radius:12px;padding:2px 11px;'
                f'font-size:11px;font-weight:600;color:#e2e8f0;margin:2px 4px 2px 0">{v}</span>'
            )

    feature_row = (
        f'<p style="margin:10px 0 0;font-size:12px;color:#94a3b8">'
        f'Feature in focus: <strong style="color:#bfdbfe;font-weight:600">{feature}</strong></p>'
        if feature else ""
    )

    return (
        '<tr>'
        '<td style="background:#0f172a;padding:36px 40px 28px">'
        '<p style="margin:0 0 6px;font-size:10.5px;font-weight:700;letter-spacing:0.15em;'
        'text-transform:uppercase;color:#475569">Competitive Intelligence</p>'
        f'<h1 style="margin:0 0 14px;font-size:24px;font-weight:700;color:#f8fafc;'
        f'letter-spacing:-0.4px;line-height:1.25">{mode_label}</h1>'
        + (f'<p style="margin:0 0 14px;font-size:13.5px;color:#cbd5e1;line-height:1.55">{research}</p>' if research else "")
        + feature_row
        + f'<div style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08)">'
        + (f'<p style="margin:0 0 8px;font-size:11px;color:#475569">📅 {date_str}</p>' if date_str else "")
        + f'<div>{vendor_pills}</div>'
        + '</div>'
        '</td>'
        '</tr>'
    )


def _html_drive_banner(gdrive_link: str) -> str:
    if not gdrive_link or not gdrive_link.startswith("http"):
        return ""
    return (
        '<tr>'
        '<td style="padding:0 40px">'
        '<div style="margin-top:20px;background:#eff6ff;border:1px solid #bfdbfe;'
        'border-radius:8px;padding:13px 18px">'
        f'<a href="{gdrive_link}" style="color:#1a56db;font-size:13px;font-weight:600;'
        'text-decoration:none">📁&nbsp; View Full Report in Google Drive &rarr;</a>'
        '</div>'
        '</td>'
        '</tr>'
    )


def _html_diff_section(diff_vendors: list) -> str:
    if not diff_vendors:
        return ""

    items_html = ""
    for dv in diff_vendors:
        content = _render_lines(dv["lines"])
        if not content.strip():
            continue
        items_html += (
            f'<div style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #fde68a">'
            f'<p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#92400e">{dv["name"]}</p>'
            f'{content}'
            '</div>'
        )

    if not items_html:
        return ""

    return (
        '<div style="margin-bottom:28px;background:#fffbeb;border:1px solid #fde68a;'
        'border-radius:10px;padding:20px 24px">'
        '<p style="margin:0 0 16px;font-size:10.5px;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#92400e">🔔 What\'s New Since Last Run</p>'
        + items_html
        + '</div>'
    )


def _html_vendor_card(vendor: dict, color: str) -> str:
    name = re.sub(r'^[^\w\s]+\s*', '', vendor["name"]).strip() or vendor["name"]

    subsections_html = ""
    sources_html     = ""

    for sub in vendor["subsections"]:
        heading = sub["heading"]
        lines   = sub["lines"]

        if "reference source" in heading.lower():
            sources_html = _render_source_pills(lines)
            continue

        content = _render_lines(lines)
        if not content.strip():
            continue

        # If the section is just a faint "not relevant" marker, render it muted
        full_text = "\n".join(lines).lower().strip()
        is_faint  = any(m in full_text for m in _FAINT_MARKERS)
        if is_faint:
            content = (
                f'<p style="margin:4px 0;font-size:13px;color:#94a3b8;font-style:italic">'
                f'{_inline(lines[0].strip()) if lines else "Not available."}</p>'
            )

        # Strip emoji from section label for cleaner uppercase display
        label = re.sub(r'[\U00010000-\U0010ffff☀-⟿✀-➿]\s*', '', heading).strip()

        subsections_html += (
            f'<div style="padding:16px 20px;border-bottom:1px solid #f1f5f9">'
            f'<p style="margin:0 0 8px;font-size:10px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:#94a3b8">{label}</p>'
            f'{content}'
            '</div>'
        )

    return (
        '<div style="margin-bottom:24px;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">'
        f'<div style="background:{color};padding:14px 20px">'
        f'<h2 style="margin:0;font-size:15px;font-weight:700;color:#ffffff;letter-spacing:0.3px">{name}</h2>'
        '</div>'
        + subsections_html
        + sources_html
        + '</div>'
    )


def _html_footer() -> str:
    return (
        '<tr>'
        '<td style="background:#f8fafc;padding:18px 40px;border-top:1px solid #e2e8f0">'
        '<p style="margin:0;font-size:11px;color:#94a3b8">'
        'Sent by <strong style="color:#64748b;font-weight:600">Competitive Intelligence Agent</strong>'
        f'&nbsp;&middot;&nbsp;{datetime.now().strftime("%B %d, %Y at %H:%M")}'
        '</p>'
        '</td>'
        '</tr>'
    )


# ── Main entrypoint ────────────────────────────────────────────────────────────

def _markdown_to_html(markdown: str, gdrive_link: str = "") -> str:
    blocks   = _parse_blocks(markdown)
    meta     = blocks["meta"]

    diff_html = _html_diff_section(blocks["diff_vendors"])

    cards_html = ""
    for i, vendor in enumerate(blocks["vendor_sections"]):
        cards_html += _html_vendor_card(vendor, _VENDOR_COLORS[i % len(_VENDOR_COLORS)])

    content_cell = (
        '<tr>'
        '<td style="padding:28px 40px 40px">'
        + diff_html
        + cards_html
        + '</td>'
        '</tr>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Competitive Intelligence Report</title>
</head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
  <!--[if mso]><table width="100%"><tr><td align="center"><![endif]-->
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#eef2f7">
    <tr>
      <td align="center" style="padding:32px 16px">
        <table width="660" cellpadding="0" cellspacing="0" role="presentation"
               style="width:660px;max-width:100%;background:#ffffff;border-radius:12px;
                      overflow:hidden;box-shadow:0 4px 28px rgba(0,0,0,0.10)">
          {_html_header(meta)}
          {_html_drive_banner(gdrive_link)}
          {content_cell}
          {_html_footer()}
        </table>
      </td>
    </tr>
  </table>
  <!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""
