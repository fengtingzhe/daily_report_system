# 游戏运营日报自动化系统

## 项目用途

本系统从 Unity、AppLovin、Google Analytics（GA4）等平台获取收入、用户、广告、投放数据，经清洗与建模生成结构化数据宽表（Mart），供 Tableau 可视化以及 AI 自动撰写日报分析文字。后续可导出 PDF 并邮件发送（当前为半自动 / 预演阶段）。

采用「一套代码，多个项目」结构：所有运行期数据都隔离在 `projects/<project_id>/` 下。

## 目录说明

| 目录 | 用途 |
|---|---|
| `config/` | 共享配置：字段映射、指标规则、AI、Tableau、收件人、数据源模板 |
| `scripts/` | 核心管线与工具脚本 |
| `scripts/utils/` | 项目路径解析、日志等通用工具 |
| `projects/<id>/` | 各项目独立的数据根目录（仅 `project.yaml` 入库） |
| `web_console/` | 本地浏览器控制台（FastAPI + 静态前端） |
| `docs/` | 工作流与迁移说明 |

每个项目目录 `projects/<id>/` 下运行期会生成：

```
data/raw/{unity,applovin,ga4}/   原始 CSV
data/clean/                       清洗后数据
data/mart/                        业务宽表
data/tableau_datasource/          Tableau 固定读取的 CSV 数据源
ai/context/、ai/draft/            AI 上下文与日报草稿
reports/pdf/、logs/、temp/、secrets/
```

## 每日执行流程

1. **数据获取**：GA4 通过 API 拉取（Unity / AppLovin 暂为手动导入 CSV），存入 `data/raw/`
2. **数据清洗**：标准化字段、统一格式，写入 `data/clean/`
3. **构建宽表**：按业务维度聚合，生成日概览、国家、平台、版本、广告位、投放、留存等 Mart
4. **同步 Tableau**：将 Mart 复制到 `data/tableau_datasource/` 供 Tableau 刷新
5. **AI 上下文**：将宽表汇总为 AI 可读的 JSON 摘要
6. **AI 生成报告**：用规则模板或 DeepSeek 生成日报文字（写回 Tableau 文本 CSV）

## 运行方式

### 安装依赖

```powershell
# 首次：双击 setup.bat 一键创建虚拟环境并安装依赖
setup.bat
```

或手动：

```powershell
py -m pip install -r requirements.txt
```

### 网页控制台（推荐）

```powershell
# 双击 open_web_console.bat，或：
py web_console\app.py
```

打开 http://127.0.0.1:8000 ，在网页中选择项目、运行各步骤、查看实时日志。

### 命令行：真实日报流程

```powershell
py scripts\run_real_daily_report.py --project default
```

依次执行：导入 CSV → 生成 Mart → 同步 Tableau → 生成 AI 上下文 → 生成 AI 日报文字。

### 命令行：测试流程（合成数据，隔离在 demo 项目）

```powershell
py scripts\run_all.py
```

生成 14 天模拟数据到 `projects/demo/`，再生成 AI 上下文与日报草稿，用于在 Tableau 中搭建第一个 Dashboard，不会影响真实项目。

### 每日自动调度（Windows 计划任务）

在网页控制台「设置 → 高级 → 自动调度」中勾选启用并设置时间，即可注册 Windows 计划任务，每天定时无人值守运行所选项目的真实日报流程。其底层调用 `scheduled_daily_report.bat`，运行日志写入 `projects/<id>/logs/scheduled_YYYYMMDD.log`。也可手动注册：

```powershell
schtasks /create /tn DailyReportSystem_default /tr "\"%CD%\scheduled_daily_report.bat\" default" /sc daily /st 08:30 /f
```

## 核心业务指标

- **付费率 / ARPPU**：日概览 Mart 增加 `payers`（付费人数）、`payment_rate = payers / DAU`、`arppu = IAP 收入 / payers`。`payers` 字段别名见 `config/field_mappings.yaml`。
- **留存（加权聚合）**：合并多平台 / 多国家时，留存率按各自 `new_users` 加权平均，而非简单取均值。
- **真实 cohort 留存**：当 clean 数据包含 `install_date`、`days_since_install`、`retained_users`（及可选 `cohort_size`）时，`mart_retention_daily` 按 `retained_users / cohort_size` 计算真实 D1/D3/D7/D14/D30；否则回退为按 `new_users` 加权聚合既有留存列。
- **异常告警**：阈值在「设置 → AI 与指标」中维护（含付费率跌幅阈值），命中后在总览页顶部以告警卡呈现。

## 未来迁移方向：DuckDB

## 未来迁移方向：DuckDB

当前使用 CSV 文件存储，后续可迁移到 DuckDB（列式存储、SQL 查询、无需部署服务、Tableau 可通过 ODBC 连接或继续导出 CSV）。迁移时主要改动 `scripts/build_mart_from_clean.py` 等数据读写层，其余脚本不受影响。
