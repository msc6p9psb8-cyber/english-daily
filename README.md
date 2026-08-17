# English Daily News Workspace

每日英语新闻学习工作台（5 篇美/英真实新闻 + 词汇/语法/俚语精讲）。

- 页面地址（GitHub Pages 固定链接）：https://msc6p9psb8-cyber.github.io/english-daily/
- 每天 UTC 01:00（北京 09:00）与 UTC 03:00（北京 11:00）由 GitHub Actions 自动抓取 BBC/Guardian RSS 并更新页面
- 抓取失败时自动降级为离线模板内容（页面会明确标注）

## 手动触发

GitHub 仓库 → Actions → Daily English News → Run workflow

## 文件结构

- `index.html` — 工作台页面（单文件，含历史新闻与自愈引擎）
- `fetch_news.py` — 抓取 BBC/Guardian RSS → /tmp/live_news.json
- `update_news.py` — 注入/检测/兜底脚本（--status / --inject / --ensure）
- `.github/workflows/daily.yml` — 定时任务定义
