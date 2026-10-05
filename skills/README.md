# 共用 Agent Skills

`skills/` 是本 repo 工作流程的唯一內容來源，採用 Claude 與 Codex 都支援的 Agent Skills `SKILL.md` 格式。Agent 專屬目錄只負責 discovery：

```text
.claude/skills/<name> -> ../../skills/<name>
.agents/skills/<name> -> ../../skills/<name>
```

因此修改 skill 時只需編輯 `skills/<name>/SKILL.md`，不需同步兩份 prompt。

Claude Code 需使用支援 symlink skill folder 的 v2.1.203 或更新版本；第一次建立 `.claude/skills/` 後，既有 session 可能需要重啟一次。

## 使用方式

| Skill | Claude Code | Codex | 功能 |
| --- | --- | --- | --- |
| `add-news` | `/add-news [url ...]` | `$add-news [url ...]` | 封存新聞並建立內容檔，不 commit |
| `review-news-taxonomy` | `/review-news-taxonomy` | `$review-news-taxonomy` | 唯讀稽核新聞分類與標籤 |
| `commit-staged` | `/commit-staged` | `$commit-staged` | 只提交已 staged 的變更，不 push |

兩者也可依 `description` 在符合的自然語言請求中載入 skill；具副作用的 `commit-staged` 仍要求使用者明確提出 commit。

## 維護方式

新增 workflow 時，建立 `skills/<name>/SKILL.md`，frontmatter 僅使用共同欄位 `name` 與 `description`，再於 `.claude/skills/` 和 `.agents/skills/` 各加一個相對 symlink。避免在共用內容使用 `$ARGUMENTS`、特定 agent 工具名稱或 vendor-only frontmatter。

完成後執行：

```bash
scripts/validate-agent-skills.py
```

## 不透過 agent 執行 add-news

`scripts/add-news-ollama.sh` 以本機 Ollama 模型（預設 `qwen3.8:27b`）跑完整個 `add-news` 流程，不需要 Claude Code 或 Codex：

```bash
scripts/add-news-ollama.sh "https://example.com/article-one" "https://example.com/article-two"
```

它會封存網址、讀取文章、請模型決定 metadata、依 `references/news-taxonomy.toml` 驗證、寫入內容檔、更新佇列並列出結果分類；結束時卸載模型（若是腳本自行啟動 `ollama serve`，也會一併關閉）。常用選項：`--dry-run` 只分類不寫檔、`--no-think` 關閉思考模式加速、`--keep-model` 結束後保留模型、`--model` 或環境變數 `ADD_NEWS_MODEL` 更換模型。產生的檔案同樣不會自動 commit。
