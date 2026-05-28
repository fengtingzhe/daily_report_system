"""
发送最新 PDF 日报邮件。

默认 dry-run，不真正发送。只有传入 --send 参数时才会通过 SMTP 发送。
"""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs

PDF_DIR = PROJECT_ROOT / "reports" / "pdf"
ENV_PATH = PROJECT_ROOT / ".env"


def relative(path: Path) -> str:
    """输出相对项目根目录的路径。"""
    return str(path.relative_to(PROJECT_ROOT))


def find_latest_pdf() -> Path | None:
    """查找 reports/pdf/ 下最新 PDF。"""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdf_files[0] if pdf_files else None


def load_mail_config() -> dict[str, str]:
    """从 .env 读取 SMTP 配置。"""
    load_dotenv(ENV_PATH)
    keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "MAIL_TO"]
    return {key: os.getenv(key, "").strip() for key in keys}


def validate_config(config: dict[str, str]) -> list[str]:
    """检查必需配置项。"""
    return [key for key, value in config.items() if not value]


def build_message(config: dict[str, str], pdf_path: Path) -> EmailMessage:
    """构造邮件正文和 PDF 附件。"""
    report_date = datetime.now().strftime("%Y-%m-%d")
    subject = f"游戏运营日报 - {report_date}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["MAIL_FROM"]
    msg["To"] = config["MAIL_TO"]
    msg.set_content(
        "你好，\n\n附件为最新游戏运营日报 PDF。\n\n"
        "本邮件由本地日报自动化脚本生成。\n"
    )

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )
    return msg


def send_email(config: dict[str, str], msg: EmailMessage) -> None:
    """通过 SMTP 发送邮件。"""
    port = int(config["SMTP_PORT"])
    with smtplib.SMTP(config["SMTP_HOST"], port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
        smtp.send_message(msg)


def main() -> None:
    """主入口：默认 dry-run，--send 才真正发送。"""
    parser = argparse.ArgumentParser(description="Send latest report PDF by email.")
    add_project_arg(parser)
    parser.add_argument("--send", action="store_true", help="Actually send the email.")
    args = parser.parse_args()

    global PDF_DIR
    paths = ensure_project_dirs(args.project)
    PDF_DIR = paths["pdf_dir"]

    print("Report email sender")
    print(f"Project: {paths['project_id']}")
    print("Mode:", "SEND" if args.send else "DRY-RUN")

    pdf_path = find_latest_pdf()
    if pdf_path is None:
        print(f"No PDF found under {relative(PDF_DIR)}. Please export a PDF from Tableau first.")
        return

    print(f"Latest PDF: {relative(pdf_path)}")
    config = load_mail_config()
    missing = validate_config(config)
    if missing:
        print("Missing mail config in .env:", ", ".join(missing))
        print("Dry-run stopped before sending.")
        return

    msg = build_message(config, pdf_path)
    print(f"Mail subject: {msg['Subject']}")
    print(f"Mail to: {msg['To']}")

    if not args.send:
        print("Dry-run only. Add --send to actually send this email.")
        return

    send_email(config, msg)
    print("Email sent successfully.")


if __name__ == "__main__":
    main()
