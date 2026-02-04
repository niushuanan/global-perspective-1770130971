# 全球视角 | 跨语言观点对比

一个极简但专业的跨语言观点对比工具：用户输入事件关键词，系统并行完成多语言 YouTube 评论与多语言新闻报道的抓取、翻译与总结，帮助用户快速理解全球视角。

---

## 核心功能

### 1) 多语言视频评论分析
- **多语言检索**：中文/英文/日文/德语/法语/西班牙语/葡萄牙语。
- **视频选择策略**：在 YouTube 搜索结果中综合 **相关度 + 播放量 + 新近性** 评分，选取排名最高的 **2 个视频**。
- **评论策略**：每个视频抓取 **点赞最多的 10 条评论**（共 20 条），并翻译为中文。
- **自动总结**：系统默认生成跨语言评论对比总结，点击按钮可重新生成。

### 2) 多语言新闻报道分析
- **多源检索**：优先 GDELT Doc API（国际新闻聚合），并回退 Google News RSS。
- **付费墙过滤**：自动跳过高概率付费墙域名与页面。
- **正文抽取**：优先正文抽取，不可用则使用 RSS 摘要作为保底内容。
- **中等长度摘要**：保留原文约 50% 的信息量，兼顾细节与可读性。
- **中文翻译**：所有摘要统一翻译为中文，便于跨国对比。
- **自动总结**：系统默认生成跨国报道角度对比总结，可手动刷新。

---

## 技术架构

### 后端（FastAPI）
- **API 入口**：`/api/video`、`/api/news`、`/api/summary/comments`、`/api/summary/news`
- **并发模型**：多语言并行请求（Async + httpx）。
- **核心引擎**：
  - YouTube Data API（主）/ Invidious（备）
  - GDELT Doc API + Google News RSS
  - trafilatura / BeautifulSoup 正文提取
  - DeepSeek 负责翻译与总结

### 前端（静态 HTML）
- `app/static/index.html`：极简黑白布局，自动渲染评论与新闻卡片。
- 默认自动生成 AI 总结，按钮为“重新生成”。

---

## 业务流程

### 视频评论流程
1. 用户输入关键词。
2. 系统将关键词翻译为目标语言。
3. YouTube 搜索 → 取前 10 个结果 → 评分排序 → 取前 2 个视频。
4. 获取每个视频点赞最高的 10 条评论。
5. DeepSeek 翻译评论 → 生成中文结果。
6. DeepSeek 总结跨语言观点差异。

### 新闻流程
1. 用户输入关键词。
2. 系统将关键词翻译为目标语言。
3. GDELT Doc API 搜索 → 若不足回退 RSS。
4. 过滤付费墙 → 正文抽取 → 失败则使用 RSS 摘要。
5. DeepSeek 生成中等长度摘要。
6. DeepSeek 翻译摘要 → 生成中文版本。
7. DeepSeek 总结跨媒体立场差异。

---

## API 结构示例

### `POST /api/video`
返回结构示例：
```json
{
  "query": "红海航运危机",
  "summary": "...AI 总结...",
  "items": [
    {
      "key": "en",
      "label": "English",
      "emoji": "🇺🇸",
      "videos": [
        {
          "videoId": "...",
          "title": "...",
          "channel": "...",
          "viewCount": 123456,
          "publishedAt": "2025-12-01T12:00:00Z",
          "comments": [
            {"original": "...", "translated": "...", "likeCount": 521}
          ]
        }
      ],
      "comments": [
        {"original": "...", "translated": "...", "likeCount": 521}
      ]
    }
  ]
}
```

### `POST /api/news`
返回结构示例：
```json
{
  "query": "红海航运危机",
  "summary": "...AI 总结...",
  "items": [
    {
      "key": "en",
      "label": "English",
      "emoji": "🇺🇸",
      "article": {
        "title": "...",
        "source": "...",
        "url": "..."
      },
      "summary": "...",
      "summaryZh": "..."
    }
  ]
}
```

---

## 本地运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
```
填入必要的 `DEEPSEEK_API_KEY` 与 `YOUTUBE_API_KEY`（推荐）。

### 3. 启动服务
```bash
uvicorn app.main:app --reload --port 8000
```
打开 `http://localhost:8000`。

---

## Render 部署
项目已提供 `render.yaml`，可直接导入。

必须配置：
- `DEEPSEEK_API_KEY`
- `YOUTUBE_API_KEY`（强烈推荐，避免评论抓取失败）

可选：
- `TRANSLATE_PROVIDER=deepseek`
- `GDELT_TIMESPAN=30d`
- `ENABLE_BING_RSS=true`（默认关闭；仅在确认合规时开启）

---

## 环境变量说明（.env）

```env
DEEPSEEK_API_KEY=xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

YOUTUBE_API_KEY=xxx

TRANSLATE_PROVIDER=deepseek

INVIDIOUS_INSTANCES=https://yewtu.be,https://vid.puffyan.us
GDELT_TIMESPAN=30d
ENABLE_BING_RSS=false

HTTP_TIMEOUT=18
MAX_CONCURRENCY=6
```

---

## 注意事项
- 如果缺少 `YOUTUBE_API_KEY`，系统将使用 Invidious 公共实例作为兜底，但稳定性较弱。
- 新闻抽取受站点结构影响较大，已启用多级兜底策略（正文 → RSS 摘要）。
- DeepSeek API 需保持稳定可用，否则翻译与总结无法正常执行。

---

## 目录结构
```
app/
  core/           配置与常量
  services/       视频/新闻/翻译/摘要核心逻辑
  static/         前端页面
render.yaml       Render 部署配置
requirements.txt  依赖清单
```

---

## 未来扩展方向
- 新增更多语言与地区
- 新闻接入更多 RSS 与媒体源白名单
- 增加“可信度/情绪倾向”维度分析
- 引入用户自定义对比维度

