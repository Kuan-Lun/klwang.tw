# 斜線指令說明

本目錄下的每個 `.md` 檔都是一個 Claude Code 的斜線指令（slash command）。在對話中輸入 `/<檔名>`（不含 `.md`）即可觸發，Claude 會照該檔案裡寫的步驟執行。

## /add-news `[url]`

封存一則新聞連結，並依本 repo 的慣例在 `source-code/content/news/` 建立對應的文章檔案。

- 用法：`/add-news https://example.com/some-article`
- 不帶網址時會反問你要處理哪一則。
- 執行內容：呼叫 `scripts/archive-url.sh` 做 Wayback Machine 封存 → 讀取原文（擋牆時退回讀封存頁，仍讀不到才用 FlareSolverr）→ 依既有慣例推導 `slug` → 判斷分類資料夾與 `tags` → 依規則產生檔名 → 寫入 TOML frontmatter。
- **不會自動 commit**，寫完檔案後會請你先檢視內容。

## /review-news-taxonomy

稽核 `source-code/content/news/` 底下的分類（資料夾）與標籤（`tags`）是否一致，純粹是唯讀報告，不會搬動或修改任何檔案。

- 用法：`/review-news-taxonomy`（不需參數）
- 會檢查：放在分類資料夾內的文章，`tags` 是否有包含該資料夾名稱；放在根目錄的文章，`tags` 是否其實該歸類到某個既有資料夾。
- 也會統計根目錄文章的標籤出現次數，若同一標籤累積到 3 篇以上，會建議是否該獨立成新資料夾（仿照當初 `電力` 資料夾的由來）。
- 只輸出報告；若要依報告內容搬檔案、開新資料夾，需另外明確要求 Claude 執行。

## /commit-staged

依本 repo 既有的 commit message 慣例，替目前已 `git add` 的變更自動撰寫訊息並送出 commit。

- 用法：先 `git add` 好要提交的檔案，再下 `/commit-staged`（不需參數）。
- 若尚未 `git add` 任何檔案，會停下請你先加入暫存區，不會自作主張幫你 add。
- 訊息格式遵循既有慣例 `type(scope): summary`（觀察歷史紀錄，幾乎一律用 `feat`，`scope` 依變動的目錄推斷，例如 `news`、`settings`、`commands`）。
- 若暫存區同時包含多個不相關領域的變更，會先跟你確認要合併成一則訊息，還是拆成多次 commit。
- 只會 commit，**不會**自動 push。

## 補充

- 這些指令的內容其實就是給 Claude 的操作指示（Markdown 文字），可以直接打開檔案閱讀或修改，調整規則即可改變 Claude 的行為，不需要寫程式。
- 新增指令時，檔名即為指令名稱（去掉 `.md`），檔案開頭用 YAML frontmatter 的 `description` 欄位簡短說明用途（會顯示在指令列表中），需要參數時可加 `argument-hint` 欄位。
