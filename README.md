# Offline Media Archive v2.10

Công cụ tạo archive ảnh, GIF và video ngoại tuyến theo phong cách Tumblr. Tệp HTML, CSS và JavaScript được đóng gói trong một trang `index.html`; media vẫn nằm trong các thư mục nguồn để giữ HTML gọn nhẹ.

## Bắt đầu nhanh

1. Đặt `build_archive.py` cạnh thư mục media, ví dụ `images/`.
2. Sao chép `config.yml_sample` thành `config.yml`.
3. Sửa tên archive, thư mục media và theme trong `config.yml` nếu cần.
4. Chạy:

   ```bash
   python3 build_archive.py
   ```

5. Mở `index.html` bằng trình duyệt. Không cần server để duyệt archive cục bộ.

Nếu không có `config.yml`, chương trình tự tìm thư mục `Images/` hoặc `images/` cạnh `build_archive.py` và trong thư mục làm việc hiện tại. Nếu vẫn không tìm thấy, chương trình sẽ báo lỗi đường dẫn.

## Cấu hình

`config.yml_sample` có chú thích tiếng Việt và là cấu hình tham khảo. Parser của script hỗ trợ các giá trị đơn giản, danh sách `images_dirs` dạng nhiều dòng, chuỗi có dấu nháy và comment bắt đầu bằng `#`. Không dùng cấu trúc YAML lồng nhau hoặc block scalar.

| Khóa | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `title` | Tên thư mục chứa `build_archive.py` + ` Archive` | Tên archive trên trang. Để trống để dùng tên tự động. |
| `images_dirs` | Tự tìm `Images/` hoặc `images/` | Danh sách thư mục media. Đường dẫn tương đối tính từ thư mục chứa `config.yml`. |
| `images_dir` | Không đặt | Bí danh tiện dùng khi chỉ có một thư mục; `images_dirs` được ưu tiên nếu có danh sách. |
| `theme` | `auto` | Theme lúc tạo: `auto` hoặc một theme cụ thể. |
| `theme_light` | `rose-pine-dawn` | Theme sáng khi `theme: auto`. |
| `theme_dark` | `mocha` | Theme tối khi `theme: auto`. |
| `sort_by` | `name` | `name`, `created` (cũ đến mới), hoặc `created_desc` (mới đến cũ). |
| `sticky_header` | `true` | Bật/tắt header ghim khi cuộn. |
| `show_filename` | `false` | Hiện tên file dưới media. |
| `show_created_time` | `false` | Hiện ngày giờ tạo file dưới media. |

`show_media_info` vẫn được hỗ trợ để tương thích cấu hình cũ: nếu đặt khóa này mà không ghi riêng `show_filename` hoặc `show_created_time`, giá trị của nó áp dụng cho cả hai.

### Nhiều thư mục media

```yaml
images_dirs:
  - "images"
  - "../other-archive/images"
  - "../third-archive/images"
```

Các đường dẫn media trong HTML được tính tương đối từ vị trí `index.html`. Giữ nguyên quan hệ thư mục khi di chuyển archive, hoặc tạo lại HTML bằng `build_archive.py` ở vị trí mới. Khi cấu hình nhiều thư mục, mỗi bài có nhãn tên thư mục nguồn; cấu hình một thư mục thì nhãn này được ẩn.

### Theme

Theme có sẵn:

- Catppuccin: `mocha`, `frappe`, `macchiato`, `latte`
- Tối: `nord`, `tokyo-night`, `gruvbox`, `rose-pine`, `noir-velvet`, `oxblood`
- Sáng: `nord-light`, `tokyo-night-light`, `gruvbox-light`, `rose-pine-dawn`

Chọn `theme: auto` để dùng `theme_light`/`theme_dark` theo cài đặt sáng tối của thiết bị. Trong trang, mục **More** cho phép đổi theme trực tiếp và chuyển phong cách **Hiện đại/Cổ điển**. Lựa chọn giao diện được lưu trong `localStorage` của trình duyệt, riêng theo từng archive.

## Dùng lệnh

```bash
python3 build_archive.py --help
python3 build_archive.py --images "/path/to/images"
python3 build_archive.py --output "/path/to/index.html"
python3 build_archive.py --title "Tên archive"
python3 build_archive.py --theme noir-velvet
python3 build_archive.py --sort-by created_desc
```

Các cờ `--images`, `--output`, `--title`, `--theme`, `--sort-by` ghi đè cấu hình tương ứng cho lần chạy đó. `--images` dùng một thư mục thay cho danh sách trong `config.yml`.

## Tính năng

- Gom media thành bài Tumblr theo mẫu tên file Tumblr (`tumblr_...o1`, `o2`...) và chuỗi số có hậu tố `_0`, `_1`...
- Nạp feed theo từng đợt khi cuộn gần cuối; media bắt đầu tải khi gần vùng xem. Video không lấy metadata trước khi cần.
- Tìm theo số thứ tự bài, tên file hoặc nội dung ghi chú Markdown; nhấn Enter để mở kết quả đầu.
- Lọc nhiều loại media cùng lúc: ảnh, GIF, video. Lightbox điều hướng trong loại media đang lọc.
- Like bài, xem danh sách Liked và lưu vị trí đọc dở trong trình duyệt.
- Lightbox có điều hướng bàn phím và vuốt ngang trên điện thoại.
- Chế độ danh sách/lưới, theme động, phong cách Cổ điển/Hiện đại.
- Sao lưu các bài đã Like và vị trí bằng chuỗi Base64 trong clipboard; nhập bằng cách dán chuỗi backup.
- Hỗ trợ ghi chú Markdown `.md` cạnh media.
- Nếu có `fav.icon`, `favicon.ico`, `favicon.png` hoặc `favicon.svg` cạnh script hay trong thư mục media, generator sẽ nhúng favicon vào HTML.

### Phím tắt

| Phím | Tác vụ |
| --- | --- |
| `J` / `↓` | Bài tiếp |
| `K` / `↑` | Bài trước |
| `Space` / `Shift+Space` | Tiến / lùi một bài |
| `L` | Like bài đang chọn |
| `F` | Bật/tắt danh sách Liked |
| `G` | Mở tìm kiếm / nhảy tới bài |
| `V` | Chuyển lưới/danh sách |
| `M` | Mở lựa chọn theme |
| `E` / `I` | Export / import backup |
| `T` | Lên đầu archive |
| Trong Lightbox: `J` / `→`, `K` / `←`, `Esc` | Media tiếp, trước, đóng |

## Định dạng media

Generator nhận JPG/JPEG, PNG/APNG, GIF, WEBP, AVIF, BMP, SVG, JXL, HEIC/HEIF, MP4, WEBM, MOV, M4V và OGV. Khả năng giải mã ảnh và codec video tùy trình duyệt/thiết bị; file được nhận diện không đảm bảo mọi trình duyệt đều phát được.

## Lưu ý

- Archive là trang tĩnh: like, theme, phong cách và vị trí đọc được lưu trên trình duyệt hiện tại; chúng không tự đồng bộ giữa thiết bị.
- Backup Base64 chỉ mã hóa cách biểu diễn dữ liệu, không phải mã hóa bảo mật. Chỉ chia sẻ chuỗi backup với người mày tin cậy.
- GIF và video dung lượng lớn vẫn cần tải dữ liệu khi xem. Lazy loading giúp tránh tải media ở xa, nhưng không làm file nguồn nhỏ hơn.
- Khi publish lên web, tải `index.html` cùng toàn bộ thư mục media được tham chiếu; bảo đảm đường dẫn tương đối còn đúng.


## Đưa dự án lên GitHub

Tên repository gợi ý: **`offline-media-archive`**. File `.gitignore` đi kèm loại trừ cấu hình cá nhân, media, HTML archive được tạo và metadata của macOS. Trước khi public repository, cần kiểm tra các tệp đã được Git theo dõi từ trước; `.gitignore` không tự gỡ các tệp đã được commit.
