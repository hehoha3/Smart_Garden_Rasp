import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import cv2
import numpy as np

from ndvi_processor import NDVIProcessor

# Cấu hình thư mục lưu ảnh
BASE_DIR = "data"
MORNING_DIR = os.path.join(BASE_DIR, "today_morning")
EVENING_DIR = os.path.join(BASE_DIR, "today_evening")
YESTERDAY_DIR = os.path.join(BASE_DIR, "yesterday")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(MORNING_DIR, exist_ok=True)
os.makedirs(EVENING_DIR, exist_ok=True)
os.makedirs(YESTERDAY_DIR, exist_ok=True)


# Hàm dừng HTTP server
def stop_http_server(port=8080):
    result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.splitlines():
            if "LISTEN" in line:
                pid = int(line.split()[1])  # PID ở cột thứ hai
                os.kill(pid, 9)
                print(f"Stopped process {pid} on port {port}")


# Hàm khởi động HTTP server
def start_http_server():
    stop_http_server(8080)  # Dừng server đang chạy trên cổng 8080 nếu có
    subprocess.Popen(["python3", "-m", "http.server", "8080"], cwd=BASE_DIR)


# Hàm xử lý ngắt (Ctrl+C)
def signal_handler(sig, frame):
    print("Cleaning up resources...")
    stop_http_server(8080)
    sys.exit(0)


# Đăng ký xử lý tín hiệu ngắt
signal.signal(signal.SIGINT, signal_handler)


# Hàm chụp ảnh
def capture_images(save_dir, num_images=15):
    camera = cv2.VideoCapture(2)  # Sử dụng camera USB (có thể thay đổi nếu cần)
    if not camera.isOpened():
        print("Error: Could not open webcam.")
        return None

    processor = NDVIProcessor()
    weak_plant_count = 0  # Đếm số lượng ảnh đã lưu

    # Lấy thời gian bắt đầu
    start_time = time.time()
    last_capture_time = None  # Thời điểm chụp ảnh cuối cùng

    print("Chờ 5 giây trước khi chụp ảnh đầu tiên...")

    while weak_plant_count < num_images:
        current_time = time.time()
        elapsed_time = current_time - start_time

        # Kiểm tra nếu đủ 5 giây để chụp ảnh đầu tiên
        if last_capture_time is None and elapsed_time < 5:
            continue

        # Kiểm tra nếu đủ 1 giây kể từ lần chụp gần nhất
        if last_capture_time is not None and (current_time - last_capture_time) < 1:
            continue

        ret, frame = camera.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Cập nhật thời gian chụp ảnh cuối cùng
        last_capture_time = current_time

        # Convert frame to correct color format if necessary
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        # Tính NDVI và phân tích vùng thực vật
        new_frame = processor.contrast_stretch(frame)
        ndvi_values = processor.calculate_ndvi(new_frame)
        vegetation_mask = (ndvi_values > 0.2).astype(np.uint8)

        # Tìm các vùng thực vật
        regions = processor.detect_vegetation_regions(ndvi_values, min_area=2000)

        # Kiểm tra và lưu ảnh
        highlighted_frame = frame.copy()
        if regions:
            for region in regions:
                x, y, w, h = region
                region_frame = frame[y : y + h, x : x + w]

                weak_areas = processor.analyze_region(
                    region,
                    ndvi_values,
                    vegetation_mask,
                    weak_threshold=0.3,
                    min_weak_area=80,
                )

                if weak_areas:
                    for weak_area in weak_areas:
                        wx, wy, ww, wh = weak_area
                        cv2.rectangle(
                            highlighted_frame,
                            (x + wx, y + wy),
                            (x + wx + ww, y + wy + wh),
                            (0, 0, 255),
                            2,
                        )

            # Lưu ảnh vào thư mục chỉ định
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(save_dir, f"image_{weak_plant_count + 1}.jpg")
            cv2.imwrite(image_path, highlighted_frame)
            weak_plant_count += 1

        # Hiển thị ảnh
        cv2.imshow("Captured Frame", highlighted_frame)

        # Xử lý sự kiện nhấn phím
        if cv2.waitKey(1) & 0xFF == ord("q"):  # Thoát khi nhấn phím 'q'
            print("Nhấn phím 'q' để thoát.")
            break

    camera.release()
    cv2.destroyAllWindows()  # Đóng tất cả cửa sổ OpenCV


# Hàm xóa ảnh cũ và di chuyển ảnh vào thư mục hôm qua
def clear_and_move_images():
    # Di chuyển ảnh từ thư mục sáng và chiều vào thư mục hôm qua
    for file in os.listdir(EVENING_DIR):
        os.rename(os.path.join(EVENING_DIR, file), os.path.join(YESTERDAY_DIR, file))

    for file in os.listdir(MORNING_DIR):
        os.remove(os.path.join(MORNING_DIR, file))


# Hàm xử lý lịch chụp ảnh
def main():
    start_http_server()  # Khởi động HTTP Server

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        if current_time == "19:23":  # Chụp ảnh sáng
            print("Chụp ảnh buổi sáng...")
            capture_images(MORNING_DIR)

        elif current_time == "18:00":  # Chụp ảnh chiều
            print("Chụp ảnh buổi chiều...")
            capture_images(EVENING_DIR)

        elif current_time == "23:59":  # Xóa ảnh sáng và chuyển ảnh chiều vào hôm qua
            print("Xóa ảnh buổi sáng và lưu ảnh hôm qua...")
            clear_and_move_images()

        time.sleep(60)  # Kiểm tra mỗi phút


if __name__ == "__main__":
    main()