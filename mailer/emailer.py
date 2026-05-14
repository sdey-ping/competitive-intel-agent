import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config.settings import GMAIL_SENDER, GMAIL_APP_PASSWORD


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
                msg["From"] = GMAIL_SENDER
                msg["To"] = recipient
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


# ── HTML builder ───────────────────────────────────────────────────────────────

_EMAIL_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
       background: #f5f5f5; margin: 0; padding: 0; color: #1e293b; }
.wrapper { max-width: 720px; margin: 32px auto; background: #ffffff;
           border-radius: 12px; overflow: hidden;
           box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.top-bar { background: #1a56db; padding: 24px 32px; }
.top-bar h1 { color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }
.top-bar p { color: #bfdbfe; margin: 6px 0 0; font-size: 13px; }
.drive-banner { background: #eff6ff; border-left: 4px solid #1a56db;
                padding: 12px 20px; margin: 24px 32px 0; border-radius: 6px;
                font-size: 13px; }
.drive-banner a { color: #1a56db; font-weight: 600; text-decoration: none; }
.content { padding: 24px 32px 32px; }
h1 { font-size: 22px; color: #0f172a; border-bottom: 2px solid #e2e8f0;
     padding-bottom: 10px; margin-top: 28px; }
h2 { font-size: 18px; color: #1a56db; border-bottom: 1px solid #e2e8f0;
     padding-bottom: 6px; margin-top: 28px; }
h3 { font-size: 14px; color: #334155; text-transform: uppercase;
     letter-spacing: 0.05em; margin-top: 20px; font-weight: 700; }
h4 { font-size: 13px; color: #64748b; text-transform: uppercase;
     letter-spacing: 0.06em; margin-top: 16px; margin-bottom: 6px; font-weight: 700; }
p { font-size: 14px; line-height: 1.7; color: #334155; margin: 8px 0; }
li { font-size: 14px; line-height: 1.7; color: #334155; margin: 4px 0; }
ul, ol { padding-left: 20px; margin: 8px 0; }
a { color: #1a56db; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }
strong { color: #0f172a; }
em { color: #64748b; }
blockquote { border-left: 3px solid #1a56db; margin: 12px 0; padding: 8px 16px;
             background: #f8faff; border-radius: 0 6px 6px 0; color: #475569;
             font-size: 14px; }
.footer { background: #f8f7f4; padding: 16px 32px; font-size: 11px;
          color: #94a3b8; border-top: 1px solid #e8e4dd; }
"""


def _inline(text: str) -> str:
    """Apply inline markdown: bold, italic, inline code, links."""
    # Inline code `code`
    text = re.sub(r'`([^`]+)`', r'<code style="background:#f1f5f9;padding:1px 5px;'
                  r'border-radius:3px;font-family:monospace;font-size:12px">\1</code>', text)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text* or _text_ (not inside words)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)
    # Markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', text)
    # Bare URLs
    text = re.sub(r'(?<!["\(>])(https?://[^\s<>"]+)', r'<a href="\1">\1</a>', text)
    return text


def _markdown_to_html(markdown: str, gdrive_link: str = "") -> str:
    lines = markdown.split("\n")
    html_parts = []
    in_ul = False
    in_ol = False
    ol_counter = 0

    def _close_list():
        nonlocal in_ul, in_ol, ol_counter
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False
            ol_counter = 0

    for line in lines:
        # Headings
        if line.startswith("#### "):
            _close_list()
            html_parts.append(f"<h4>{_inline(line[5:])}</h4>")
        elif line.startswith("### "):
            _close_list()
            html_parts.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            _close_list()
            html_parts.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            _close_list()
            html_parts.append(f"<h1>{_inline(line[2:])}</h1>")
        # Horizontal rule
        elif line.strip() == "---":
            _close_list()
            html_parts.append("<hr>")
        # Unordered list
        elif re.match(r'^[-*] ', line):
            if in_ol:
                _close_list()
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            html_parts.append(f"<li>{_inline(line[2:].strip())}</li>")
        # Ordered list
        elif re.match(r'^\d+\. ', line):
            if in_ul:
                _close_list()
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            content = re.sub(r'^\d+\. ', '', line)
            html_parts.append(f"<li>{_inline(content.strip())}</li>")
        # Blockquote
        elif line.startswith("> "):
            _close_list()
            html_parts.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
        # Empty line
        elif line.strip() == "":
            _close_list()
            html_parts.append("<br>")
        # Paragraph
        else:
            _close_list()
            html_parts.append(f"<p>{_inline(line)}</p>")

    _close_list()

    drive_banner = ""
    if gdrive_link and gdrive_link.startswith("http"):
        drive_banner = (
            f"<div class='drive-banner'>"
            f"📁&nbsp; <a href='{gdrive_link}'>View full report in Google Drive</a>"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>{_EMAIL_CSS}</style></head>
<body>
<div class="wrapper">
  <div class="top-bar">
    <h1>Competitive Intelligence Report</h1>
    <p>Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
  </div>
  {drive_banner}
  <div class="content">
    {''.join(html_parts)}
  </div>
  <div class="footer">
    Sent by Competitive Intelligence Agent &nbsp;·&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}
  </div>
</div>
</body>
</html>"""
