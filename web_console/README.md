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

使用 GA4 API 前需要：

1. 在 Google Cloud 启用 Google Analytics Data API。
2. 创建服务账号并下载 JSON。
3. 在 GA4 后台给服务账号邮箱授予对应 Property 的查看权限。
4. 本地创建 `config/api_sources.yaml`，不要提交这个文件。
5. 建议把服务账号 JSON 放到 `secrets/`，不要提交 JSON。

配置示例：

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

正式拉取：

```powershell
py scripts\fetch_ga4_api.py --project default
```

## 安全说明

- 控制台只绑定 `127.0.0.1`，不监听外网。
- 后端只允许运行白名单脚本，不提供任意命令输入。
- 文件预览只允许读取固定输出文件，不读取 `.env`。
- 不显示 API Key 或 SMTP 密码。
- 邮件功能只提供 dry-run，不提供正式发送按钮。
- 控制台不删除任何数据文件。
