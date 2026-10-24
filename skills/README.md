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
| `commit-changes` | `/commit-changes` | `$commit-changes` | 依變更目的自動分組、stage 並建立一或多筆 commit；支援只預覽計畫，不 push |

兩種 agent 也可依 `description` 在符合的自然語言請求中載入 skill；建立 commit 仍要求使用者明確提出 commit 或直接呼叫提交 skill。詢問功能、建立 skill 或只要求預覽，不會提交現有變更。

`commit-changes` 的分組依據見 [公開規範與本專案的採用方式](commit-changes/references/commit-policy.md)：Git 的邏輯變更原則、Google Small CLs 的完整可用單位，以及 Conventional Commits 的訊息語意。它會先列出各組目的、檔案或 hunks、訊息與拆分理由，再依授權自動提交；不按檔案數或副檔名硬拆。

Codex 使用範例（Claude Code 將 `$commit-changes` 換成 `/commit-changes`）：

```text
$commit-changes
$commit-changes --dry-run
$commit-changes 只提交 Apollo 更新相關變更
```

沒有指定範圍時會檢查 staged、unstaged 與 untracked 變更。`--dry-run` 只列計畫，不改 index 或建立 commit；若只要提交目前 staged 的快照，繼續使用 `commit-staged`。

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
