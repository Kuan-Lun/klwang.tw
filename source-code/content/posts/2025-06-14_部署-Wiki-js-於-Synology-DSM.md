+++
title = "解決權限問題：以 LinuxServer.io 在 Synology DSM 上部署 Wiki.js"
slug = "wikijs-linuxserverio-synologydsm"
date = 2025-06-14

[taxonomies]
tags = ["Wiki.js", "docker", "linuxserver.io", "Synology"]
authors = ["王冠倫"]
+++

在上一篇[文章](/posts/choose-wikijs-for-selfhosted-knowledge-base/)中已說明[選擇標準](/posts/choose-wikijs-for-selfhosted-knowledge-base/#xuan-ze-biao-zhun)，並分析為何 Wiki.js 相較於 BookStack、DokuWiki 等知識庫系統更符合需求。本篇將說明如何在 **Synology DSM 環境**（即 Synology NAS 的作業系統）中透過 Docker Compose 部署 Wiki.js，並說明為何選用 **[LinuxServer.io 映像](https://hub.docker.com/r/linuxserver/wikijs)與 PostgreSQL 資料庫**，以解決 [Wiki.js 官方映像 `ghcr.io/requarks/wiki`](https://hub.docker.com/r/requarks/wiki) 在 Synology DSM 上常見的**權限錯誤問題**。

# 為什麼使用 Docker 安裝？

[Wiki.js 官方文件](https://docs.requarks.io/install/docker)明確推薦使用 **Docker** 來部署 Wiki.js，並提供完整的範例與支援。這是目前最穩定、最簡化的部署方式，尤其適合在 Synology DSM、Ubuntu Server 或其他 Linux 容器化環境中使用。

在此選擇 Docker 的原因如下：

* 官方首選方案：更新順暢、社群活躍、文件完整
* 模組化與可移植性：各服務作為獨立容器，易於移轉與管理
* 簡化安裝流程：無需手動安裝 Node.js 、資料庫與依賴
* 跨平臺部署一致性：相同設定可在 Synology DSM、VM、雲上部署
* 方便升級與維護：更新只需 pull 新映像，保留設定與資料
* 易於備份與還原：備份挂載目錄與 compose 檔即可還原

# 為什麼使用 LinuxServer.io 的 Wiki.js 映像？

使用 Wiki.js 官方映像於 Synology DSM 上執行 Docker Compose 部署時，會在進行初始化設定的過程中遭遇下列錯誤：

```bash
EACCES: permission denied, mkdir '/wiki/data/cache'
```

這意味著 Wiki.js 嘗試在容器內建立目錄時，缺乏安全定義的寫入權限——即使已經給予挂載目錄正確權限，還是會出現錯誤。這是因為 [Wiki.js 官方映像預設使用 `wiki` 使用者執行](https://docs.requarks.io/install/docker#change-user-mode)，當容器內使用者 UID 與 GID 和容器外主機目錄設定不符時，就會導致權限錯誤。而 [LinuxServer.io](https://www.linuxserver.io/) 的 [Wiki.js 映像](https://hub.docker.com/r/linuxserver/wikijs)，該版本支援 `PUID` 與 `PGID` 的環境設定，可以分別指定容器內執行用戶的 UID 與GID，確保和容器外主機目錄的設定一致，以此解決權限問題。

# 為什麼改用 PostgreSQL 資料庫？

LinuxServer.io 提供的 Wiki.js 映像預設使用 **SQLite** 作為儲存引擎，這對於單人使用或快速測試環境很方便。鑒於目標是建立一個穩定、可多人協作、具備備份策略的知識系統，故改用 **PostgreSQL** 作為資料庫。

主要原因包括：

* 更好的資料一致性與互斥處理能力
* 支援定期備份與還原操作
* [Wiki.js 官方推薦 PostgreSQL 為首選資料庫](https://docs.requarks.io/install/postgresql)

Wiki.js 支援通過環境變數（如 `DB_TYPE`, `DB_HOST`, `DB_USER` 等）指定外部資料庫類型與連線設定。無論是官方映像或 LinuxServer.io 映像，都可透過設定此類設定使 Wiki.js 連線到 PostgreSQL 容器，無須修改應用程式本身。

# 部署設定檔 `docker-compose.yml`

以下為本文使用的 `docker-compose.yml` 範例，包含 Wiki.js 與 PostgreSQL 容器的設定。請依實際環境替換 `[port]` 及各資料夾路徑。

```yml
# version: "3.8"                                # 可省略，僅為相容舊版 docker-compose 指令所用

services:
wikijs:
    image: lscr.io/linuxserver/wikijs:latest
    container_name: wikijs-wikijs
    depends_on:
    - db
    ports:
    - "[port]:3000"                             # 請自行指定主機埠號
    environment:
    - TZ=Asia/Taipei
    - PUID=1026
    - PGID=100
    - DB_TYPE=postgres
    - DB_HOST=db
    - DB_PORT=5432
    - DB_USER=wikijs
    - DB_PASS=wikijsrocks
    - DB_NAME=wikijs
    volumes:
    - /[wiki_data]:/data                        # 請替換為實際路徑
    - /[wiki_config]:/config                    # 請替換為實際路徑
    restart: unless-stopped

db:
    image: postgres:latest
    container_name: wikijs-postgres_sql
    environment:
    - POSTGRES_USER=wikijs
    - POSTGRES_PASSWORD=wikijsrocks
    - POSTGRES_DB=wikijs
    volumes:
    - /[postgres_data]:/var/lib/postgresql/data # 請替換為實際路徑
    restart: unless-stopped
```

若不熟悉如何於 Synology Container Manager 中使用 docker-compose，請參考[官方教學](https://archive.ph/IxXYj)。