# 游戏运营日报自动化系统

## 项目用途

本系统从 Unity、AppLovin、Google Analytics 等平台自动拉取收入、用户、广告、投放数据，经清洗和建模后生成结构化数据宽表（Mart），供 Tableau 可视化以及 AI 自动撰写日报分析文字，最终导出 PDF 报告并邮件发送。

## 目录说明

| 目录 | 用途 |
|---|---|
| `config/` | 项目配置、API Key、指标规则、收件人、Tableau 配置 |
| `scripts/fetch/` | 从各平台拉取原始数据的脚本 |
| `scripts/transform/` | 原始数据清洗、标准化脚本 |
| `scripts/mart/` | 构建业务宽表（日概览、国家、平台、版本等维度） |
| `scripts/ai/` | AI 预分析、日报草稿生成、提示词模板 |
| `scripts/report/` | PDF 导出和邮件发送脚本 |
| `scripts/utils/` | 日期、文件、日志、校验等通用工具 |
| `data/raw/` | 各平台拉取的原始 CSV 数据 |
| `data/clean/` | 清洗后的标准化数据 |
| `data/mart/` | 业务宽表数据 |
| `data/tableau_datasource/` | Tableau 直接读取的固定路径 CSV 数据源 |
| `tableau/` | Tableau 工作簿、导出和备注 |
| `ai/` | AI 上下文、预分析、人工备注、草稿和终稿 |
| `reports/` | PDF、Excel、邮件输出 |
| `logs/` | 运行日志 |
| `archive/` | 月度备份和历史报告归档 |
| `temp/` | 下载缓存和临时文件 |

## 每日执行流程

1. **数据拉取**：从 Unity、AppLovin、GA4 拉取原始数据，存入 `data/raw/`
2. **数据清洗**：标准化字段名、统一时区、去重、异常值处理，写入 `data/clean/`
3. **构建宽表**：按业务维度聚合，生成日概览、国家、平台、版本、广告位、投放、留存等宽表
4. **AI 上下文**：将宽表数据汇总为 AI 可读的 JSON 摘要
5. **AI 生成报告**：调用 AI 生成预分析和日报草稿
6. **导出与发送**：将宽表复制到 `data/tableau_datasource/` 供 Tableau 刷新，导出 PDF，发送邮件

## 运行方式

双击 `run_daily_report.bat` 或在终端执行：

```bash
python scripts/run_all.py
```

## 未来迁移方向：DuckDB

当前第一阶段使用 CSV 文件存储，后续将迁移到 DuckDB：

- **替换 CSV 读写**：用 DuckDB 的 `read_csv_auto()` 和 `COPY ... TO` 替代 pandas 的 CSV I/O
- **SQL 构建宽表**：在 `scripts/mart/` 中改为执行 DuckDB SQL 查询，替代 pandas 聚合逻辑
- **Tableau 兼容**：DuckDB 原生支持 ODBC，Tableau 可直接连接 DuckDB 数据库文件或继续导出 CSV
- **优势**：列式存储、SQL 标准查询、无需部署数据库服务、兼容 Python 生态、查询性能优于 CSV

迁移时只需修改 `scripts/transform/` 和 `scripts/mart/` 的数据读写层，其余脚本不受影响。
