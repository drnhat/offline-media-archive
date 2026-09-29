 Gemini
Cuộc trò chuyện mới
Tìm kiếm trong các cuộc trò chuyện
Thư viện
Sổ ghi chú mới
Lịch sử và Hồi ức về Hệ điều hành Unix
Viêm gan siêu vi và thai kỳ
Tất cả sổ ghi chú
Tạo README cho build_archive.py
Script Python Ghi Metadata Âm Nhạc
Hướng dẫn cài đặt và giải nén
Trang web tạo favicon miễn phí
Xe Honda Vision có phanh ABS không?
Tải File Qua Proxy SOCKS5 Bằng Aria2c
Python script for Tumblr-style archive
Cách tính phí sử dụng ChatGPT
Đặt tên thư mục code tạm
Cách khắc phục lỗi push Git bị từ chối
Khả Năng Chịu Tải Của Dây Điện 0.75mm²
Tư vấn webserver siêu nhẹ phục vụ file tĩnh
Khắc Phục Màn Hình Rung Lắc
Kiểm Tra Hồ Sơ Bệnh Án
Cách tăng sáng video trên MPV
Lệnh FFmpeg Trích Xuất Keyframe
Giải mã file dữ liệu Tumblr
Hướng Dẫn Tải Dữ Liệu Tumblr
Tìm archive Tumblr Đèn Dạ Khói Đường
Tạo Web Hiển Thị Ảnh Tumblr
Script chuẩn hóa tag file FLAC
Dịch Phụ Đề Tiếng Thái
Sửa lỗi import trong Python
Sửa lỗi mã Python dịch SRT
Kiểm Tra Hạn Mức Sử Dụng
Trò chuyện với Gemini

Viết readme thật chuyên nghiệp cho code này nha

Dưới đây là file README.md được thiết kế chuẩn mực, chuyên nghiệp cho dự án của bạn (phù hợp đăng trên GitHub/GitLab).
📸 Tumblr-Style Offline Image & Video Archive Builder (build_archive.py)

Một công cụ Python gọn nhẹ, mạnh mẽ giúp đóng gói toàn bộ bộ sưu tập ảnh và video offline của bạn thành một file HTML duy nhất (index.html) với giao diện phong cách Tumblr hiện đại, mượt mà và tối ưu hóa trải nghiệm người dùng trên cả PC và thiết bị di động.
✨ Tính năng nổi bật

    🚀 Single-File Output & Full Offline: Đóng gói giao diện HTML, CSS, JavaScript thành 1 file duy nhất. Dễ dàng lưu trữ, chia sẻ hoặc mở trực tiếp trên trình duyệt mà không cần Server/Node.js.

    🎨 14+ Theme Catppuccin & Palette màu sắc đẹp mắt: Hỗ trợ theme sáng/tối tự động (auto) hoặc lựa chọn thủ công: Mocha, Frappe, Macchiato, Latte, Nord, Tokyo Night, Gruvbox, Rosé Pine, Oxblood, Noir Velvet...

    📁 Tự động gom nhóm bài viết (Tumblr-style Grouping):

        Nhận diện thông minh chuỗi ảnh/media cùng 1 post qua định dạng tên file của Tumblr (o1, o2), số hiệu (128635952498_0.jpg) hoặc tên series.

        Hỗ trợ gom nhóm thư mục con linh hoạt với tính năng Lọc thư mục theo nhánh.

    📝 Hỗ trợ Ghi chú / Markdown Sidecar: Tự động đọc nội dung file .md cùng tên với ảnh/bài viết để hiển thị chú thích, bài viết kèm theo.

    🎥 Hỗ trợ Đa phương tiện:

        Hình ảnh: JPG, PNG, WEBP, AVIF, GIF, BMP, SVG, JXL, HEIC/HEIF, APNG.

        Video: MP4, WEBM, MOV, M4V, OGV.

    ⚡ Hiệu năng cao & Lazy Loading: Tải ảnh theo dạng cuộn trang (Infinite Scroll / Batch rendering) nhẹ nhàng, mượt mà ngay cả với hàng chục ngàn ảnh.

    🔍 Tìm kiếm & Bộ lọc nâng cao:

        Tìm kiếm tức thì theo số bài, tên file hoặc nội dung ghi chú.

        Lọc theo loại media (Ảnh, GIF, Video) hoặc bài viết đã thả tim (Liked).

        Chế độ hiển thị Lưới gọn (Grid View) hoặc Danh sách (Feed View).

    ⌨️ Phím tắt điều hướng nhanh & Lightbox: Trải nghiệm xem ảnh phóng to, chuyển bài bằng bàn phím (J/K, Space, G, L, V, M...) hoặc vuốt cảm ứng trên điện thoại.

    💾 Backup / Restore dữ liệu Thích (Likes): Cho phép xuất/nhập danh sách bài viết đã thả tim dưới dạng file JSON.

🛠️ Yêu cầu hệ thống

    Python: Python 3.8+

    Thư viện bên thứ ba: Không có! Chỉ sử dụng Thư viện chuẩn (Standard Library) của Python.

🚀 Hướng dẫn nhanh (Quick Start)
1. Cấu trúc thư mục chuẩn

Đặt file build_archive.py cùng cấp với thư mục chứa ảnh/video của bạn (ví dụ ./images):
Plaintext

my-image-archive/
├── build_archive.py
├── config.yml (không bắt buộc)
└── images/
    ├── 128635952498_0.jpg
    ├── 128635952498_1.jpg
    ├── 128635952498_1.md        <-- (Tùy chọn) Chú thích cho bài viết dạng Markdown
    ├── photo_2026-09-29.jpg
    └── subfolder/
        └── video_clip.mp4

2. Chạy lệnh tạo Archive

Chạy lệnh sau trong terminal:
Bash

python3 build_archive.py

Lệnh trên sẽ quét thư mục ảnh và tạo ra file index.html. Bạn chỉ cần click đúp vào index.html để mở bộ sưu tập trên trình duyệt!
⚙️ Cấu hình (config.yml)

Bạn có thể tạo file config.yml nằm cạnh script để tùy chỉnh mặc định:
YAML

# Tiêu đề bộ sưu tập
title: "BST Ảnh Của Tôi"

# Đường dẫn thư mục chứa media (hoặc danh sách các thư mục)
images_dir: "images"
# Hoặc khai báo nhiều thư mục:
# images_dirs:
#   - "album_2025"
#   - "album_2026"
# Hoặc quét tất cả thư mục con:
# images_dirs: "all"

# Giao diện mặc định (auto, mocha, nord, tokyo-night, rose-pine, ...)
theme: "auto"
theme_light: "rose-pine-dawn"
theme_dark: "mocha"

# Sắp xếp: name (theo tên), created (ngày cũ nhất trước), created_desc (mới nhất trước)
sort_by: "created_desc"

# Cài đặt giao diện
sticky_header: "true"
show_filename: "false"
show_created_time: "false"
show_file_size: "false"
show_video_thumbnails: "false"

💻 Tham số dòng lệnh (CLI Options)

Bạn có thể ghi đè cài đặt từ config.yml bằng các tham số CLI:
Bash

python3 build_archive.py [options]

Tham số	Mô tả
--images <path>	Chỉ định đường dẫn thư mục media (Ghi đè config.yml).
--output <path>	Chỉ định đường dẫn file HTML xuất ra (Mặc định: index.html).
--title <text>	Đặt tiêu đề cho Archive.
--theme <theme>	Đặt theme màu sắc (Ví dụ: mocha, nord, tokyo-night, latte...).
--sort-by <type>	Kiểu sắp xếp: name, created, created_desc.

Ví dụ:
Bash

# Tạo archive từ thư mục ./my_photos với theme Tokyo Night và sắp xếp mới nhất lên đầu
python3 build_archive.py --images ./my_photos --title "Kỷ Niệm 2026" --theme tokyo-night --sort-by created_desc --output gallery.html

⌨️ Phím tắt điều hướng (Keyboard Shortcuts)

Khi đang mở trang HTML Archive, bạn có thể dùng các phím tắt sau:
Duyệt bài (Feed View)

    J / ↓ : Chuyển xuống bài tiếp theo.

    K / ↑ : Quay lại bài trước.

    Space / Shift + Space : Cuộn nhanh tới/lùi.

    T : Nhảy lên đầu trang.

Công cụ & Thao tác

    G : Mở ô tìm kiếm bài viết / media.

    L : Thả tim (Like) bài viết đang chọn.

    F : Bật/tắt chế độ chỉ hiển thị bài đã thích.

    V : Đổi giữa chế độ Lưới (Grid View) và Danh sách (Feed View).

    M : Đổi nhanh Theme giao diện.

    E / I : Export / Import dữ liệu thả tim (Backup/Restore).

Lightbox (Xem phóng to)

    J / → : Xem media tiếp theo.

    K / ← : Xem media phía trước.

    Esc : Đóng Lightbox.

📄 Giấy phép (License)

Mã nguồn được phát hành dưới giấy phép MIT License. Bạn có thể tự do sử dụng, chỉnh sửa và chia sẻ.

Mày tạo luôn Readme.md đi, để tao bỏ lên github
2. Chạy lệnh tạo Archive

Chạy lệnh sau trong terminal:
Bash

python3 build_archive.py

Lệnh trên sẽ quét thư mục ảnh và tạo ra file index.html. Bạn chỉ cần click đúp vào index.html để mở bộ sưu tập trên trình duyệt!
⚙️ Cấu hình (config.yml)

Bạn có thể tạo file config.yml nằm cạnh script để tùy chỉnh mặc định:
YAML

# Tiêu đề bộ sưu tập
title: "BST Ảnh Của Tôi"

# Đường dẫn thư mục chứa media (hoặc danh sách các thư mục)
images_dir: "images"
# Hoặc khai báo nhiều thư mục:
# images_dirs:
#   - "album_2025"
#   - "album_2026"
# Hoặc quét tất cả thư mục con:
# images_dirs: "all"

# Giao diện mặc định (auto, mocha, nord, tokyo-night, rose-pine, ...)
theme: "auto"
theme_light: "rose-pine-dawn"
theme_dark: "mocha"

# Sắp xếp: name (theo tên), created (ngày cũ nhất trước), created_desc (mới nhất trước)
sort_by: "created_desc"

# Cài đặt giao diện
sticky_header: "true"
show_filename: "false"
show_created_time: "false"
show_file_size: "false"
show_video_thumbnails: "false"

💻 Tham số dòng lệnh (CLI Options)

Bạn có thể ghi đè cài đặt từ config.yml bằng các tham số CLI:
Bash

python3 build_archive.py [options]

Tham số	Mô tả
--images <path>	Chỉ định đường dẫn thư mục media (Ghi đè config.yml).
--output <path>	Chỉ định đường dẫn file HTML xuất ra (Mặc định: index.html).
--title <text>	Đặt tiêu đề cho Archive.
--theme <theme>	Đặt theme màu sắc (Ví dụ: mocha, nord, tokyo-night, latte...).
--sort-by <type>	Kiểu sắp xếp: name, created, created_desc.

Ví dụ:
Bash

# Tạo archive từ thư mục ./my_photos với theme Tokyo Night và sắp xếp mới nhất lên đầu
python3 build_archive.py --images ./my_photos --title "Kỷ Niệm 2026" --theme tokyo-night --sort-by created_desc --output gallery.html

⌨️ Phím tắt điều hướng (Keyboard Shortcuts)

Khi đang mở trang HTML Archive, bạn có thể dùng các phím tắt sau:
Duyệt bài (Feed View)

    J / ↓ : Chuyển xuống bài tiếp theo.

    K / ↑ : Quay lại bài trước.

    Space / Shift + Space : Cuộn nhanh tới/lùi.

    T : Nhảy lên đầu trang.

Công cụ & Thao tác

    G : Mở ô tìm kiếm bài viết / media.

    L : Thả tim (Like) bài viết đang chọn.

    F : Bật/tắt chế độ chỉ hiển thị bài đã thích.

    V : Đổi giữa chế độ Lưới (Grid View) và Danh sách (Feed View).

    M : Đổi nhanh Theme giao diện.

    E / I : Export / Import dữ liệu thả tim (Backup/Restore).

Lightbox (Xem phóng to)

    J / → : Xem media tiếp theo.

    K / ← : Xem media phía trước.

    Esc : Đóng Lightbox.

📄 Giấy phép (License)

Mã nguồn được phát hành dưới giấy phép MIT License. Bạn có thể tự do sử dụng, chỉnh sửa và chia sẻ.
"""

with open("README.md", "w", encoding="utf-8") as f:
f.write(readme_content)

print("FILE_CREATED: README.md")


```text?code_stdout&code_event_index=1
FILE_CREATED: README.md

Tệp README.md đã được tạo thành công!
Biểu tượng MD
README
 MD 
📸 Tumblr-Style Offline Image & Video Archive Builder (build_archive.py)

Một công cụ Python gọn nhẹ, mạnh mẽ giúp đóng gói toàn bộ bộ sưu tập ảnh và video offline của bạn thành một file HTML duy nhất (index.html) với giao diện phong cách Tumblr hiện đại, mượt mà và tối ưu hóa trải nghiệm người dùng trên cả PC và thiết bị di động.
✨ Tính năng nổi bật

    🚀 Single-File Output & Full Offline: Đóng gói giao diện HTML, CSS, JavaScript thành 1 file duy nhất. Dễ dàng lưu trữ, chia sẻ hoặc mở trực tiếp trên trình duyệt mà không cần Server/Node.js.

    🎨 14+ Theme Catppuccin & Palette màu sắc đẹp mắt: Hỗ trợ theme sáng/tối tự động (auto) hoặc lựa chọn thủ công: Mocha, Frappe, Macchiato, Latte, Nord, Tokyo Night, Gruvbox, Rosé Pine, Oxblood, Noir Velvet...

    📁 Tự động gom nhóm bài viết (Tumblr-style Grouping):

        Nhận diện thông minh chuỗi ảnh/media cùng 1 post qua định dạng tên file của Tumblr (o1, o2), số hiệu (128635952498_0.jpg) hoặc tên series.

        Hỗ trợ gom nhóm thư mục con linh hoạt với tính năng Lọc thư mục theo nhánh.

    📝 Hỗ trợ Ghi chú / Markdown Sidecar: Tự động đọc nội dung file .md cùng tên với ảnh/bài viết để hiển thị chú thích, bài viết kèm theo.

    🎥 Hỗ trợ Đa phương tiện:

        Hình ảnh: JPG, PNG, WEBP, AVIF, GIF, BMP, SVG, JXL, HEIC/HEIF, APNG.

        Video: MP4, WEBM, MOV, M4V, OGV.

    ⚡ Hiệu năng cao & Lazy Loading: Tải ảnh theo dạng cuộn trang (Infinite Scroll / Batch rendering) nhẹ nhàng, mượt mà ngay cả với hàng chục ngàn ảnh.

    🔍 Tìm kiếm & Bộ lọc nâng cao:

        Tìm kiếm tức thì theo số bài, tên file hoặc nội dung ghi chú.

        Lọc theo loại media (Ảnh, GIF, Video) hoặc bài viết đã thả tim (Liked).

        Chế độ hiển thị Lưới gọn (Grid View) hoặc Danh sách (Feed View).

    ⌨️ Phím tắt điều hướng nhanh & Lightbox: Trải nghiệm xem ảnh phóng to, chuyển bài bằng bàn phím (J/K, Space, G, L, V, M...) hoặc vuốt cảm ứng trên điện thoại.

    💾 Backup / Restore dữ liệu Thích (Likes): Cho phép xuất/nhập danh sách bài viết đã thả tim dưới dạng file JSON.

🛠️ Yêu cầu hệ thống

    Python: Python 3.8+

    Thư viện bên thứ ba: Không có! Chỉ sử dụng Thư viện chuẩn (Standard Library) của Python.

🚀 Hướng dẫn nhanh (Quick Start)
1. Cấu trúc thư mục chuẩn

Đặt file build_archive.py cùng cấp với thư mục chứa ảnh/video của bạn (ví dụ ./images):
Plaintext

my-image-archive/
├── build_archive.py
├── config.yml (không bắt buộc)
└── images/
    ├── 128635952498_0.jpg
    ├── 128635952498_1.jpg
    ├── 128635952498_1.md        <-- (Tùy chọn) Chú thích cho bài viết dạng Markdown
    ├── photo_2026-09-29.jpg
    └── subfolder/
        └── video_clip.mp4

2. Chạy lệnh tạo Archive

Chạy lệnh sau trong terminal:
Bash

python3 build_archive.py

Lệnh trên sẽ quét thư mục ảnh và tạo ra file index.html. Bạn chỉ cần click đúp vào index.html để mở bộ sưu tập trên trình duyệt!
⚙️ Cấu hình (config.yml)

Bạn có thể tạo file config.yml nằm cạnh script để tùy chỉnh mặc định:
YAML

# Tiêu đề bộ sưu tập
title: "BST Ảnh Của Tôi"

# Đường dẫn thư mục chứa media (hoặc danh sách các thư mục)
images_dir: "images"
# Hoặc khai báo nhiều thư mục:
# images_dirs:
#   - "album_2025"
#   - "album_2026"
# Hoặc quét tất cả thư mục con:
# images_dirs: "all"

# Giao diện mặc định (auto, mocha, nord, tokyo-night, rose-pine, ...)
theme: "auto"
theme_light: "rose-pine-dawn"
theme_dark: "mocha"

# Sắp xếp: name (theo tên), created (ngày cũ nhất trước), created_desc (mới nhất trước)
sort_by: "created_desc"

# Cài đặt giao diện
sticky_header: "true"
show_filename: "false"
show_created_time: "false"
show_file_size: "false"
show_video_thumbnails: "false"

💻 Tham số dòng lệnh (CLI Options)

Bạn có thể ghi đè cài đặt từ config.yml bằng các tham số CLI:
Bash

python3 build_archive.py [options]

Tham số	Mô tả
--images <path>	Chỉ định đường dẫn thư mục media (Ghi đè config.yml).
--output <path>	Chỉ định đường dẫn file HTML xuất ra (Mặc định: index.html).
--title <text>	Đặt tiêu đề cho Archive.
--theme <theme>	Đặt theme màu sắc (Ví dụ: mocha, nord, tokyo-night, latte...).
--sort-by <type>	Kiểu sắp xếp: name, created, created_desc.

Ví dụ:
Bash

# Tạo archive từ thư mục ./my_photos với theme Tokyo Night và sắp xếp mới nhất lên đầu
python3 build_archive.py --images ./my_photos --title "Kỷ Niệm 2026" --theme tokyo-night --sort-by created_desc --output gallery.html

⌨️ Phím tắt điều hướng (Keyboard Shortcuts)

Khi đang mở trang HTML Archive, bạn có thể dùng các phím tắt sau:
Duyệt bài (Feed View)

    J / ↓ : Chuyển xuống bài tiếp theo.

    K / ↑ : Quay lại bài trước.

    Space / Shift + Space : Cuộn nhanh tới/lùi.

    T : Nhảy lên đầu trang.

Công cụ & Thao tác

    G : Mở ô tìm kiếm bài viết / media.

    L : Thả tim (Like) bài viết đang chọn.

    F : Bật/tắt chế độ chỉ hiển thị bài đã thích.

    V : Đổi giữa chế độ Lưới (Grid View) và Danh sách (Feed View).

    M : Đổi nhanh Theme giao diện.

    E / I : Export / Import dữ liệu thả tim (Backup/Restore).

Lightbox (Xem phóng to)

    J / → : Xem media tiếp theo.

    K / ← : Xem media phía trước.

    Esc : Đóng Lightbox.

📄 Giấy phép (License)

Mã nguồn được phát hành dưới giấy phép MIT License. Bạn có thể tự do sử dụng, chỉnh sửa và chia sẻ.


Gemini là một AI và có thể mắc sai sót.
Gemini
Realtime
Images
Preview
Export
🌐 English

# 📸 Tumblr-Style Offline Image & Video Archive Builder (`build_archive.py`)

Một công cụ Python gọn nhẹ, mạnh mẽ giúp đóng gói toàn bộ bộ sưu tập ảnh và video offline của bạn thành **một file HTML duy nhất (`index.html`)** với giao diện phong cách Tumblr hiện đại, mượt mà và tối ưu hóa trải nghiệm người dùng trên cả PC và thiết bị di động.

---

## ✨ Tính năng nổi bật

* 🚀 **Single-File Output & Full Offline**: Đóng gói giao diện HTML, CSS, JavaScript thành 1 file duy nhất. Dễ dàng lưu trữ, chia sẻ hoặc mở trực tiếp trên trình duyệt mà không cần Server/Node.js.
* 🎨 **14+ Theme Catppuccin & Palette màu sắc đẹp mắt**: Hỗ trợ theme sáng/tối tự động (`auto`) hoặc lựa chọn thủ công: *Mocha, Frappe, Macchiato, Latte, Nord, Tokyo Night, Gruvbox, Rosé Pine, Oxblood, Noir Velvet...*
* 📁 **Tự động gom nhóm bài viết (Tumblr-style Grouping)**:
  * Nhận diện thông minh chuỗi ảnh/media cùng 1 post qua định dạng tên file của Tumblr (`o1`, `o2`), số hiệu (`128635952498_0.jpg`) hoặc tên series.
  * Hỗ trợ gom nhóm thư mục con linh hoạt với tính năng **Lọc thư mục theo nhánh**.
* 📝 **Hỗ trợ Ghi chú / Markdown Sidecar**: Tự động đọc nội dung file `.md` cùng tên với ảnh/bài viết để hiển thị chú thích, bài viết kèm theo.
* 🎥 **Hỗ trợ Đa phương tiện**:
  * **Hình ảnh**: `JPG`, `PNG`, `WEBP`, `AVIF`, `GIF`, `BMP`, `SVG`, `JXL`, `HEIC/HEIF`, `APNG`.
  * **Video**: `MP4`, `WEBM`, `MOV`, `M4V`, `OGV`.
* ⚡ **Hiệu năng cao & Lazy Loading**: Tải ảnh theo dạng cuộn trang (Infinite Scroll / Batch rendering) nhẹ nhàng, mượt mà ngay cả với hàng chục ngàn ảnh.
* 🔍 **Tìm kiếm & Bộ lọc nâng cao**:
  * Tìm kiếm tức thì theo số bài, tên file hoặc nội dung ghi chú.
  * Lọc theo loại media (*Ảnh*, *GIF*, *Video*) hoặc bài viết đã thả tim (*Liked*).
  * Chế độ hiển thị **Lưới gọn (Grid View)** hoặc **Danh sách (Feed View)**.
* ⌨️ **Phím tắt điều hướng nhanh & Lightbox**: Trải nghiệm xem ảnh phóng to, chuyển bài bằng bàn phím (`J`/`K`, `Space`, `G`, `L`, `V`, `M`...) hoặc vuốt cảm ứng trên điện thoại.
* 💾 **Backup / Restore dữ liệu Thích (Likes)**: Cho phép xuất/nhập danh sách bài viết đã thả tim dưới dạng file JSON.

---

## 🛠️ Yêu cầu hệ thống

* **Python**: `Python 3.8+`
* **Thư viện bên thứ ba**: **Không có!** Chỉ sử dụng Thư viện chuẩn (Standard Library) của Python.

---

## 🚀 Hướng dẫn nhanh (Quick Start)

### 1. Cấu trúc thư mục chuẩn

Đặt file `build_archive.py` cùng cấp với thư mục chứa ảnh/video của bạn (ví dụ `./images`):

```text
my-image-archive/
├── build_archive.py
├── config.yml (không bắt buộc)
└── images/
    ├── 128635952498_0.jpg
    ├── 128635952498_1.jpg
    ├── 128635952498_1.md        <-- (Tùy chọn) Chú thích cho bài viết dạng Markdown
    ├── photo_2026-09-29.jpg
    └── subfolder/
        └── video_clip.mp4
```

### 2. Chạy lệnh tạo Archive

Chạy lệnh sau trong terminal:

```bash
python3 build_archive.py
```

Lệnh trên sẽ quét thư mục ảnh và tạo ra file **`index.html`**. Bạn chỉ cần click đúp vào `index.html` để mở bộ sưu tập trên trình duyệt!

---

## ⚙️ Cấu hình (`config.yml`)

Bạn có thể tạo file `config.yml` nằm cạnh script để tùy chỉnh mặc định:

```yaml
# Tiêu đề bộ sưu tập
title: "BST Ảnh Của Tôi"

# Đường dẫn thư mục chứa media (hoặc danh sách các thư mục)
images_dir: "images"
# Hoặc khai báo nhiều thư mục:
# images_dirs:
#   - "album_2025"
#   - "album_2026"
# Hoặc quét tất cả thư mục con:
# images_dirs: "all"

# Giao diện mặc định (auto, mocha, nord, tokyo-night, rose-pine, ...)
theme: "auto"
theme_light: "rose-pine-dawn"
theme_dark: "mocha"

# Sắp xếp: name (theo tên), created (ngày cũ nhất trước), created_desc (mới nhất trước)
sort_by: "created_desc"

# Cài đặt giao diện
sticky_header: "true"
show_filename: "false"
show_created_time: "false"
show_file_size: "false"
show_video_thumbnails: "false"
```

---

## 💻 Tham số dòng lệnh (CLI Options)

Bạn có thể ghi đè cài đặt từ `config.yml` bằng các tham số CLI:

```bash
python3 build_archive.py [options]
```

| Tham số | Mô tả |
| :--- | :--- |
| `--images <path>` | Chỉ định đường dẫn thư mục media (Ghi đè `config.yml`). |
| `--output <path>` | Chỉ định đường dẫn file HTML xuất ra (Mặc định: `index.html`). |
| `--title <text>` | Đặt tiêu đề cho Archive. |
| `--theme <theme>` | Đặt theme màu sắc (Ví dụ: `mocha`, `nord`, `tokyo-night`, `latte`...). |
| `--sort-by <type>` | Kiểu sắp xếp: `name`, `created`, `created_desc`. |

**Ví dụ:**

```bash
# Tạo archive từ thư mục ./my_photos với theme Tokyo Night và sắp xếp mới nhất lên đầu
python3 build_archive.py --images ./my_photos --title "Kỷ Niệm 2026" --theme tokyo-night --sort-by created_desc --output gallery.html
```

---

## ⌨️ Phím tắt điều hướng (Keyboard Shortcuts)

Khi đang mở trang HTML Archive, bạn có thể dùng các phím tắt sau:

### Duyệt bài (Feed View)
* <kbd>J</kbd> / <kbd>↓</kbd> : Chuyển xuống bài tiếp theo.
* <kbd>K</kbd> / <kbd>↑</kbd> : Quay lại bài trước.
* <kbd>Space</kbd> / <kbd>Shift</kbd> + <kbd>Space</kbd> : Cuộn nhanh tới/lùi.
* <kbd>T</kbd> : Nhảy lên đầu trang.

### Công cụ & Thao tác
* <kbd>G</kbd> : Mở ô tìm kiếm bài viết / media.
* <kbd>L</kbd> : Thả tim (Like) bài viết đang chọn.
* <kbd>F</kbd> : Bật/tắt chế độ chỉ hiển thị bài đã thích.
* <kbd>V</kbd> : Đổi giữa chế độ **Lưới (Grid View)** và **Danh sách (Feed View)**.
* <kbd>M</kbd> : Đổi nhanh Theme giao diện.
* <kbd>E</kbd> / <kbd>I</kbd> : Export / Import dữ liệu thả tim (Backup/Restore).

### Lightbox (Xem phóng to)
* <kbd>J</kbd> / <kbd>→</kbd> : Xem media tiếp theo.
* <kbd>K</kbd> / <kbd>←</kbd> : Xem media phía trước.
* <kbd>Esc</kbd> : Đóng Lightbox.

---

## 📄 Giấy phép (License)

Mã nguồn được phát hành dưới giấy phép **MIT License**. Bạn có thể tự do sử dụng, chỉnh sửa và chia sẻ.
