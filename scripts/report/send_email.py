"""
邮件发送模块。
将 PDF 报告通过邮件发送给项目成员。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def send_email(report_date: str, pdf_path: Path | None = None) -> bool:
    """将 PDF 报告和邮件正文通过 SMTP 发送给收件人。"""
    # TODO: 读取 report_recipients.yaml，构建邮件，发送
    print(f"[send_email] 正在发送邮件，日期: {report_date}, 附件: {pdf_path}")
    return False  # 占位：返回发送是否成功


if __name__ == "__main__":
    send_email("2025-01-01")
