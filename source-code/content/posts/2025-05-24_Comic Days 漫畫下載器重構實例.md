+++
title = "SOLID 原則應用：Comic Days 漫畫下載器重構實例"
slug = "comicdays-zhtw"
date = "2025-05-24"

[taxonomies]
tags = ["SOLID", "重構", "設計模式", "Go"]
authors = ["王冠倫"]
+++

# 前言

本案例重構自 GitHub 開源專案 [`ComicDaysGoDownloader`](https://github.com/MrShitFox/ComicDaysGoDownloader)，其初始版本取自 commit [`c219073`](https://github.com/MrShitFox/ComicDaysGoDownloader/commit/c2190734d1018c1ab421b346ccad10a475386ac0)。

這份程式碼完成了漫畫頁面的下載與解碼工作。雖然功能完整，但存在一些可讀性差、耦合度高、不易擴充與測試的情況，導致維護與擴充困難。

以下透過實際重構，說明如何轉換成乾淨、可維護的架構。

---

# 起點：`main.go` 的問題

<details>
<summary>點此展開原始 <code>main.go</code> 程式碼</summary>

```go
package main

import (
    "bufio"
    "encoding/json"
    "fmt"
    "html"
    "image"
    "image/draw"
    "image/png"
    "io/ioutil"
    "log"
    "net/http"
    "os"
    "path/filepath"
    "sort"
    "strings"
    "time"

    "github.com/PuerkitoBio/goquery"
    "github.com/disintegration/imaging"
)

type Page struct {
    Src    string `json:"src"`
    Width  int    `json:"width"`
    Height int    `json:"height"`
}

type Cookie struct {
    Domain         string  `json:"domain"`
    ExpirationDate float64 `json:"expirationDate"`
    HostOnly       bool    `json:"hostOnly"`
    HTTPOnly       bool    `json:"httpOnly"`
    Name           string  `json:"name"`
    Path           string  `json:"path"`
    SameSite       string  `json:"sameSite"`
    Secure         bool    `json:"secure"`
    Session        bool    `json:"session"`
    StoreID        string  `json:"storeId"`
    Value          string  `json:"value"`
}

func main() {
    fmt.Println("Comic Days Manga Downloader and Deobfuscator")
    fmt.Println("============================================")

    fmt.Println("\nStage 1: Initialization")
    fmt.Println("- This stage prepares the environment and retrieves manga information.")

    cookies := loadCookies("cookie.json")

    fmt.Print("Please enter a manga link from comic-days website: ")
    reader := bufio.NewReader(os.Stdin)
    url, _ := reader.ReadString('\n')
    url = strings.TrimSpace(url)

    client := &http.Client{}
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        log.Fatal("Error creating request:", err)
    }

    for _, cookie := range cookies {
        req.AddCookie(&http.Cookie{
            Name:  cookie.Name,
            Value: cookie.Value,
        })
    }

    resp, err := client.Do(req)
    if err != nil {
        log.Fatal("Error fetching the webpage:", err)
    }
    defer resp.Body.Close()

    doc, err := goquery.NewDocumentFromReader(resp.Body)
    if err != nil {
        log.Fatal("Error parsing the webpage:", err)
    }

    jsonData, exists := doc.Find("#episode-json").Attr("data-value")
    if !exists {
        log.Fatal("Could not find episode data on the page")
    }
    jsonData = html.UnescapeString(jsonData)

    var data map[string]interface{}
    if err := json.Unmarshal([]byte(jsonData), &data); err != nil {
        log.Fatal("Error parsing JSON data:", err)
    }

    pages := data["readableProduct"].(map[string]interface{})["pageStructure"].(map[string]interface{})["pages"].([]interface{})

    var validPages []Page
    for _, p := range pages {
        page := p.(map[string]interface{})
        if src, ok := page["src"].(string); ok && src != "" {
            validPages = append(validPages, Page{
                Src:    src,
                Width:  int(page["width"].(float64)),
                Height: int(page["height"].(float64)),
            })
        }
    }

    sort.Slice(validPages, func(i, j int) bool {
        return validPages[i].Src < validPages[j].Src
    })

    fmt.Printf("- Found %d pages\n", len(validPages))

    filesDir := filepath.Join(".", time.Now().Format("2006-01-02-15-04-05"))
    os.MkdirAll(filesDir, os.ModePerm)
    fmt.Printf("- Created directory for saving images: %s\n", filesDir)

    fmt.Println("\nStage 2: Downloading and Deobfuscating Pages")
    fmt.Println("- This stage downloads, deobfuscates, and saves each page of the manga.")

    for i, page := range validPages {
        pageNum := i + 1
        fmt.Printf("\nProcessing page %d of %d\n", pageNum, len(validPages))

        img := downloadPage(pageNum, page, cookies)
        if img == nil {
            fmt.Printf("Skipping page %d due to download error\n", pageNum)
            continue
        }

        deobfuscateAndSavePage(pageNum, page, img, filesDir)
    }

    fmt.Println("\nStage 3: Completion")
    fmt.Println("- All pages have been processed and saved.")
    fmt.Printf("- You can find the downloaded manga in the directory: %s\n", filesDir)
}

func loadCookies(filename string) []Cookie {
    file, err := os.Open(filename)
    if err != nil {
        fmt.Printf("Warning: Could not open cookie file: %v\n", err)
        return nil
    }
    defer file.Close()

    bytes, err := ioutil.ReadAll(file)
    if err != nil {
        fmt.Printf("Warning: Could not read cookie file: %v\n", err)
        return nil
    }

    var cookies []Cookie
    if err := json.Unmarshal(bytes, &cookies); err != nil {
        fmt.Printf("Warning: Could not parse cookie file: %v\n", err)
        return nil
    }

    fmt.Println("Successfully loaded cookies from file.")
    return cookies
}

func downloadPage(pageNum int, page Page, cookies []Cookie) image.Image {
    fmt.Printf("Downloading page %d...\n", pageNum)

    client := &http.Client{}
    req, err := http.NewRequest("GET", page.Src, nil)
    if err != nil {
        log.Printf("Error creating request for page %d: %v", pageNum, err)
        return nil
    }

    req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    req.Header.Set("Referer", "https://comic-days.com/")

    for _, cookie := range cookies {
        req.AddCookie(&http.Cookie{
            Name:  cookie.Name,
            Value: cookie.Value,
        })
    }

    resp, err := client.Do(req)
    if err != nil {
        log.Printf("Error downloading image for page %d: %v", pageNum, err)
        return nil
    }
    defer resp.Body.Close()

    img, err := imaging.Decode(resp.Body)
    if err != nil {
        log.Printf("Error decoding image for page %d: %v", pageNum, err)
        return nil
    }

    fmt.Printf("Page %d downloaded successfully.\n", pageNum)
    return img
}

func deobfuscateAndSavePage(pageNum int, page Page, img image.Image, filesDir string) {
    fmt.Printf("Deobfuscating page %d...\n", pageNum)

    filePath := filepath.Join(filesDir, fmt.Sprintf("%03d.png", pageNum))

    spacingWidth := (page.Width / 32) * 8
    spacingHeight := (page.Height / 32) * 8

    newImg := image.NewRGBA(image.Rect(0, 0, page.Width, page.Height))

    for x := 0; x+spacingWidth <= page.Width; x += spacingWidth {
        for y := (x / spacingWidth) * spacingHeight + spacingHeight; y+spacingHeight <= page.Height; y += spacingHeight {
            oldRect := image.Rect(x, y, x+spacingWidth, y+spacingHeight)
            newPosX := (y / spacingHeight) * spacingWidth
            newPosY := (x / spacingWidth) * spacingHeight
            newRect := image.Rect(newPosX, newPosY, newPosX+spacingWidth, newPosY+spacingHeight)

            draw.Draw(newImg, oldRect, img, newRect.Min, draw.Src)
            draw.Draw(newImg, newRect, img, oldRect.Min, draw.Src)
        }
    }

    for i := 0; i < 4; i++ {
        midLineX := i * spacingWidth
        midLineY := i * spacingHeight
        midRect := image.Rect(midLineX, midLineY, midLineX+spacingWidth, midLineY+spacingHeight)
        draw.Draw(newImg, midRect, img, midRect.Min, draw.Src)
    }

    rightTransparentWidth := detectTransparentStripWidth(newImg)
    fmt.Printf("Detected transparent right strip width for page %d: %d pixels\n", pageNum, rightTransparentWidth)

    if rightTransparentWidth > 0 {
        sourceRect := image.Rect(page.Width-rightTransparentWidth, 0, page.Width, page.Height)
        destRect := sourceRect
        draw.Draw(newImg, destRect, img, sourceRect.Min, draw.Src)
    }

    outFile, err := os.Create(filePath)
    if err != nil {
        log.Printf("Error creating file for page %d: %v", pageNum, err)
        return
    }
    defer outFile.Close()

    png.Encode(outFile, newImg)

    fmt.Printf("Page %d deobfuscated and saved.\n", pageNum)
}

func detectTransparentStripWidth(img image.Image) int {
    bounds := img.Bounds()
    width := bounds.Dx()
    height := bounds.Dy()

    maxTransparentWidth := 0

    for x := width - 1; x >= 0; x-- {
        isTransparentColumn := true
        for y := 0; y < height; y++ {
            _, _, _, alpha := img.At(x, y).RGBA()
            if alpha != 0 {
                isTransparentColumn = false
                break
            }
        }
        if isTransparentColumn {
            maxTransparentWidth++
        } else {
            break
        }
    }
    return maxTransparentWidth
}

```

</details>

## 問題分析

1. **違反 SRP（單一職責原則）**：`main()`、`downloadPage()` 同時處理 I/O、邏輯、解析、圖像處理等多個責任。
1. **違反 OCP（開放封閉原則）**：若要替換圖片處理邏輯或改變輸出格式，需要直接修改主邏輯。
1. **其他原則如 DIP/ISP/LSP 也未被遵守，因為程式碼間高度耦合。**

---

# 重構步驟一：抽出 Cookie 載入（SRP）

## 變更內容

建立 `cookie.go`，定義 cookie 的結構與載入行為。

## 語法範例

```go
// cookie.go
type Cookie struct {
    Name  string `json:"name"`
    Value string `json:"value"`
    // 其餘欄位略
}

type CookieLoader interface {
    Load() ([]Cookie, error)
}

type FileCookieLoader struct {
    Filename string
}

func NewFileCookieLoader(filename string) FileCookieLoader {
    return FileCookieLoader{Filename: filename}
}

func (f FileCookieLoader) Load() ([]Cookie, error) {
    // 載入邏輯
}
```

---

# 重構步驟二：建立 ComicSession 封裝初始化（SRP + DIP）

## 變更內容

新增 `comicsession.go`，將初始化流程中與使用者互動、HTML 抓取、JSON 解析與輸出目錄建立等行為封裝成 `ComicSession` 結構，讓主程式的 `main()` 不再同時負責這些低階處理，符合 **單一職責原則（SRP）**。

此外，我們也為 cookie 載入行為定義了 `CookieLoader` 介面，這是一個朝向 **依賴反轉原則（DIP）** 的設計。雖然目前 `ComicSession` 仍直接使用 `FileCookieLoader`，尚未以介面注入方式實作，但這樣的設計已預留抽象化的彈性。未來若有第二種 cookie 載入來源（例如遠端 API 或資料庫），可無痛轉換為介面導向架構，而無需更動主邏輯。

我們也選擇保留與原始程式碼相同的呼叫方式：

```go
cookies := loadCookies("cookie.json")
```

以利程式邏輯保持簡潔，避免在尚未出現多種實作時過度設計。整體而言，這是一種 **尚未完全實作但已導入抽象邊界的 DIP 設計策略**。

## 語法範例

```go
type ComicSession struct {
    Cookies []Cookie
    URL     string
    Pages   []Page
    OutDir  string
    // 其他欄位略
}

func NewComicSession(cookieFile string) (*ComicSession, error) {
    cookies := NewFileCookieLoader(cookieFile).Load()
    // 抓取 HTML、解析頁面、建立輸出目錄等
}
```

---

# 重構步驟三：封裝單頁處理行為（SRP + LSP）

## 變更內容

建立 `page.go`，讓 `Page` 自己負責下載與處理圖像，並將與頁面相關的行為封裝成方法。

這不僅符合 **SRP（單一職責原則）**，也為實現 **LSP（里氏替換原則）** 打下基礎。具體來說，這些方法定義了一組穩定的行為介面，未來若新增其他頁面來源（如 `ZipPage`、`EncryptedPage` 等），只要實作相同行為，就可以被原流程安全替代，無需修改主邏輯。

換句話說，這使得不同型別的頁面物件能夠 **在使用端被替換使用而不影響功能正確性**，這正是 LSP 的核心精神。

## 語法範例

```go
type Page struct {
    Src    string
    Width  int
    Height int
}

func (p Page) Download(cookies []Cookie, pageNum int) (image.Image, error) {
    // HTTP 請求與解碼
}

func (p Page) DeobfuscateAndSave(img image.Image, outDir string, pageNum int) error {
    // 呼叫 ImageProcessor
}
```

若未來我們將 `Page` 抽象為介面：

```go
type PageProcessor interface {
    Download(cookies []Cookie, pageNum int) (image.Image, error)
    DeobfuscateAndSave(img image.Image, outDir string, pageNum int) error
}
```

則無論是 `Page`、`ZipPage` 還是 `EncryptedPage`，只要實作該介面，都可被主程式替代使用，這就是 LSP 在 Go 語言中的實踐方式。

---

# 重構步驟四：抽出圖片處理邏輯（SRP + ISP）

## 變更內容

建立 `imageprocessor.go`，將圖片解碼、透明條處理與儲存等邏輯從 `Page` 中拆出，讓圖片處理責任集中，符合單一職責原則（SRP）。

此外，這樣的結構也為未來的擴充留下空間——如果有其他模組也需要處理圖像，就可以進一步將這些功能抽離為更小的介面（如 `Deobfuscator`、`ImageSaver` 等），讓各模組只依賴自己需要的方法，符合介面隔離原則（ISP）。雖然目前尚未定義介面，但這樣的設計 **為後續演進預留了彈性**。

## 語法範例

```go
type ImageProcessor struct {
    Src image.Image
    Dst *image.RGBA
}

func (ip *ImageProcessor) Deobfuscate(width, height int) *image.RGBA
func (ip *ImageProcessor) DetectTransparentStripWidth() int
func (ip *ImageProcessor) RestoreRightTransparentStrip(width, height, stripWidth int)
func (ip *ImageProcessor) SaveImage(filePath string) error
```

---

# 重構步驟五：簡化主程式入口（SRP）

## 變更內容

重寫 `main.go`，僅負責流程控制與呼叫。

## 語法範例

```go
func main() {
    session, _ := NewComicSession("cookie.json")
    for i, page := range session.Pages {
        img, _ := page.Download(session.Cookies, i+1)
        page.DeobfuscateAndSave(img, session.OutDir, i+1)
    }
}
```

---

# 小結：SOLID 原則落實對照表

| 原則  | 重構實例                                | 實現方式              |
| --- | ----------------------------------- | ----------------- |
| SRP | `Page`/`ImageProcessor` 等各司其職        | 每個 struct 專責一類行為  |
| OCP | 支援不同 `CookieLoader` 實作                | 介面設計 + 擴充性模組      |
| LSP | `Page` 方法適用於所有來源                    | 可以未來加上 zip source |
| ISP | `ImageProcessor` 暴露精簡方法             | 無須實作用不到的方法        |
| DIP | `ComicSession` 依賴 `CookieLoader` 介面 | 依賴抽象而非具體實作        |

---

# 延伸練習建議

* 嘗試改寫輸出格式為 PDF，檢查 OCP 落實程度。
* 加入單元測試，驗證是否符合 LSP。
* 改用多執行緒處理圖片，並觀察是否需要再進一步拆分責任。

---

# 完整重構程式碼附錄

以下為重構後的主要程式檔案：

<details>
<summary>main.go</summary>

```go
package main

import (
 "fmt"
 "log"
)

func main() {
 fmt.Println("Comic Days Manga Downloader and Deobfuscator")
 fmt.Println("============================================")

 fmt.Println("\nStage 1: Initialization")
 fmt.Println("- This stage prepares the environment and retrieves manga information.")

 session, err := NewComicSession("cookie.json")
 if err != nil {
  log.Fatal(err)
 }

 fmt.Println("\nStage 2: Downloading and Deobfuscating Pages")
 fmt.Println("- This stage downloads, deobfuscates, and saves each page of the manga.")

 for i, page := range session.Pages {
  pageNum := i + 1
  fmt.Printf("\nProcessing page %d of %d\n", pageNum, len(session.Pages))

  img, err := page.Download(session.Cookies, pageNum)
  if err != nil {
   log.Printf("Warning: %v", err)
  }
  if img == nil {
   continue
  }

  err = page.DeobfuscateAndSave(img, session.OutDir, pageNum)
  if err != nil {
   log.Printf("Warning: %v", err)
  }
 }

 fmt.Println("\nStage 3: Completion")
 fmt.Println("- All pages have been processed and saved.")
 fmt.Printf("- You can find the downloaded manga in the directory: %s\n", session.OutDir)
}

```

</details>

<details>
<summary>cookie.go</summary>

```go
package main

import (
 "encoding/json"
 "fmt"
 "io"
 "os"
)

type Cookie struct {
 Domain         string  `json:"domain"`
 ExpirationDate float64 `json:"expirationDate"`
 HostOnly       bool    `json:"hostOnly"`
 HTTPOnly       bool    `json:"httpOnly"`
 Name           string  `json:"name"`
 Path           string  `json:"path"`
 SameSite       string  `json:"sameSite"`
 Secure         bool    `json:"secure"`
 Session        bool    `json:"session"`
 StoreID        string  `json:"storeId"`
 Value          string  `json:"value"`
}

type CookieLoader interface {
 Load() ([]Cookie, error)
}

type FileCookieLoader struct {
 Filename string
}

func NewFileCookieLoader(filename string) FileCookieLoader {
 return FileCookieLoader{Filename: filename}
}

func (f FileCookieLoader) Load() ([]Cookie, error) {
 file, err := os.Open(f.Filename)
 if err != nil {
  return nil, fmt.Errorf("could not open cookie file: %v", err)
 }
 defer file.Close()

 bytes, err := io.ReadAll(file)
 if err != nil {
  return nil, fmt.Errorf("could not read cookie file: %v", err)
 }

 var cookies []Cookie
 if err := json.Unmarshal(bytes, &cookies); err != nil {
  return nil, fmt.Errorf("could not parse cookie file: %v", err)
 }

 return cookies, nil
}

```

</details>

<details>
<summary>comicsession.go</summary>

```go
package main

import (
 "bufio"
 "encoding/json"
 "fmt"
 "html"
 "log"
 "net/http"
 "os"
 "path/filepath"
 "sort"
 "strings"
 "time"

 "github.com/PuerkitoBio/goquery"
)

type ComicSession struct {
 Cookies []Cookie
 Client  *http.Client
 URL     string
 Doc     *goquery.Document
 Pages   []Page
 OutDir  string
}

func NewComicSession(cookieFile string) (*ComicSession, error) {
 cookies, err := NewFileCookieLoader(cookieFile).Load()
 if err != nil {
  log.Printf("Warning: %v", err)
  // 可選：若沒有 cookie 也可繼續，但你也可以選擇中止
 }

 url, err := readComicDaysURL()
 if err != nil {
  return nil, err
 }

 client := &http.Client{}
 doc, err := fetchComicHTML(url, cookies, client)
 if err != nil {
  return nil, err
 }

 jsonData, err := extractEpisodeJSON(doc)
 if err != nil {
  return nil, err
 }

 pages, err := parsePages(jsonData)
 if err != nil {
  return nil, err
 }

 outDir, err := createOutputDir()
 if err != nil {
  return nil, err
 }

 return &ComicSession{
  Cookies: cookies,
  Client:  client,
  URL:     url,
  Doc:     doc,
  Pages:   pages,
  OutDir:  outDir,
 }, nil
}

func readComicDaysURL() (string, error) {
 fmt.Print("Please enter a manga link from comic-days website: ")
 reader := bufio.NewReader(os.Stdin)
 url, err := reader.ReadString('\n')
 return strings.TrimSpace(url), err
}

func fetchComicHTML(url string, cookies []Cookie, client *http.Client) (*goquery.Document, error) {
 req, err := http.NewRequest("GET", url, nil)
 if err != nil {
  return nil, fmt.Errorf("error creating request: %v", err)
 }

 for _, cookie := range cookies {
  req.AddCookie(&http.Cookie{
   Name:  cookie.Name,
   Value: cookie.Value,
  })
 }

 resp, err := client.Do(req)
 if err != nil {
  return nil, fmt.Errorf("error fetching the webpage: %v", err)
 }
 defer resp.Body.Close()

 doc, err := goquery.NewDocumentFromReader(resp.Body)
 if err != nil {
  return nil, fmt.Errorf("error parsing the webpage: %v", err)
 }

 return doc, nil
}

func extractEpisodeJSON(doc *goquery.Document) (string, error) {
 jsonData, exists := doc.Find("#episode-json").Attr("data-value")
 if !exists {
  return "", fmt.Errorf("could not find episode data on the page")
 }
 jsonData = html.UnescapeString(jsonData)
 if jsonData == "" {
  return "", fmt.Errorf("episode data is empty")
 }
 return jsonData, nil
}

func parsePages(jsonData string) ([]Page, error) {
 var data map[string]interface{}
 if err := json.Unmarshal([]byte(jsonData), &data); err != nil {
  return nil, fmt.Errorf("error parsing JSON data: %v", err)
 }

 readableProduct, ok := data["readableProduct"].(map[string]interface{})
 if !ok {
  return nil, fmt.Errorf("invalid JSON structure: missing readableProduct")
 }
 pageStructure, ok := readableProduct["pageStructure"].(map[string]interface{})
 if !ok {
  return nil, fmt.Errorf("invalid JSON structure: missing pageStructure")
 }
 pages, ok := pageStructure["pages"].([]interface{})
 if !ok {
  return nil, fmt.Errorf("invalid JSON structure: missing pages")
 }

 var validPages []Page
 for _, p := range pages {
  page, ok := p.(map[string]interface{})
  if !ok {
   continue
  }
  src, ok := page["src"].(string)
  width, okW := page["width"].(float64)
  height, okH := page["height"].(float64)
  if ok && okW && okH && src != "" {
   validPages = append(validPages, NewPage(
    src,
    int(width),
    int(height),
   ))
  }
 }

 sort.Slice(validPages, func(i, j int) bool {
  return validPages[i].Src < validPages[j].Src
 })

 return validPages, nil
}

func createOutputDir() (string, error) {
 dir := filepath.Join(".", time.Now().Format("2006-01-02-15-04-05"))
 err := os.MkdirAll(dir, os.ModePerm)
 if err != nil {
  return "", fmt.Errorf("failed to create output directory: %v", err)
 }
 return dir, nil
}

```

</details>

<details>
<summary>page.go</summary>

```go
package main

import (
 "fmt"
 "image"
 "net/http"
 "path/filepath"

 "github.com/disintegration/imaging"
)

type Page struct {
 Src    string `json:"src"`
 Width  int    `json:"width"`
 Height int    `json:"height"`
}

func NewPage(src string, width, height int) Page {
 return Page{
  Src:    src,
  Width:  width,
  Height: height,
 }
}

func (p Page) Download(cookies []Cookie, pageNum int) (image.Image, error) {
 fmt.Printf("Downloading page %d...\n", pageNum)

 client := &http.Client{}
 req, err := http.NewRequest("GET", p.Src, nil)
 if err != nil {
  return nil, fmt.Errorf("error creating request for page %d: %v", pageNum, err)
 }

 req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
 req.Header.Set("Referer", "https://comic-days.com/")

 for _, cookie := range cookies {
  req.AddCookie(&http.Cookie{
   Name:  cookie.Name,
   Value: cookie.Value,
  })
 }

 resp, err := client.Do(req)
 if err != nil {
  return nil, fmt.Errorf("error downloading image for page %d: %v", pageNum, err)
 }
 defer resp.Body.Close()

 img, err := imaging.Decode(resp.Body)
 if err != nil {
  return nil, fmt.Errorf("error decoding image for page %d: %v", pageNum, err)
 }

 if img == nil {
  return nil, fmt.Errorf("skipping page %d due to download error", pageNum)
 }

 fmt.Printf("Page %d downloaded successfully.\n", pageNum)
 return img, nil
}

func (p Page) DeobfuscateAndSave(img image.Image, outDir string, pageNum int) error {
 fmt.Printf("Deobfuscating page %d...\n", pageNum)

 filePath := filepath.Join(outDir, fmt.Sprintf("%03d.png", pageNum))
 imageCtx := NewImageContext(img)
 imageCtx.Deobfuscate(p.Width, p.Height)
 rightTransparentWidth := imageCtx.DetectTransparentStripWidth()
 fmt.Printf("Detected transparent right strip width for page %d: %d pixels\n", pageNum, rightTransparentWidth)

 imageCtx.RestoreRightTransparentStrip(p.Width, p.Height, rightTransparentWidth)

 err := imageCtx.SaveImage(filePath)
 if err != nil {
  return fmt.Errorf("error creating file for page %d: %v", pageNum, err)
 }

 fmt.Printf("Page %d deobfuscated and saved.\n", pageNum)
 return nil
}

```

</details>

<details>
<summary>imageprocessor.go</summary>

```go
package main

import (
 "image"
 "image/draw"
 "image/png"
 "os"
)

type ImageProcessor struct {
 Src image.Image
 Dst *image.RGBA
}

func NewImageContext(src image.Image) *ImageProcessor {
 return &ImageProcessor{
  Src: src,
  Dst: nil,
 }
}

func (ip *ImageProcessor) Deobfuscate(width, height int) *image.RGBA {
 spacingWidth := (width / 32) * 8
 spacingHeight := (height / 32) * 8

 ip.Dst = image.NewRGBA(image.Rect(0, 0, width, height))

 for x := 0; x+spacingWidth <= width; x += spacingWidth {
  for y := (x/spacingWidth)*spacingHeight + spacingHeight; y+spacingHeight <= height; y += spacingHeight {
   oldRect := image.Rect(x, y, x+spacingWidth, y+spacingHeight)
   newPosX := (y / spacingHeight) * spacingWidth
   newPosY := (x / spacingWidth) * spacingHeight
   newRect := image.Rect(newPosX, newPosY, newPosX+spacingWidth, newPosY+spacingHeight)

   draw.Draw(ip.Dst, oldRect, ip.Src, newRect.Min, draw.Src)
   draw.Draw(ip.Dst, newRect, ip.Src, oldRect.Min, draw.Src)
  }
 }

 for i := 0; i < 4; i++ {
  midLineX := i * spacingWidth
  midLineY := i * spacingHeight
  midRect := image.Rect(midLineX, midLineY, midLineX+spacingWidth, midLineY+spacingHeight)
  draw.Draw(ip.Dst, midRect, ip.Src, midRect.Min, draw.Src)
 }

 return ip.Dst
}

func (ip *ImageProcessor) SaveImage(filePath string) error {
 outFile, err := os.Create(filePath)
 if err != nil {
  return err
 }
 defer outFile.Close()
 return png.Encode(outFile, ip.Dst)
}

func (ip *ImageProcessor) RestoreRightTransparentStrip(width, height, stripWidth int) {
 if stripWidth <= 0 {
  return
 }
 sourceRect := image.Rect(width-stripWidth, 0, width, height)
 destRect := sourceRect
 draw.Draw(ip.Dst, destRect, ip.Src, sourceRect.Min, draw.Src)
}

func (ip *ImageProcessor) DetectTransparentStripWidth() int {
 bounds := ip.Dst.Bounds()
 width := bounds.Dx()
 height := bounds.Dy()

 maxTransparentWidth := 0

 for x := width - 1; x >= 0; x-- {
  isTransparentColumn := true
  for y := 0; y < height; y++ {
   _, _, _, alpha := ip.Dst.At(x, y).RGBA()
   if alpha != 0 {
    isTransparentColumn = false
    break
   }
  }
  if isTransparentColumn {
   maxTransparentWidth++
  } else {
   break
  }
 }
 return maxTransparentWidth
}

```

</details>

# 最終重構成果

我們可以在這個 Merged Pull Request (PR) [#1](https://github.com/MrShitFox/ComicDaysGoDownloader/pull/1/files) 看到最終成品。
