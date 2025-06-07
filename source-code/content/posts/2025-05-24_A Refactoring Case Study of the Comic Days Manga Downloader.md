+++
title = "Applying SOLID Principles: A Refactoring Case Study of the Comic Days Manga Downloader"
description = "An English-translated case study that applies SOLID principles to refactor an open-source Go manga downloader, showcasing clean architecture and design improvements."
slug = "comicdays-en"
date = "2025-05-24"

[taxonomies]
tags = ["SOLID", "重構", "設計模式", "Go"]
+++

# Preface

This article is an English translation of a [Chinese version](/posts/comicdays-zhtw/), translated using ChatGPT-4o. If you notice any errors or inaccuracies, feel free to [contact me via email](mailto:polyphonicared@gmail.com).

This case study is a refactoring of the open-source GitHub project [`ComicDaysGoDownloader`](https://github.com/MrShitFox/ComicDaysGoDownloader), based on its initial version from commit [`c219073`](https://github.com/MrShitFox/ComicDaysGoDownloader/commit/c2190734d1018c1ab421b346ccad10a475386ac0).

The original code successfully handled the downloading and decoding of manga pages. While functionally complete, it suffered from poor readability, tight coupling, and difficulty in extension and testing, making it hard to maintain or enhance.

Through this hands-on refactoring example, we demonstrate how to transform the original structure into a clean and maintainable architecture.

---

# Starting Point: Problems in `main.go`

<details>
<summary>Click to view the original <code>main.go</code> source</summary>

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

## Problem Analysis

1. **Violation of SRP (Single Responsibility Principle)**: Both `main()` and `downloadPage()` are responsible for I/O, logic, parsing, and image processing.
2. **Violation of OCP (Open-Closed Principle)**: Replacing image processing logic or changing the output format requires modifying core logic directly.
3. **Other SOLID principles (DIP/ISP/LSP)** are also violated due to the high coupling across components.

---

# Refactoring Step 1: Extract Cookie Loading (SRP)

## Changes

Created `cookie.go` to define the structure and behavior for loading cookies.

## Code Example

```go
// cookie.go
type Cookie struct {
    Name  string `json:"name"`
    Value string `json:"value"`
    // Other fields omitted
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
    // Loading logic
}
```

---

# Refactoring Step 2: Create `ComicSession` for Initialization (SRP + DIP)

## Changes

Added `comicsession.go` to encapsulate user interaction, HTML fetching, JSON parsing, and output directory setup into a `ComicSession` struct, offloading these responsibilities from `main()`. This adheres to the **Single Responsibility Principle (SRP)**.

We also introduced a `CookieLoader` interface, aiming for **Dependency Inversion Principle (DIP)**. While `ComicSession` currently uses `FileCookieLoader` directly and not via interface injection, this abstraction provides future flexibility. If a new cookie source (e.g., remote API or database) is introduced, the architecture can adopt it seamlessly without changing the core logic.

We intentionally kept the original usage pattern:

```go
cookies := loadCookies("cookie.json")
```

to avoid overengineering before multiple implementations are needed. This represents a **DIP-oriented design strategy with abstract boundaries in place**, even if not fully implemented yet.

## Code Example

```go
type ComicSession struct {
    Cookies []Cookie
    URL     string
    Pages   []Page
    OutDir  string
    // Other fields omitted
}

func NewComicSession(cookieFile string) (*ComicSession, error) {
    cookies := NewFileCookieLoader(cookieFile).Load()
    // Fetch HTML, parse pages, create output directory, etc.
}
```

---

# Refactoring Step 3: Encapsulate Page Behavior (SRP + LSP)

## Changes

Created `page.go`, allowing `Page` to handle downloading and image processing itself, with all page-related logic encapsulated in methods.

This not only satisfies the **SRP (Single Responsibility Principle)**, but also lays the groundwork for the **LSP (Liskov Substitution Principle)**. The methods define a stable behavioral interface so that if future types like `ZipPage` or `EncryptedPage` are added, they can be safely substituted in the main flow without modification.

In other words, different page types can be **used interchangeably without affecting program correctness**, which is the essence of LSP.

## Code Example

```go
type Page struct {
    Src    string
    Width  int
    Height int
}

func (p Page) Download(cookies []Cookie, pageNum int) (image.Image, error) {
    // HTTP request and decoding
}

func (p Page) DeobfuscateAndSave(img image.Image, outDir string, pageNum int) error {
    // Calls ImageProcessor
}
```

If we later abstract `Page` into an interface:

```go
type PageProcessor interface {
    Download(cookies []Cookie, pageNum int) (image.Image, error)
    DeobfuscateAndSave(img image.Image, outDir string, pageNum int) error
}
```

then `Page`, `ZipPage`, or `EncryptedPage` can all be used in the same place, illustrating LSP in Go.

---

# Refactoring Step 4: Extract Image Processing Logic (SRP + ISP)

## Changes

Created `imageprocessor.go` to move decoding, transparent-strip handling, and saving logic out of `Page`, giving image processing its own responsibility per **SRP**.

This structure also allows future extensions—if other modules need image processing, we can further break the logic into smaller interfaces like `Deobfuscator`, `ImageSaver`, etc., so that modules depend only on what they need. This aligns with the **Interface Segregation Principle (ISP)**. Although interfaces are not yet defined, the current design **reserves flexibility for future evolution**.

## Code Example

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

# Refactoring Step 5: Simplify Main Entry Point (SRP)

## Changes

Rewrote `main.go` to handle only flow control and function calls.

## Code Example

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

# Summary: SOLID Principle Mapping

| Principle | Refactoring Example                       | Implementation Approach                     |
| --------- | ----------------------------------------- | ------------------------------------------- |
| SRP       | `Page`, `ImageProcessor` with clear roles | Each struct handles a single responsibility |
| OCP       | Support for multiple `CookieLoader` types | Interface design + modularity               |
| LSP       | `Page` methods work for all page sources  | Future extensibility via shared interfaces  |
| ISP       | `ImageProcessor` with minimal public API  | Modules don't depend on unused methods      |
| DIP       | `ComicSession` depends on `CookieLoader`  | Depends on abstraction, not concretions     |

---

# Suggested Extensions

* Try changing the output format to PDF to evaluate OCP compliance.
* Add unit tests to validate LSP conformance.
* Use multithreading for image processing and assess if further SRP-based separation is needed.

---

# Full Refactored Code Appendix

The following includes the major refactored source files:

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

---

# Final Refactoring Result

We can view the complete result in the merged Pull Request (PR) [#1](https://github.com/MrShitFox/ComicDaysGoDownloader/pull/1/files).
