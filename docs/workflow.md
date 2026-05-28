# 本地游戏运营日报工作流

本文档说明当前项目的测试流程、真实流程、数据分层和可选外部能力。

## 流程入口

测试流程：

```powershell
run_daily_report.bat
```

该流程运行 `scripts/run_all.py`，会生成 Tableau 测试数据源，再生成 AI 上下文和日报文字。

真实流程：

```powershell
run_real_daily_report.bat
```

该流程运行 `scripts/run_real_daily_report.py`，串联：

```text
scripts/import_raw_csv.py
scripts/build_mart_from_clean.py
scripts/sync_mart_to_tableau_datasource.py
scripts/generate_ai_context.py
scripts/generate_ai_report.py
```

完整真实流程测试：

```powershell
test_real_pipeline.bat
```

它会创建一个假的 Unity CSV，并跑通 raw -> clean -> mart -> Tableau datasource -> AI 文本。

## 手动 CSV 输入目录

把各平台手工导出的原始 CSV 放到：

```text
data/raw/unity/
data/raw/applovin/
data/raw/ga4/
```

`scripts/import_raw_csv.py` 会读取这些文件，清洗字段名并输出到 clean 层。

## 数据分层

raw 层：

```text
data/raw/
```

存放平台原始 CSV，不提交到 Git。

clean 层：

```text
data/clean/
```

存放清洗后的平台 CSV，不提交到 Git。

mart 层：

```text
data/mart/
```

存放面向分析的聚合宽表，不提交到 Git。

Tableau 固定数据源：

```text
data/tableau_datasource/
```

Tableau 模板读取这里的固定 CSV。`scripts/sync_mart_to_tableau_datasource.py` 会把 `data/mart/` 中的 mart 表同步到这里，但不会修改 `ai_report_text.csv`。

## AI 输出

AI 上下文：

```text
ai/context/daily_ai_context.json
```

日报草稿：

```text
ai/draft/daily_report_draft.md
```

Tableau 可读取的日报文字：

```text
data/tableau_datasource/ai_report_text.csv
```

DeepSeek 默认关闭。需要使用时，复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY`，并在 `config/ai_report.yaml` 中设置：

```yaml
use_deepseek: true
```

如果 DeepSeek 调用失败，脚本会自动回退到本地规则模板。

## PDF

当前 PDF 仍建议从 Tableau 手动导出到：

```text
reports/pdf/
```

检查最新 PDF：

```powershell
py scripts\check_pdf_output.py
```

`scripts/export_tableau_pdf.py` 是可选占位脚本，默认不自动导出。

## 邮件

邮件脚本默认 dry-run，不会直接发送：

```powershell
py scripts\send_report_email.py
```

确认 `.env` 中 SMTP 配置完整后，才使用：

```powershell
py scripts\send_report_email.py --send
```

## API 拉数骨架

当前 API 拉数脚本只做安全占位，不强行真实调用：

```text
scripts/fetch_unity_api.py
scripts/fetch_applovin_api.py
scripts/fetch_ga4_api.py
```

配置示例在：

```text
config/api_sources.example.yaml
```

如需启用，请复制为 `config/api_sources.yaml` 并填写真实配置。不要提交真实密钥。

## Git 安全规则

不要提交：

```text
data/raw/
data/clean/
data/mart/
reports/pdf/
logs/
.env
```

提交前运行：

```powershell
git status
```

确认只包含代码、配置样例和文档改动。
