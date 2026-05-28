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

新项目结构下，推荐把各平台手工导出的原始 CSV 放到项目目录：

```text
projects/default/data/raw/unity/
projects/default/data/raw/applovin/
projects/default/data/raw/ga4/
```

然后指定项目运行：

```powershell
py scripts\run_real_daily_report.py --project default
```

旧根目录输入目录仍保留给兼容和历史测试：

把各平台手工导出的原始 CSV 放到：

```text
data/raw/unity/
data/raw/applovin/
data/raw/ga4/
```

`scripts/import_raw_csv.py` 会读取这些文件，清洗字段名并输出到 clean 层。

## 可迁移与多项目

本仓库现在采用“一套代码，多项目配置”的结构。不要为每个游戏复制一份完整代码仓库；多个游戏应放在同一个仓库的 `projects/<project_id>/` 下。

项目目录示例：

```text
projects/default/
projects/cash_game_a/
```

每个项目都有自己的数据、AI 输出、报告和 Tableau 目录：

```text
projects/default/data/raw/
projects/default/data/clean/
projects/default/data/mart/
projects/default/data/tableau_datasource/
projects/default/ai/context/
projects/default/ai/draft/
projects/default/reports/pdf/
projects/default/reports/email/
projects/default/tableau/
projects/default/logs/
```

迁移到另一台电脑时：

```text
1. 复制代码仓库
2. 安装 Python 依赖：python -m pip install -r requirements.txt
3. 复制 .env.example 为 .env，并填写本机密钥和 SMTP 配置
4. 复制或创建 projects/<project_id>/
5. 运行 py scripts\list_projects.py 检查项目列表
```

列出项目：

```powershell
py scripts\list_projects.py
```

创建新项目：

```powershell
py scripts\init_project.py --project cash_game_a --name "网赚游戏 A"
```

把旧根目录中的 Tableau 测试模板和 AI 文件复制到 `projects/default`：

```powershell
py scripts\migrate_root_to_project.py --project default
py scripts\migrate_root_to_project.py --project default --apply
```

第一条命令是 dry-run，只打印计划；第二条命令才真正复制。

真实流程推荐使用项目参数：

```powershell
py scripts\run_real_daily_report.py --project default
```

`run_real_daily_report.bat` 默认运行 `--project default`。如果要运行其他项目，可以直接执行：

```powershell
py scripts\run_real_daily_report.py --project cash_game_a
```

## 数据分层

raw 层：

```text
data/raw/
projects/default/data/raw/
```

存放平台原始 CSV，不提交到 Git。

clean 层：

```text
data/clean/
projects/default/data/clean/
```

存放清洗后的平台 CSV，不提交到 Git。

mart 层：

```text
data/mart/
projects/default/data/mart/
```

存放面向分析的聚合宽表，不提交到 Git。

Tableau 固定数据源：

```text
data/tableau_datasource/
projects/default/data/tableau_datasource/
```

Tableau 模板读取这里的固定 CSV。`scripts/sync_mart_to_tableau_datasource.py` 会把 `data/mart/` 中的 mart 表同步到这里，但不会修改 `ai_report_text.csv`。

## AI 输出

AI 上下文：

```text
ai/context/daily_ai_context.json
projects/default/ai/context/daily_ai_context.json
```

日报草稿：

```text
ai/draft/daily_report_draft.md
projects/default/ai/draft/daily_report_draft.md
```

Tableau 可读取的日报文字：

```text
data/tableau_datasource/ai_report_text.csv
projects/default/data/tableau_datasource/ai_report_text.csv
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
projects/default/reports/pdf/
```

检查最新 PDF：

```powershell
py scripts\check_pdf_output.py
py scripts\check_pdf_output.py --project default
```

`scripts/export_tableau_pdf.py` 是可选占位脚本，默认不自动导出。

## 邮件

邮件脚本默认 dry-run，不会直接发送：

```powershell
py scripts\send_report_email.py
py scripts\send_report_email.py --project default
```

确认 `.env` 中 SMTP 配置完整后，才使用：

```powershell
py scripts\send_report_email.py --send
py scripts\send_report_email.py --project default --send
```

## API 拉数

```text
scripts/fetch_unity_api.py
scripts/fetch_applovin_api.py
scripts/fetch_ga4_api.py
```

Unity 和 AppLovin 目前仍是安全占位脚本，不强行真实调用。GA4 已支持 Google Analytics Data API 第一版拉数，输出到：

```text
projects/default/data/raw/ga4/
```

配置示例在：

```text
config/api_sources.example.yaml
```

如需启用 GA4，请先完成：

```text
1. 在 Google Cloud 启用 Google Analytics Data API
2. 创建服务账号并下载 JSON
3. 在 GA4 后台给服务账号邮箱授予对应 Property 的查看权限
4. 本地创建 config/api_sources.yaml
5. 建议把服务账号 JSON 放到 secrets/
```

`config/api_sources.yaml` 示例：

```yaml
ga4:
  enabled: true
  property_id: "你的 GA4 property id"
  credentials_path: "D:/daily_report_system/secrets/ga4-service-account.json"
  start_date: "7daysAgo"
  end_date: "yesterday"
  reports:
    daily_overview: true
    country_platform_daily: true
    event_daily: true
```

检查配置但不调用 API：

```powershell
py scripts\fetch_ga4_api.py --project default --dry-run
```

正式拉取 GA4 raw CSV：

```powershell
py scripts\fetch_ga4_api.py --project default
```

也可以在 Web 控制台点击”拉取 GA4 API”。

GA4 配置可以在 Web 控制台中完成，不需要手动编辑 YAML：

1. 打开 http://127.0.0.1:8000
2. 在 “GA4 API 配置” 面板中填写 property_id、上传服务账号 JSON、设置日期范围和 reports 开关
3. 点击 “保存 GA4 配置” → 写入 config/api_sources.yaml
4. 点击 “检查 GA4 配置” → 验证配置完整性
5. 点击 “拉取 GA4 API” → 执行拉数

配置会保存到 `config/api_sources.yaml`，服务账号 JSON 保存到 `secrets/ga4-service-account.json`。这两个文件都不会提交 Git。

## Git 安全规则

不要提交：

```text
data/raw/
data/clean/
data/mart/
projects/*/data/raw/
projects/*/data/clean/
projects/*/data/mart/
projects/*/data/tableau_datasource/*.csv
reports/pdf/
projects/*/reports/pdf/
logs/
projects/*/logs/
.env
config/api_sources.yaml
secrets/
projects/*/secrets/
*service-account*.json
*credentials*.json
```

提交前运行：

```powershell
git status
```

确认只包含代码、配置样例和文档改动。

## Web 控制台

本地 Web 控制台位于：

```text
web_console/
```

启动方式：

```powershell
py web_console\app.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

控制台用于选择项目、查看 raw/clean/mart/Tableau/PDF 文件数量、配置 GA4 API、运行白名单日报脚本、预览 AI 输出和最新日志。它只绑定 `127.0.0.1`，不监听外网，不提供登录系统、文件删除、任意命令执行或正式发送邮件按钮。

推荐使用方式：

```text
1. 选择项目 default
2. 把真实 CSV 放到 projects/default/data/raw/unity/、applovin/、ga4/
3. 如需 GA4 API 拉数，先配置 config/api_sources.yaml，再点击“拉取 GA4 API”
4. 点击“运行真实日报流程”
5. 打开 Tableau 刷新数据源
6. 从 Tableau 手动导出 PDF 到 projects/default/reports/pdf/
7. 点击“检查 PDF”
8. 点击“邮件 Dry-run”
```
