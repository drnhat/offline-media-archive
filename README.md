# Tumblr-style Media Archive (build_archive.py v3.2)

Biến một thư mục ảnh/video thành **một file `index.html` duy nhất**, xem hoàn toàn offline theo phong cách Tumblr: cuộn dọc như dòng bài viết, hoặc lưới masonry, có xem ảnh phóng to, tìm kiếm, bộ lọc đã lưu, bài đã thích, sao lưu, icon Màn hình chính iPhone…

Không cần cài thêm gì: chỉ cần **Python 3.11 trở lên** (đọc cấu hình bằng `tomllib` có sẵn trong thư viện chuẩn, không phụ thuộc thư viện ngoài). Chạy bằng Python cũ hơn, script sẽ báo lỗi rõ ràng và dừng.

---

## 1. Bắt đầu nhanh

```
📁 Archive/
├── build_archive.py
├── config.toml
└── Images/            ← bỏ ảnh, video (và file .md ghi chú) vào đây
```

```bash
python build_archive.py          # tạo index.html cạnh script
python build_archive.py --open   # tạo xong tự mở trong trình duyệt
```

Mở `index.html` bằng bất kỳ trình duyệt hiện đại nào (Chrome, Edge, Firefox, Safari). Có thể chép cả thư mục sang USB/điện thoại; giữ nguyên vị trí tương đối giữa `index.html` và thư mục media.

> **Lưu ý:** `index.html` tham chiếu tới ảnh/video theo đường dẫn tương đối. Nếu di chuyển `index.html`, hãy build lại (hoặc di chuyển cùng thư mục media).

---

## 2. Cấu hình (`config.toml`)

Mọi tùy chọn đều có chú thích ngay trong file mẫu. Tóm tắt:

| Nhóm | Khóa | Giá trị | Mặc định |
|---|---|---|---|
| Nội dung | `title` | Tên trang | `<tên thư mục> Archive` |
| | `images_dir` | Một thư mục media | `Images` |
| | `images_dirs` | Nhiều thư mục (danh sách), hoặc `[all]` | — |
| Giao diện | `theme` | `auto` hoặc tên theme (xem bên dưới) | `mocha` |
| | `theme_light` / `theme_dark` | Theme dùng khi `theme: auto` | `latte` / `mocha` |
| | `default_view` | `feed` \| `grid` | `feed` |
| | `columns` | `0` = tự động, hoặc 1–10 | `0` |
| | `feed_width` | 480–1100 (px) | `720` |
| | `sticky_header` | `true` \| `false` | `true` |
| Thứ tự | `sort_by` | `name` \| `created` \| `created_desc` | `name` |
| Thông tin | `show_filename`, `show_created_time`, `show_file_size`, `show_dimensions` | `true` \| `false` | `false` |
| Video | `show_video_thumbnails` | Hiện khung hình đầu | `false` |
| | `video_autoplay` | Tự phát (tắt tiếng) khi cuộn tới | `false` |
| Lọc | `folder_filter_depth` | 0–10 cấp thư mục con | `1` |
| Loại trừ | `ignored_folders` | Danh sách tên/mẫu thư mục bỏ qua khi quét | `[]` |
| Icon iOS | `app_icon` | Đường dẫn file PNG làm icon Màn hình chính | tự tìm / tự vẽ |
| | `app_name` | Tên ngắn dưới icon | `title` |
| | `app_status_bar` | `black-translucent` \| `default` \| `black` | `black-translucent` |
| Build | `probe_dimensions` | Đọc kích thước ảnh lúc build | `true` |

**Theme có sẵn:** `mocha`, `frappe`, `macchiato`, `latte`, `nord`, `tokyo-night`, `gruvbox`, `rose-pine`, `noir-velvet`, `oxblood`, `nord-light`, `tokyo-night-light`, `gruvbox-light`, `rose-pine-dawn`, `dracula`, `solarized-dark`, `solarized-light`, `midnight` (đen AMOLED), `sakura`.

**Cú pháp TOML cần nhớ:**

```toml
title = "My Archive"        # chữ: đặt trong dấu ngoặc kép
sticky_header = true        # đúng/sai: viết thường, KHÔNG ngoặc kép
feed_width = 720            # số: viết trần, KHÔNG ngoặc kép
images_dir = "D:/Pictures"  # Windows: dùng dấu / hoặc nháy đơn 'D:\Pictures'
```

Nếu sai kiểu (ví dụ `columns = "3"`) hoặc file hỏng cú pháp, script báo lỗi kèm tên khóa/dòng và không build. Khóa không nhận ra chỉ bị cảnh báo và bỏ qua. Tên khóa cũ của v2 (`name`, `image_dir`, `folders`, `sort`, `layout`…) vẫn được nhận.

> **Chuyển từ `config.yml`:** phiên bản này **không còn đọc `config.yml`**. Nếu chỉ còn `config.yml`, script dừng và nhắc bạn chuyển đổi. Cách chuyển: đổi `khóa: giá trị` thành `khóa = giá trị`, đặt chữ trong ngoặc kép, đổi danh sách `images_dirs` thành mảng `[ "A", "B" ]` (xem file mẫu).

### Nhiều thư mục

```yaml
images_dirs = [
  "Images",
  "D:/Pictures/Tumblr",
  "../Backup/Memes",
]
```

Có từ 2 thư mục trở lên, mỗi bài hiện nhãn thư mục nguồn và menu **Lọc** có thêm mục chọn thư mục. `images_dirs = ["all"]` dùng mọi thư mục con (có chứa media) cạnh `config.toml`.

---

## 3. Dòng lệnh

```
python build_archive.py [tùy chọn]

  --images THƯ_MỤC     Dùng một thư mục media này, bỏ qua config.toml
  --output FILE        File HTML đầu ra (mặc định: index.html cạnh script)
  --title TÊN          Ghi đè tên archive
  --theme TÊN          Ghi đè theme
  --sort-by KIỂU       name | created | created_desc
  --ignore MẪU         Bỏ qua thư mục khớp mẫu (lặp lại được, gộp với ignored_folders)
  --icon FILE.png      Icon Màn hình chính iOS (ghi đè app_icon)
  --no-probe           Bỏ qua bước đọc kích thước ảnh
  --clear-cache        Xóa cache kích thước ảnh rồi build lại
  --open               Mở trình duyệt sau khi build
  --watch              Theo dõi thư mục, tự build lại khi thêm/xóa/sửa file
  --quiet              Chỉ in lỗi
```

Ví dụ:

```bash
python build_archive.py --images "D:/Memes" --theme dracula --sort-by created_desc --open
python build_archive.py --watch      # vừa bỏ ảnh vào thư mục vừa xem kết quả (F5 trình duyệt)
python build_archive.py --ignore Thumbs --ignore "Anime/2023"   # bỏ qua vài thư mục
```

Lần build đầu đọc kích thước từng ảnh và lưu vào file `.build_archive_cache.json` cạnh script; các lần sau chỉ đọc lại file mới hoặc đã đổi, nên rất nhanh. Xóa file này bất cứ lúc nào cũng an toàn.

---

## 4. Cách nhóm file thành bài viết

Các file cùng bài sẽ nằm chung một bài (nhiều ảnh cuộn liền nhau):

| Kiểu tên file | Ví dụ | Nhóm theo |
|---|---|---|
| Tumblr | `tumblr_abc123o1_1280.jpg`, `tumblr_abc123o2_1280.jpg` | `tumblr_abc123` |
| Số + chỉ mục | `128635952498_0.jpg`, `128635952498_1.jpg` | `128635952498` |
| Mã + số thứ tự + tiêu đề | `1h5bjv8 01 Cute Asian.jpg`, `1h5bjv8 02 Cute Asian.jpg` | mã + tiêu đề |
| Khác | `holiday.jpg` | tên file (mỗi file một bài) |

Các file cùng nhóm nhưng nằm ở thư mục con khác nhau vẫn là các bài riêng.

**Định dạng hỗ trợ:** JPG, PNG/APNG, GIF, WEBP, AVIF, BMP, SVG, JXL, HEIC/HEIF · MP4, WEBM, MOV, M4V, OGV. Việc phát được hay không tùy trình duyệt và codec (HEIC/JXL, ví dụ, nhiều trình duyệt chưa hiển thị được).

Thư mục ẩn (bắt đầu bằng `.`), `@eaDir`, `__MACOSX` bị bỏ qua.

### Ghi chú bằng Markdown

Đặt file `.md` **cùng tên** với ảnh (hoặc cùng tên nhóm bài) để hiện ghi chú dưới media:

```
tumblr_abc123o1_1280.jpg
tumblr_abc123o1_1280.md     ← ghi chú cho ảnh này
```

Hỗ trợ: tiêu đề `#`, **đậm**, *nghiêng*, ~~gạch~~, `code`, liên kết, danh sách `-` và `1.`, trích dẫn `>`, đường kẻ `---`. HTML thô luôn bị vô hiệu hóa (an toàn). Ghi chú cũng được đưa vào tìm kiếm.

---

## 5. Sử dụng trên trang

### Thanh công cụ (góc dưới phải; dưới cùng trên điện thoại)

**Lọc** (loại media, thư mục) · **Đã thích** · **Tìm** · **Ngẫu nhiên** · **Lên đầu** · **Thêm** (cài đặt: phong cách, bố cục, độ rộng/số cột, theme, đảo thứ tự, tự phát video, tốc độ trình chiếu, sao lưu, trợ giúp).

### Phím tắt

| Phím | Chức năng |
|---|---|
| `J` / `↓` · `K` / `↑` | Bài tiếp / bài trước |
| `Space` / `Shift+Space` | Bài tiếp / bài trước |
| `G` | Tìm và nhảy tới bài |
| `B` | Mở hộp "Bộ lọc đã lưu" |
| `Shift+Enter` (trong hộp tìm) | Chỉ hiện các bài khớp tìm kiếm (lọc danh sách) |
| `Esc` | Bỏ lọc tìm kiếm đang bật |
| `R` | Bài ngẫu nhiên |
| `L` | Thích / bỏ thích bài đang xem |
| `F` | Chỉ hiện bài đã thích |
| `V` | Đổi danh sách ⇄ lưới |
| `M` | Chọn theme |
| `E` / `I` | Sao lưu / khôi phục |
| `T` | Lên đầu trang |
| `?` hoặc `H` | Bảng trợ giúp |

**Khi đang xem ảnh phóng to:**

| Phím / thao tác | Chức năng |
|---|---|
| `←` `→` (hoặc `K` `J`, `Space`) | Ảnh trước / sau |
| `+` `−` `0` · cuộn chuột · chụm 2 ngón · chạm đúp | Phóng to / thu nhỏ / đặt lại |
| Kéo chuột / ngón tay | Di chuyển ảnh khi đã phóng to |
| `S` | Trình chiếu tự động |
| `I` | Bảng thông tin (tên file, kích thước, dung lượng, ngày, ghi chú) |
| `D` · `O` | Tải xuống · Mở trong tab mới |
| `F` | Toàn màn hình |
| `L` | Thích bài |
| `Esc` · vuốt xuống · nút Back | Đóng |

### Tìm kiếm (`G`)

Gõ số thứ tự (`300` hoặc `#300`), tên file, tên thư mục hoặc nội dung ghi chú. Nhiều từ = phải khớp tất cả. Toán tử:

| Toán tử | Ý nghĩa |
|---|---|
| `is:video` · `is:gif` · `is:image` | Bài có loại media đó |
| `is:multi` | Bài có nhiều media |
| `is:liked` | Bài đã thích |
| `is:note` | Bài có ghi chú `.md` |

Ví dụ: `is:multi cute` · `is:video is:liked`. Dùng `↑` `↓` chọn kết quả, `Enter` để nhảy tới bài.

### Lọc danh sách theo tìm kiếm (mới ở 3.1)

Muốn **xem cả tập ảnh khớp** thay vì nhảy từng bài: nhập nội dung tìm rồi bấm **Lọc danh sách (N)** hoặc nhấn `Shift+Enter`. Trang chỉ còn hiện N bài khớp, ở cả chế độ danh sách lẫn lưới, và trình xem ảnh phóng to cũng chỉ duyệt trong tập này.

- Một thanh trạng thái dưới tiêu đề hiện nội dung đang lọc và số bài. Bấm vào chữ để sửa, bấm **✕** hoặc nhấn `Esc` để bỏ lọc (trang giữ nguyên bài bạn đang xem nếu bài đó có trong danh sách đầy đủ).
- Dùng được mọi cú pháp của tìm kiếm: từ khóa, số bài, `is:video`, `is:gif`, `is:multi`, `is:liked`, `is:note`.
- Kết hợp được với bộ lọc **Lọc** (loại media, thư mục), **Đã thích** và **Đảo thứ tự**; các điều kiện cùng áp dụng.
- Mở hộp tìm khi đang lọc, nội dung lọc hiện sẵn để chỉnh; xóa trống rồi bấm **Bỏ lọc** cũng tắt được.
- Từ khóa không khớp bài nào thì không áp dụng (báo bằng thông báo, giữ nguyên lọc cũ). Chọn nhảy tới một bài nằm ngoài tập đang lọc sẽ tự bỏ lọc để mở bài đó.
- Bộ lọc chỉ tồn tại trong phiên xem, không lưu; tải lại trang thì trở về danh sách đầy đủ.

### Liên kết tới bài

Bấm vào số bài (`#123`) để sao chép liên kết dạng `index.html#p123`. Mở liên kết đó sẽ nhảy thẳng tới bài 123.

### Bộ lọc đã lưu (mới ở 3.2)

Lưu một tổ hợp lọc để dùng lại bằng một cú bấm. Một bộ lọc đã lưu ghi nhớ: **nội dung lọc theo tìm kiếm**, **loại media** (ảnh/GIF/video), **thư mục được chọn** và **chế độ Đã thích**.

- **Thêm:** bật các bộ lọc mong muốn (menu **Lọc**, **Đã thích**, hoặc “Lọc danh sách” trong hộp tìm kiếm), rồi bấm biểu tượng bookmark trên thanh trạng thái lọc, hoặc `B`, hoặc **Lọc → Lưu / quản lý bộ lọc…**. Đặt tên rồi nhấn `Enter`. Để trống tên thì dùng tên gợi ý theo nội dung lọc. Lưu lại với tên đã có (không phân biệt hoa/thường) sẽ **cập nhật** bộ lọc đó thay vì tạo bản sao.
- **Dùng lại:** bấm tên trong hộp thoại, hoặc chọn nhanh ở đầu menu **Lọc** (hiện 8 bộ lọc đầu). Bộ lọc đang áp dụng được đánh dấu.
- **Đổi tên:** bấm biểu tượng bút chì, gõ tên mới, `Enter` để lưu, `Esc` để hủy. Tên trống hoặc trùng tên khác sẽ bị từ chối.
- **Xóa:** bấm biểu tượng thùng rác (có hỏi xác nhận).
- Mỗi dòng cho biết điều kiện và **số bài hiện khớp**. Tối đa 40 bộ lọc.
- Nếu một bộ lọc nhắc tới thư mục không còn tồn tại (đổi tên/xóa thư mục), điều kiện thư mục đó được bỏ qua và trang có thông báo.
- Bộ lọc đã lưu nằm trong trình duyệt và **được đưa vào file sao lưu** (mục 6): khôi phục sẽ **gộp**, bỏ qua tên đã có, không ghi đè. File sao lưu cũ (không có bộ lọc) vẫn nhập được.
- Chỉ *danh sách* bộ lọc được nhớ; bộ lọc *đang bật* thì không (tải lại trang là về danh sách đầy đủ).

---

## 6. Dữ liệu cá nhân và sao lưu

Bài đã thích, bộ lọc đã lưu, vị trí đang đọc, theme và tùy chọn giao diện được lưu trong **trình duyệt** (localStorage), riêng cho từng archive.

- **Tương thích v2:** mã nhận diện archive và ID bài giữ nguyên công thức của v2, nên bài đã thích và vị trí đọc cũ **tự động dùng lại** sau khi nâng cấp, với điều kiện thư mục media không đổi vị trí/tên file.
- Đổi tên/di chuyển thư mục media hoặc thêm/xóa file làm thay đổi mã nhận diện, khi đó dữ liệu cũ sẽ không còn khớp. Hãy **sao lưu trước** (`E`), build lại rồi **khôi phục** (`I`): bài nào còn tồn tại sẽ được giữ.
- **Sao lưu & khôi phục** (`E`): tải file `.json`, hoặc sao chép chuỗi Base64. File gồm bài đã thích, **bộ lọc đã lưu** và vị trí đọc. Khôi phục **gộp** với bài đã thích và bộ lọc hiện có, không xóa dữ liệu cũ. Chuỗi backup của v2 vẫn nhập được.
- Chế độ ẩn danh, xóa dữ liệu trình duyệt, hoặc đổi trình duyệt/máy sẽ mất dữ liệu này, nên hãy sao lưu định kỳ.

---

## 7. Icon Màn hình chính iPhone/iPad (mới ở 3.2)

Mỗi `index.html` đều có sẵn các thẻ để khi mở bằng **Safari → Chia sẻ → Thêm vào Màn hình chính** sẽ hiện icon đẹp và mở toàn màn hình như một ứng dụng:

- `<link rel="apple-touch-icon" sizes="…" href="data:image/png;base64,…">` (icon nhúng thẳng vào file)
- `apple-mobile-web-app-capable`, `mobile-web-app-capable` (mở không có thanh địa chỉ)
- `apple-mobile-web-app-title` (tên dưới icon, lấy từ `app_name` hoặc `title`)
- `apple-mobile-web-app-status-bar-style` (từ `app_status_bar`; mặc định `black-translucent`, trang tự chừa lề an toàn cho tai thỏ/đảo động)
- Icon cũng được dùng làm favicon nếu bạn không có `fav.icon`/`favicon.*`.

**Chọn icon** (theo thứ tự ưu tiên):

1. `--icon đường_dẫn.png` trên dòng lệnh.
2. `app_icon = "icon.png"` trong `config.toml` (đường dẫn tính từ vị trí `config.toml`).
3. Tự nhận file `apple-touch-icon.png`, `app-icon.png` hoặc `icon.png` nằm cạnh `config.toml`/script.
4. Không có gì → **script tự vẽ một icon mặc định** (hai thẻ ảnh xếp chồng, tông màu theo theme), không cần thư viện nào. Icon được cache nên các lần build sau không mất thêm thời gian.

Icon nên là **PNG 180×180, không trong suốt** (iOS tô nền đen cho vùng trong suốt). Nếu máy có **Pillow** (`pip install pillow`), script tự cắt vuông, thu về 180×180 và dán lên nền đặc theo màu theme, nên bạn có thể dùng JPG/WEBP/PNG kích thước bất kỳ. Không có Pillow thì chỉ nhận PNG (dùng nguyên file, cảnh báo nếu sai kích thước); file khác PNG sẽ bị bỏ qua và dùng icon mặc định. Đường dẫn sai cũng chỉ cảnh báo rồi dùng icon mặc định, không làm hỏng build.

**Lưu ý khi dùng trên iPhone:**

- Safari chỉ cho “Thêm vào Màn hình chính” đối với trang có địa chỉ web. Xem qua máy chủ trong mạng nội bộ (ví dụ `python -m http.server` trong thư mục archive, rồi mở `http://<IP-máy-tính>:8000/` bằng Safari) hoặc đưa lên hosting/NAS của bạn. Tính năng này chưa được thử trên iPhone thật trong lúc phát triển.
- **Ứng dụng trên Màn hình chính có bộ nhớ riêng, tách khỏi Safari**: bài đã thích và bộ lọc đã lưu tạo trong Safari sẽ không tự xuất hiện trong ứng dụng. Dùng **Sao lưu & khôi phục** (`E`/`I`) để chuyển qua lại.
- Đổi icon sau khi đã thêm: gỡ ứng dụng khỏi Màn hình chính rồi thêm lại (iOS ghi nhớ icon cũ).

---

## 8. Loại trừ thư mục khi quét (mới ở 3.2)

Khai báo trong `config.toml` và/hoặc dòng lệnh; hai nguồn được **gộp**. Thư mục khớp bị bỏ qua hoàn toàn (không quét vào trong, nên cũng nhanh hơn).

```toml
ignored_folders = ["Thumbs", "_old*", "Anime/2023", "*/private", "~/Backup"]
```

```bash
python build_archive.py --ignore Thumbs --ignore "Anime/2023"
```

| Mẫu | Ý nghĩa |
|---|---|
| `Thumbs` (không có `/`) | Mọi thư mục tên đó, ở bất kỳ cấp nào |
| `_old*`, `bak?` | Ký tự đại diện `*` `?` `[abc]` như shell |
| `Anime/2023` (có `/`) | Đúng đường dẫn này, tính từ thư mục media |
| `Anime/*` | Mọi thư mục con trực tiếp của Anime |
| `*/private` | Thư mục `private` nằm trong một thư mục khác |
| `D:/Pictures/Tam`, `~/Backup` | Đường dẫn tuyệt đối: bỏ qua thư mục đó và mọi thứ bên trong |

- Không phân biệt hoa/thường. Dùng dấu `/` cho mọi hệ điều hành (kể cả Windows).
- Với `images_dirs = ["all"]`, mẫu cũng áp dụng cho chính các thư mục cấp 1 (ví dụ `ignored_folders = ["Backup"]` loại thư mục `Backup` khỏi danh sách).
- Cuối lần build có dòng thông báo số thư mục đã bỏ qua.
- **Lưu ý:** thêm/bớt mẫu loại trừ làm thay đổi tập bài của archive, nên mã nhận diện archive đổi và bài đã thích/vị trí đọc cũ có thể không còn khớp. Hãy **sao lưu (`E`) trước**, build lại rồi khôi phục (`I`).
- Thư mục ẩn (bắt đầu bằng `.`), `@eaDir`, `__MACOSX` luôn bị bỏ qua.

---

## 9. Hiệu năng và mẹo cho bộ sưu tập lớn

- Trang chỉ dựng vài bài đầu và tải thêm khi cuộn; ảnh dùng lazy-load. Ảnh đã có kích thước từ lúc build nên không bị nhảy layout.
- Kiểm thử với 20.000 bài (32.000 media): build khoảng 1,4 giây (bản cũ ~8,6 giây); `index.html` ~3,6 MB (bản cũ ~6,5 MB); trang mở nhanh hơn ~40%.
- Nhảy rất xa (ví dụ tới bài thứ 15.000 bằng tìm kiếm) cần dựng các bài ở giữa nên mất vài giây; nhảy vài nghìn bài chỉ khoảng nửa giây.
- Ảnh gốc dung lượng lớn sẽ làm lưới nặng hơn: trình duyệt phải giải mã ảnh gốc để hiển thị ô nhỏ (script không tạo ảnh thu nhỏ).
- Dùng `--watch` khi đang thêm nhiều ảnh; dùng `--no-probe` chỉ khi thật sự cần build nhanh nhất có thể.

---

## 10. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| "Không tìm thấy thư mục media" | Kiểm tra `images_dir` trong `config.toml` (đường dẫn tính từ vị trí `config.toml`). |
| Ảnh không hiện / khung xám | `index.html` bị chuyển đi nơi khác, hoặc định dạng trình duyệt không hỗ trợ (HEIC, JXL). Build lại tại chỗ, hoặc chuyển ảnh sang JPG/WEBP. |
| Video không phát | Codec không được hỗ trợ (ví dụ HEVC trên một số trình duyệt). Dùng MP4 H.264 hoặc WEBM. |
| Cảnh báo "ảnh không đọc được kích thước" | File lạ hoặc hỏng. Trang vẫn chạy, chỉ có thể nhảy layout nhẹ ở các ảnh đó. |
| Mất bài đã thích sau khi đổi thư mục | Xem mục 6: sao lưu trước khi đổi, sau đó khôi phục. |
| Build lỗi liên quan `config.toml` | Sai cú pháp TOML (thiếu ngoặc kép quanh chữ, hoặc số/đúng-sai bị đặt trong ngoặc kép). Thông báo lỗi nêu rõ khóa hoặc dòng. |
| "chỉ đọc config.toml" | Bạn còn `config.yml` cũ. Chuyển sang `config.toml` như hướng dẫn ở mục 2. |
| "cần Python 3.11 trở lên" | Cập nhật Python (`python --version` để kiểm tra). |
| Icon Màn hình chính không đổi / nền đen | Nền trong suốt sẽ bị iOS tô đen: dùng PNG đặc 180×180 (hoặc cài Pillow). Đổi icon xong phải gỡ ứng dụng khỏi Màn hình chính rồi thêm lại. |
| Thư mục đã loại trừ vẫn xuất hiện | Kiểm tra mẫu: không có `/` là khớp tên, có `/` là khớp đường dẫn tính từ thư mục media. |
| Muốn build lại từ đầu | `python build_archive.py --clear-cache`. |

---

## 11. Có gì mới

### 3.2
- **Bộ lọc đã lưu:** thêm, áp dụng nhanh, đổi tên, xóa; nằm trong file sao lưu.
- **Icon Màn hình chính iOS:** thẻ `apple-touch-icon` và meta ứng dụng web; nhận icon của bạn hoặc tự vẽ icon mặc định; cấu hình `app_icon`, `app_name`, `app_status_bar`, tham số `--icon`.
- **Loại trừ thư mục khi quét:** `ignored_folders` trong `config.toml` và `--ignore` trên dòng lệnh, hỗ trợ ký tự đại diện, mẫu theo đường dẫn và đường dẫn tuyệt đối.
- Sửa: nhấn `Esc` khi con trỏ đang ở một ô tick trong menu Lọc/Cài đặt giờ đóng luôn menu.

### 3.1
- **Cấu hình chuyển sang `config.toml`** (yêu cầu Python 3.11+), bỏ hỗ trợ `config.yml`. Kiểm tra kiểu giá trị chặt hơn, báo khóa lạ, báo lỗi rõ ràng.
- **Lọc danh sách theo nội dung tìm kiếm**, kèm thanh trạng thái sửa/bỏ lọc.

### 3.0 (so với v2)

- **Nhanh hơn:** quét thư mục một lượt, đọc kích thước ảnh song song và có cache, nhóm bài tối ưu; HTML nhẹ hơn ~45%; ít RAM hơn, tải trang nhanh hơn.
- **Không nhảy layout:** ảnh có kích thước sẵn, `content-visibility` cho bài ngoài màn hình.
- **Lưới masonry thật**, cân cột, chọn số cột, đổi bố cục tức thì.
- **Xem ảnh phóng to mới:** zoom/kéo/chụm, trình chiếu, toàn màn hình, thông tin file, tải xuống, tải trước ảnh kế bên, vuốt để chuyển/đóng, nút Back đóng ảnh.
- **Tìm kiếm có toán tử** và duyệt bằng bàn phím; **bài ngẫu nhiên**; **đảo thứ tự**; **thanh tiến độ**; **liên kết trực tiếp** `#p123`.
- **Sao lưu bằng file**, khôi phục dạng gộp; tự phát video khi cuộn tới; 5 theme mới; biểu tượng SVG (không phụ thuộc font emoji).
- **CLI:** `--watch`, `--open`, `--no-probe`, `--clear-cache`, `--quiet`.
- **Giữ tương thích:** mã nhận diện archive, ID bài, thứ tự bài, cách nhóm file và ghi chú `.md` giống hệt v2 (đã đối chiếu trên bộ 721 bài và 20.000 bài).
