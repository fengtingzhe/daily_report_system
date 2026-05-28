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
3. 点击“运行真实日报流程”。
4. 打开 Tableau 并刷新数据源。
5. 从 Tableau 手动导出 PDF 到 `projects/default/reports/pdf/`。
6. 点击“检查 PDF”。
7. 点击“邮件 Dry-run”检查邮件配置和附件，不会正式发送邮件。

## 安全说明

- 控制台只绑定 `127.0.0.1`，不监听外网。
- 后端只允许运行白名单脚本，不提供任意命令输入。
- 文件预览只允许读取固定输出文件，不读取 `.env`。
- 不显示 API Key 或 SMTP 密码。
- 邮件功能只提供 dry-run，不提供正式发送按钮。
- 控制台不删除任何数据文件。
