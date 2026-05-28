# 本地 Web 控制台

这是日报自动化项目的本机控制台 MVP，用于在浏览器里运行已经存在的多项目脚本。

## 启动

```powershell
cd D:\daily_report_system
py web_console\app.py
```

打开：

```text
http://127.0.0.1:8000
```

## 使用流程

1. 选择项目，例如 `default`。
2. 把真实 CSV 放到：
   - `projects/default/data/raw/unity/`
   - `projects/default/data/raw/applovin/`
   - `projects/default/data/raw/ga4/`
3. 如需从 GA4 Data API 拉数，先配置 `config/api_sources.yaml`，再点击“拉取 GA4 API”。
4. 点击“运行真实日报流程”。
5. 打开 Tableau 并刷新数据源。
6. 从 Tableau 手动导出 PDF 到 `projects/default/reports/pdf/`。
7. 点击“检查 PDF”。
8. 点击“邮件 Dry-run”检查邮件配置和附件，不会正式发送邮件。

## GA4 API

GA4 配置现在可以直接在 Web 控制台中完成，无需手动编辑 YAML 文件。

在 "GA4 API 配置" 面板中：

1. 填写 **Property ID**（例如 `123456789`）
2. 上传 **服务账号 JSON** 到 `secrets/ga4-service-account.json`
3. 设置 **日期范围**（start_date / end_date）
4. 勾选需要拉取的 **reports**（daily_overview / country_platform_daily / event_daily）
5. 点击 **保存 GA4 配置** → 写入 `config/api_sources.yaml`
6. 点击 **检查 GA4 配置** → 验证配置是否完整
7. 点击 **拉取 GA4 API** → 执行拉数脚本

配置会写入 `config/api_sources.yaml`，服务账号 JSON 保存到 `secrets/ga4-service-account.json`。这两个文件都不会提交到 Git。

前提条件：
- 在 Google Cloud 启用 Google Analytics Data API
- 创建服务账号并下载 JSON
- 在 GA4 后台给服务账号邮箱授予对应 Property 的查看权限

## 安全说明

- 控制台只绑定 `127.0.0.1`，不监听外网。
- 后端只允许运行白名单脚本，不提供任意命令输入。
- 文件预览只允许读取固定输出文件，不读取 `.env`。
- 不显示 API Key 或 SMTP 密码。
- 邮件功能只提供 dry-run，不提供正式发送按钮。
- 控制台不删除任何数据文件。
