+++
title = "Synology 的 Container Manager 出現 標籤為 `<none>` 的映像檔時，該如何查詢與清理？"
slug = "synology-docker-none-images-cleanup"
date = 2026-10-24

[taxonomies]
tags = ["docker", "Synology"]
authors = ["王冠倫"]
+++

在 Synology NAS 的 Container Manager 應用程式查看映像檔頁面時，有時會看到部分映像檔的「標籤」顯示為 `<none>`。此時，該映像檔並不見得是正在被某些容器引用，而是單純由於過去更新映像檔或重新建置程式後，原本的標籤可能轉移到新版本，舊映像檔便留所導致。倘若使用者嘗試對該映像檔點擊「刪除」按鈕或是使用「未使用映像檔」按鈕來進行移除時，會發現無法正常移除。在這種情況下，我們可能就需要使用 SSH 登入來進行手動操作，以此清除這些殘留的映像檔——僅限於具備管理員權限的帳號才得以執行此操作 [^1]。

## 一、列出目前的映像檔

在 Synology 常見的預設權限設定下，執行 Docker 指令需要加上 `sudo`，以取得存取 Docker 服務所需的權限。因此，本文統一使用 `sudo docker ...`。若出現密碼提示，請輸入目前登入 NAS 的帳號密碼——於終端機輸入密碼時不顯示字元是正常現象，切莫驚慌。

除了 Container Manager 應用程式映像檔頁面所顯示的映像檔清單之外，實際上還可能有更多的映像檔存在。我們可以使用以下指令列出目前 NAS 上的所有映像檔，並且查看每個映像檔的名稱、標籤、映像檔 ID、建立時間與大小：

```bash
sudo docker images
```

上該指令的輸出可能像這樣：

```text
REPOSITORY             TAG       IMAGE ID       CREATED       SIZE
linuxserver/freshrss    latest    3cde83130d3e   9 hours ago   117MB
<none>                 <none>    33bde938ab3e   38 hours ago  1.98GB
gotson/komga            <none>    3ce1ec113eba   3 weeks ago   483MB
python                 <none>    691aea61c5aa   8 weeks ago   1.12GB
```

關於上述表格的各個欄位的說明如下：

| 欄位 | 用途說明 |
| --- | --- |
| `REPOSITORY` | 映像檔的儲存庫名稱，例如 `python`、`gotson/komga`。 |
| `TAG` | 映像檔標籤，例如 `latest` 或版本號碼。 |
| `IMAGE ID` | 映像檔識別碼，後續可用它查詢引用容器或移除映像檔。 |
| `CREATED` | 映像檔建立至今的時間，不是下載到 NAS 的時間。 |
| `SIZE` | 映像檔及其所含各層的大小。不同映像檔可能共享層，不能直接相加當作可回收空間。 |

我們可以觀察到當 `REPOSITORY` 為 `<none>` 的項目，並不會於Container Manager 應用程式映像檔頁面所顯示。通常當某個映像檔的 `REPOSITORY` 值和 `TAG` 值都是 `<none>` 時，是因為更新或重新建置後留下的。若只有 `TAG` 是 `<none>`，則不一定；可能是透過 digest（內容摘要識別碼）保留的映像檔 [^2]，不能單憑這個欄位判定是否可刪除。

## 二、清理符合條件的懸空映像檔

我們可以從上一小節的內容中知道 **`<none>` 不等於「未被使用」**，它只表示對應欄位沒有名稱或標籤，仍可能有容器引用該映像檔。因此，正確的處理方式是列出映像檔後，根據符合條件的映像檔進行初步清理；最後再查詢剩餘映像檔是否有容器使用，手動進行個別移除。以下為初步清理的對應指令，他會清理被 Docker 判定為 dangling（懸空），且沒有被任何容器引用的映像檔：

```bash
sudo docker image prune
```

執行後會出現確認提示：

```text
WARNING! This will remove all dangling images.
Are you sure you want to continue? [y/N]
```

確認要清理後，輸入 `y` 並按 Enter 即可。Docker 會列出清理結果，最後顯示 `Total reclaimed space`，代表這次實際釋放的空間。這個指令會保留執行中或已停止容器仍引用的映像檔，也不會刪除容器、資料卷或掛載資料夾。不過，若有需要保留的本地建置成果或回退版本，應先加上標籤或備份，再進行清理。

## 三、查詢是哪個容器使用映像檔

執行完上一節的述指令後，我們可以確認清理後還有哪些映像檔：

```bash
sudo docker images
```

此時可能仍有 `REPOSITORY` 值和 `TAG` 值都是 `<none>` 的映像檔存在，這並不代表該映像檔一定正在使用；藉由將下述指令中的 `xxxx` 換成上一個指令所看到的 `IMAGE ID` 可接著查詢容器的引用狀況，找出使用指定映像檔，或使用其衍生映像檔的容器，並以表格列出容器 ID、名稱、映像檔及狀態：

```bash
sudo docker ps -a --filter ancestor=xxxx --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
```

關於上述指令中的各個指令或參數的說明如下：

| 指令或參數 | 用途說明 |
| --- | --- |
| `sudo` | 以提升的權限執行指令。 |
| `docker ps` | 列出容器。 |
| `-a` | 包含所有狀態的容器，尤其是已停止但尚未移除的容器。 |
| `--filter ancestor=xxxx` | 篩選使用指定映像檔或其衍生映像檔的容器。 |
| `--format "table ..."` | 指定表格欄位；`{{.ID}}`、`{{.Names}}`、`{{.Image}}`、`{{.Status}}` 分別是容器 ID、名稱、映像檔與狀態，`\t` 用來分隔欄位。 |

例如，查詢前面清單中的 Python：

```bash
# 查詢 Python 映像檔的引用容器
sudo docker ps -a --filter ancestor=691aea61c5aa --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
```

查詢結果中的 `NAMES` 是容器名稱，`STATUS` 則顯示目前狀態。`Up` 表示正在執行，`Exited` 表示已停止；已停止的容器仍可能引用映像檔。

如果只有以下表頭而沒有任何資料列，則表示目前查詢的 Docker 服務中，沒有找到符合條件的容器：

```text
CONTAINER ID   NAMES   IMAGE   STATUS
```

若有查到結果，則應先確認該容器的用途；由於 `ancestor` 也會匹配衍生映像檔，結果不一定全部直接使用同一個 `IMAGE ID`。

## 四、個別移除不再需要的映像檔

可以將下述指令中的 `xxxx` 換成 `IMAGE ID` 來移除經上一節指令確認不再需要的映像檔：

```bash
sudo docker rmi xxxx
```

上述指令中的 `docker rmi` 等同於 `docker image rm`，與用來移除容器的 `docker rm` 不同例如，且可以一次指定兩個 ID。範例如下：

```bash
sudo docker rmi 691aea61c5aa 3ce1ec113eba
```

我們可以於最後執行以下第一節所提出的指令，確認目標映像檔已從清單中移除：

```bash
sudo docker images
```

# 參考資料

[^1]: [Synology (2025, 1, 6)。如何使用 RSA 金鑰組以 SSH 的方式登入 DSM？Synology 知識中心](https://archive.ph/ec58J)
[^2]: [Docker Inc. docker image ls. Docker docs](https://web.archive.org/web/20261025082315/https://docs.docker.com/reference/cli/docker/image/ls/)
