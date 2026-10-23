# Claudou for Windows 🚀

> **Mở nhiều tài khoản Claude Desktop trên một máy Windows**

## Cách hoạt động

Claude Desktop (bản Microsoft Store) lưu toàn bộ data (session, đăng nhập, config) vào thư mục:
```
%LOCALAPPDATA%\Claude-Data\claude_pzs8sxrjxfjjc\
```

Claudou tạo nhiều "profile" (thư mục riêng biệt) và trước mỗi lần launch, chuyển hướng **Directory Junction** của thư mục trên sang profile được chọn. Mỗi profile hoàn toàn độc lập.

## Cài đặt & Chạy

### Chạy trực tiếp (cần Python)

```powershell
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Chạy app (cần quyền Admin để tạo junction)
python claudou.py
```

> **Lưu ý:** App sẽ tự yêu cầu quyền Administrator khi khởi động (cần để tạo directory junction).

### Build file .exe

```powershell
pip install pyinstaller
.\build_exe.ps1
# File exe tạo ra tại: dist\Claudou.exe
```

## Hướng dẫn sử dụng

1. **Tạo Profile**: Nhấn **＋ Tạo Profile Mới** → đặt tên, chọn emoji và màu sắc
2. **Mở Claude**: Nhấn **▶ Mở** hoặc double-click vào profile card
3. **Quản lý**: Nhấn **⋮** để đổi tên hoặc xóa profile
4. **Đổi account**: Đóng Claude hiện tại → nhấn **▶ Mở** với profile khác

## Cấu trúc dữ liệu

```
%LOCALAPPDATA%\Claudou\
├── config.json           # Danh sách profiles và metadata
└── profiles\
    ├── default\          # Profile mặc định (data riêng)
    ├── cong_ty_a\        # Profile Công ty A
    └── ca_nhan\          # Profile cá nhân
```

## Lưu ý quan trọng

- ⚠️ **Cần đóng Claude trước** khi chuyển sang profile khác
- ⚠️ **Cần quyền Admin** để tạo directory junction (app tự yêu cầu)
- ✅ Mỗi profile có session đăng nhập, lịch sử chat, và MCP config riêng
- ✅ Hỗ trợ Claude Desktop bản Microsoft Store (MSIX)

## Yêu cầu hệ thống

- Windows 10/11
- Python 3.12+ (nếu chạy từ source)
- Claude Desktop (Microsoft Store version)
- Quyền Administrator
