"""
Tableau PDF 自动导出占位脚本。

不同环境可能使用 Tableau Desktop、Tableau Server 或 Tableau Cloud，自动导出方式不同。
因此本脚本默认不启用，只做环境检查和说明，不影响主流程。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "tableau_config.yaml"


def main() -> None:
    """检查 Tableau 命令行工具是否可用。"""
    print("Tableau PDF export helper")
    print("Default behavior: disabled. No PDF will be exported automatically.")

    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    tableau_exe = shutil.which("tableau")
    tabcmd_exe = shutil.which("tabcmd")

    if tableau_exe:
        print(f"Found Tableau command: {tableau_exe}")
    elif tabcmd_exe:
        print(f"Found tabcmd command: {tabcmd_exe}")
    else:
        print("No Tableau command line tool was found in PATH.")

    print("Configured workbook path:", config.get("workbook_path", "not configured"))
    print("Please export PDF manually from Tableau into reports/pdf/ for now.")


if __name__ == "__main__":
    main()
