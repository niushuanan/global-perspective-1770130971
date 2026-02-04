# 全球视角 | 跨语言评论对比（YouTube 专注版）

这是一个极简但专业的跨语言评论对比工具：用户输入事件关键词，系统并行抓取多语言 YouTube 评论，完成过滤、翻译与总结，帮助用户快速理解全球观点差异。

---

## 核心功能

### 1) 多语言评论采样
- 覆盖语言：中文 / 英文 / 日文 / 德语 / 法语 / 西班牙语 / 葡萄牙语
- 每种语言：**Top10 视频 × 每视频 5 条高赞评论** → 50 条
- 评论过滤：去链接 + 去低信息量 + 多语言广告/引流黑名单

### 2) 中文翻译
- 统一使用 DeepSeek 进行快速、地道翻译
- 同屏展示原文与中文译文

### 3) AI 总结（手动触发）
- 每个语言页可生成「本语种总结」
- 全局可生成「跨语言总总结」

---

## 产品体验结构

- **分页浏览**：每页一个语言社区（优雅翻页）
- **本语种总结**：用户点击生成，避免无效消耗
- **全球总结**：对比多语言舆情差异

---

## 技术架构

### 后端（FastAPI）
- `/api/video`：多语言评论抓取
- `/api/summary/comments`：本语种 / 全球总结

### 数据流程
1. 输入关键词
2. 多语言翻译
3. YouTube 搜索 → 取 Top10 视频
4. 抓取高赞评论 → 过滤
5. 翻译成中文
6. 按需生成总结

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
填入 `DEEPSEEK_API_KEY` 和 `YOUTUBE_API_KEY`。

### 3. 启动服务
```bash
uvicorn app.main:app --reload --port 8000
```
浏览器打开 `http://localhost:8000`。

---

## Render 部署

项目已提供 `render.yaml`，可直接导入。

必须配置：
- `DEEPSEEK_API_KEY`
- `YOUTUBE_API_KEY`

可选：
- `TRANSLATE_PROVIDER=deepseek`

---

## 环境变量说明（.env）

```env
DEEPSEEK_API_KEY=xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

YOUTUBE_API_KEY=xxx

TRANSLATE_PROVIDER=deepseek

INVIDIOUS_INSTANCES=https://yewtu.be,https://vid.puffyan.us

HTTP_TIMEOUT=18
MAX_CONCURRENCY=6
```

---

## 目录结构
```
app/
  core/           配置与常量
  services/       评论抓取、过滤、翻译、总结
  static/         前端页面
render.yaml       Render 部署配置
requirements.txt  依赖清单
```

---

## 过滤规则简述
- 含链接 → 直接过滤
- 低信息量（过短 / 纯表情 / 无有效字符）→ 过滤
- 多语言广告/引流词 → 过滤

---

## 未来可扩展方向
- 增加语言数量
- 增加「情绪倾向」与「关键词云」
- 引入自定义过滤强度（严格 / 默认 / 宽松）

