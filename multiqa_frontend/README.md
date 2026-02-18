# 回声竞技场

## 本地启动
1. `cd /Users/zhuanghongkai/Desktop/大模型竞赛/multiqa_frontend`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python gateway.py`
6. 浏览器打开 `http://127.0.0.1:8787`

## 说明
- 智谱、Kimi、MiniMax 通过本地 Python 网关调用，支持流式输出与重试。
- DeepSeek、Qwen 仍由前端直连。
- 历史记录支持按条删除。
- 可用环境变量覆盖网关内置密钥：`ZHIPU_API_KEY`、`MOONSHOT_API_KEY`、`MINIMAX_API_KEY`。
- 当 `kimi-2.5-thinking` 不可用时，网关会自动回退到 `kimi-k2-0711-preview`，也可通过 `MOONSHOT_FALLBACK_MODEL` 覆盖。
- 前端私钥建议写到 `local_keys.js`（参考 `local_keys.example.js`），网关私钥建议写到 `secrets.local.json`（参考 `secrets.local.example.json`）。
- `local_keys.js` 和 `secrets.local.json` 已加入 `.gitignore`，不会被提交到 GitHub。
