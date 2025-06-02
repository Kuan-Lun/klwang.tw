+++
title = "Python 初階配對交易"
slug = "ntu-pts-with-python"
weight = 99

[extra]
local_image = "/courses/ntu-pts-with-python/ntu-pts-with-python-logo.png"
+++

國立臺灣大學資訊系統訓練班[課程頁面](https://train.csie.ntu.edu.tw/train/course.php?id=3363)

# 課程簡介

> 如果失敗的成本高得無法承受
>
> 那麼某件事有多常成功一點也不重要
>
> ---[隨機騙局：潛藏在生活與市場中的機率陷阱](https://www.books.com.tw/products/0010636642)
>
> [Nassim Nicholas Taleb](https://archive.ph/Kq4NW) (譯：羅耀宗)

近 17 年 (2003 年至 2020 年 7 月) 發行量加權股價報酬指數 (俗稱：大盤還原價) 平均每年報酬率高達 9.70% (採幾何平均計算，相關資料請參閱：[臺灣證券交易所，無日期](https://archive.ph/Be8rw))。同時，臺灣證券交易參與現狀亦是十分熱絡，平均每兩名成年中就有一人開戶 ([陳昱光，民 107 年 2 月 25 日](https://archive.ph/my7xf))；不重複開戶人數高達 1,053 萬餘人，2019 年每位股民更是平均獲利 67 萬元 ([潘智義，民 108 年 12 月 31 日](https://archive.ph/V95Is))。顯而易見地，證券交易可說早已是個人理財中的基礎能力。

然證券化和信用擴張的創新、科技與投資理論所催生的新型交易策略 ([Bodie et al., 民 101](https://archive.ph/GVpP4))，與如 Covid-19 疫情難以預料的突發事件 ([經濟日報，民 109 年 6 月 26 日](https://money.udn.com/money/story/5599/4660481)) 等，致使證券市場充滿了各種快速且複雜的震盪變化，更造成發行量加權股價報酬指數的日報酬率樣本標準差高達 1.17% (2003 年至 2020 年 7 月，相關資料請參閱：[臺灣證券交易所，無日期](https://archive.ph/Be8rw))。 故本門課著重在資產配置上，利用沖銷風險為根基的配對交易 (["配對交易"，民 107](https://archive.ph/sqR0T)) 為課程主軸，將以距離方法 (distance method, 相關資料請參閱：["Pairs trade," 2020, para. #Model-based pairs trading](https://archive.ph/0XpIj)) 作為課程完成目標教學。

課程重要注意事項：(1) 此課程原為 Python 初階證券交易分析中數據分析的內容，程式設計部分已移至 Python 初階複合設計模式課程中。修習本課程學員僅須熟悉 Python 語法即可；(2) 本線上課程授課方式為提供已錄製完成的影片，無直播授課；(3) 基於法規限制 ([臺灣證券交易所，使用條款，無日期](https://archive.ph/NP1rh)與[臺灣期貨交易所，使用條款，無日期](https://archive.ph/3tWBG))，部分數據僅可使用過去已久的舊資料。(4) 結業標準採作業等權重加權後達 70 分，各作業內容與截止日期依當期課程決定。

【線上課程的課程設計為「線上錄影課程」，學員可以透過精心剪輯設計的課程影片不停地複習實作的步驟，確保可以順利完成所有的操作。也可以隨時在線上討論區或作業的討論獲得必要的協助或提示來一起學習怎麼解決實際的問題。此課程結業標準為作業等權重加權達70分。】

※線上課程上課時間：可自行安排時間上課

影片上架進度，請參考備註欄位第(三)點線上課程常見QA連結網址

# 課程大綱

| 單元     | 章節                | 提供試閱        |
|--------|-------------------|------------------------------------------------|
| 介紹     | 投資                | [是 (請點選)](https://drive.google.com/file/d/1LOJkv7-JixjemeYO1WdYWykh4HIfaX5d/preview) |
|        | 效率市場              | [是 (請點選)](https://drive.google.com/file/d/1P0TZGsBKgfRYYF-HDh13h74PoaL8SzXH/preview) |
|        | 程式交易              | [是 (請點選)](https://drive.google.com/file/d/1fJqY8rlvDox8iYGfJhCXRpk7kMCMbflR/preview) |
|        | 交易策略系統            | [是 (請點選)](https://drive.google.com/file/d/1VgpGWgWx80PL6ApYSTFHbYQW_zVbJKKG/preview) |
|        | 配對交易策略            | [是 (請點選)](https://drive.google.com/file/d/1dkO4SXULhPPWWABKyJdzPaG6zUOr2DKw/preview) |
| 還原價    | 除權息計算結果表          | 否           |
|        | 參考價               | 否           |
|        | 還原價               | 否           |
|        | 客製化還原價範例 A        | 否           |
|        | 客製化還原價範例 B        | 否           |
| 報酬     | 報酬率               | [是 (請點選)](https://drive.google.com/file/d/1J5UBL-OreNoNcpuU5Evnvobxq6TFXvci/preview) |
|        | 投資組合報酬率           | [是 (請點選)](https://drive.google.com/file/d/1pnh_h6epyXq3QzBohTOAMPNx35sCj90p/preview) |
|        | 衡量多重期間的報酬         | [是 (請點選)](https://drive.google.com/file/d/1jD2lzEFAnuaqeWmeIQRJoT_MWhTPOq5A/preview) |
|        | 風險與風險貼水           | [是 (請點選)](https://drive.google.com/file/d/1R9xVTuz78m1K-6XwDiMXIylKQTp1orM7/preview) |
| 套利定價理論 | 套利定價理論            | [是 (請點選)](https://drive.google.com/file/d/1mf1a58TsbF4mfXQnPUczKyts7kzq6Dut/preview) |
|        | 配對交易的投資組合         | 否           |
|        | 現金流與報酬            | 否           |
| 模型     | 套利定價理論下的模型猜測      | 否           |
|        | 猜測模型的具體化          | 否           |
|        | 線性迴歸              | 否           |
|        | 多變量線性迴歸           | 否           |
|        | 多變量線性迴歸的應用        | 否           |
|        | 線性迴歸與多變量線性迴歸的轉換關係 | 否           |
| 估計     | 最小平方問題            | [是 (請點選)](https://drive.google.com/file/d/1UoRLxYzOpeCNABLHFtsij6tRsOuq8PJv/preview) |
|        | 普通最小平方法估計量        | [是 (請點選)](https://drive.google.com/file/d/1qR7Zc5aISVLoinXdpOfEIRZD10OyPveL/preview) |
|        | 不偏性               | 否           |
|        | 一致性               | 否           |
|        | 最大概似估計法           | 否           |
| 相關     | 已知因子時的測量法         | [是 (請點選)](https://drive.google.com/file/d/1wmivnWRQjNaN0_TRbpxQVp1dDrApvhn4/preview) |
|        | 未知因子時的測量法         | 否           |
| 檢定     | 假設                | [是 (請點選)](https://drive.google.com/file/d/1lZhLRiFxQkLgUgqoE_rt98opJu1Z_x82/preview) |
|        | 混淆矩陣              | 否           |
|        | 單尾檢定              | 否           |
|        | 單尾檢定特性            | 否           |
|        | 雙尾檢定              | 否           |
|        | 受限最小平方估計量         | 否           |
|        | 線性檢定              | [是 (請點選)](https://drive.google.com/file/d/17Fkvkmy_J4n3weFUTyrA0p0h0RN1wH6B/preview) |
| 多重檢定   | 偏度                | 否           |
|        | 峰度                | 否           |
|        | 常態檢定              | 否           |
|        | 複檢定               | [是 (請點選)](https://drive.google.com/file/d/1lJZncTfR-US1CgBTaIq83h8CxTn67JLM/preview) |

# 學習評量

第 330 期前 (不含) 之學員，可來信索取第 330 期之學習評量參考解答。

- [330 學習評量](ntu-pts-with-python-330-pts-exam.pdf) (take home, ver. 1, updated 7/27/20)

# 備註

- 本課程以中文教材為主，但仍有部分文字語言為英文，同時教材僅部分使用。
- 本課程預計會安排程式考試一次。
- 實際授課內容需視課堂學員學習情況而定。
- 為配合當下最新 Python 版本，本課程不建議學員使用虛擬環境。
- 本課程會提供雲端硬碟供學員下載上課的程式碼，於課程結束後一週關閉。
- 本課程預計會安排之學習評量，可於課程網站中參考上期試卷題目。

# 適合對象

- 嫻熟於使用 Python 者
- 證券或相關金融商品交易經驗者
- 對線性代數與機率論基礎有所了解者

# 開發環境

| 環境              | 版本     |
|-----------------|--------|
| Python          | 3.9.7  |
| JupyterLab      | 3.1.12 |
| yfinance        | 0.1.63 |
| NumPy           | 1.21.2 |
| NumPy Financial | 1.0.0  |
| SciPy           | 1.7.1  |
| Matplotlib      | 3.4.3  |
| pandas          | 1.3.3  |
