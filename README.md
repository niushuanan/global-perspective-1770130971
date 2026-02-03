# 全球视角 | 跨语言观点对比

这是一个极简工具型网站：输入事件关键词，系统并行完成多语言 YouTube 评论分析与多语言新闻报道分析，输出评论原文 + 中文翻译，并支持一键 AI 总结。

## 功能说明
- **视频评论流程**：多语言检索 → 首条视频 → 抓取前五条评论 → 中文翻译 → AI 汇总
- **新闻报道流程**：多语言检索 → 过滤广告/付费墙 → 正文抽取 → 中等长度摘要 → 中文翻译 → AI 汇总

## 本地运行
1. 安装依赖
```bash
pip install -r requirements.txt
```
2. 配置环境变量
```bash
cp .env.example .env
```
填写 `DEEPSEEK_API_KEY`，其它可选变量按需填写。

3. 启动服务
```bash
uvicorn app.main:app --reload --port 8000
```
打开 `http://localhost:8000` 即可使用。

## 部署到 Render
已提供 `render.yaml`，可直接导入。

需要设置的环境变量：
- `DEEPSEEK_API_KEY`（必填）
- `YOUTUBE_API_KEY`（可选，未提供时使用 Invidious 公共实例）
- `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID`（可选，未提供时使用 Google News RSS）
- `MYMEMORY_EMAIL`（可选，MyMemory 翻译额度识别）

## 说明
- 如果缺少 YouTube/Google API Key，系统会自动使用免费公开接口进行兜底，但稳定性可能下降。
- 新闻摘要默认由 DeepSeek 生成，再翻译为中文。
