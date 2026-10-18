# CHECKPOINT — News Article Cache Architecture
## 2026-10-18

### 1. Quyết định kiến trúc

Tàng Thư News Crawler không coi `ArticlePool` là bộ nhớ chỉ tồn tại trong một lần chạy.

Thay vào đó, hệ thống có một tầng **`ArticleCache` lâu dài** để tái sử dụng các bài đã crawl.

Luồng tổng quát:

```text
Bulletin Registry
      ↓
Active subscriptions
      ↓
Chỉ crawl source có người đăng ký
      ↓
Generic Discovery — tối đa 25 URL/source
      ↓
ArticleCache
   ├─ URL đã cache → dùng lại
   └─ URL mới → crawl + extract → lưu cache
      ↓
Article Pool của edition
   ├─ bài mới
   └─ bài cũ còn phù hợp từ cache
      ↓
Personal selection
      ↓
0neNews.epub
```

### 2. Tiết kiệm tài nguyên

- Source không có subscription đang hoạt động: **không discovery, không crawl, không download**.
- Với source có subscription:
  - Discovery tối đa 25 URL/source.
  - URL đã có trong `ArticleCache`: không download/extract lại.
  - Chỉ URL mới được fetch và extract.
- Các bài cũ trong cache có thể tiếp tục được sử dụng cho các edition sau nếu còn phù hợp.

### 3. Nguồn cập nhật ít

Nguồn cập nhật chậm không bị loại chỉ vì hôm đó có ít bài mới.

Ví dụ cần 10 bài:

```text
3 bài mới
+ 2 bài cache hôm qua
+ 4 bài cache hôm kia
+ 1 bài cache cũ hơn
= 10 bài
```

Như vậy chỉ 3 bài mới phải download.

### 4. Nhận diện bài

Khóa nhận diện chính:

```text
source_id + canonical_url
```

Điều này giữ nguyên quyết định trước:

- Dedup trong cùng source.
- Không dedup giữa các source.

### 5. Dữ liệu ArticleCache dự kiến

Mỗi record tối thiểu:

```text
source_id
canonical_url
title
content
excerpt
published_at
discovered_at
fetched_at
image(s)
content_mode
```

### 6. Lifecycle cache

Cache không giữ vô hạn.

Sẽ có một `retention policy` riêng để quyết định:
- bài nào còn đủ mới để đưa vào Article Pool;
- bài nào chỉ giữ trong cache;
- khi nào xóa cache cũ.

**Chưa chốt thời gian retention** (7/30/90 ngày...).

### 7. Quan hệ với Tàng thư OPDS

`Bulletin Registry` và `Subscription` trong `tangthu-opds` sẽ quyết định source nào thực sự được đưa vào daily crawl.

Crawler vẫn chịu trách nhiệm:
- discovery;
- fetch/extract;
- ArticleCache;
- ArticlePool;
- personal selection;
- EPUB.

OPDS không làm crawler, extraction hoặc EPUB building.

### 8. News delivery

`0neNews.epub` là file cố định của từng tủ sách.

Crawler upload/update file sau khi edition hoàn thành. Drive file ID được giữ nguyên.

Không cần chờ `DriveCheck` 07:12 để news trở nên khả dụng; khi upload hoàn tất, bản mới đã có thể được truy cập qua link/file ID hiện tại.

### 9. Chưa chốt

Các policy sau chưa quyết định:
- retention period của ArticleCache;
- tiêu chí chính xác để chọn bài cũ khi source thiếu bài mới;
- giới hạn tổng số bài cache;
- chiến lược cleanup cache.

### 10. Bước tiếp theo

Tiếp tục với `tangthu-opds`:

1. Bulletin Registry.
2. Subscription của từng tủ sách.
3. UI chức năng **Tin tức**.
4. Cấu hình selection/edition.
5. Sau đó nối cấu hình này vào daily crawler.

Không thiết kế lại crawler từ đầu.
