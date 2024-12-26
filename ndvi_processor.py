import cv2
import numpy as np


class NDVIProcessor:
    def __init__(self):
        pass

    def contrast_stretch(self, im):
        in_min = np.percentile(im, 5)
        in_max = np.percentile(im, 95)
        out_min, out_max = 0.0, 255.0
        out = (im - in_min) * ((out_max - out_min) / (in_max - in_min)) + out_min
        return out

    def calculate_ndvi(self, frame):
        # Convert frame to float32 for NDVI calculation
        frame_float32 = frame.astype(np.float32)
        b, g, r = cv2.split(frame_float32)

        # Calculate NDVI
        ndvi = (g - r) / (g + r + 1e-6)

        # Apply Gaussian blur to reduce noise
        ndvi = cv2.GaussianBlur(ndvi, (5, 5), 0)

        # Convert to HSV but first ensure we're working with uint8
        frame_uint8 = frame.astype(np.uint8)
        hsv = cv2.cvtColor(frame_uint8, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Soil generally has low saturation and value in HSV, so we use this to filter out
        soil_mask = (s < 50) & (v < 50)

        # More stringent criteria for vegetation detection, considering high light conditions
        vegetation_mask = (
            (g > r * 1.5) & (g > b * 1.5) & (g > 50) & ~soil_mask
        ).astype(np.uint8)

        # Apply the mask to NDVI
        ndvi = cv2.bitwise_and(ndvi, ndvi, mask=vegetation_mask)

        return ndvi

    def detect_vegetation_regions(self, ndvi_image, threshold=0.2, min_area=2000):
        # Dynamic threshold
        adaptive_threshold = max(np.mean(ndvi_image) * 0.6, threshold)
        vegetation_mask = (ndvi_image > adaptive_threshold).astype(np.uint8)

        # Morphological operations to remove small noise and connect small regions
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        vegetation_mask = cv2.morphologyEx(vegetation_mask, cv2.MORPH_OPEN, kernel)
        vegetation_mask = cv2.morphologyEx(vegetation_mask, cv2.MORPH_CLOSE, kernel)

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            vegetation_mask, connectivity=8
        )

        regions = []
        for i in range(1, num_labels):  # Skipping label 0 which is the background
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                x, y, w, h = (
                    stats[i, cv2.CC_STAT_LEFT],
                    stats[i, cv2.CC_STAT_TOP],
                    stats[i, cv2.CC_STAT_WIDTH],
                    stats[i, cv2.CC_STAT_HEIGHT],
                )
                regions.append((x, y, w, h))

        return regions

    def analyze_region(
        self, region, ndvi_image, vegetation_mask, weak_threshold=0.3, min_weak_area=80
    ):
        x, y, w, h = region
        region_ndvi = ndvi_image[y : y + h, x : x + w]
        region_vegetation_mask = vegetation_mask[y : y + h, x : x + w]

        # Adjust weak threshold considering high light conditions might make NDVI values higher
        adjusted_weak_threshold = min(weak_threshold + 0.1, 0.5)  # Adjust as needed

        # Create a mask for weak vegetation
        weak_mask = (
            (region_ndvi > 0.2) & (region_ndvi < adjusted_weak_threshold)
        ).astype(np.uint8)
        weak_mask = cv2.bitwise_and(weak_mask, region_vegetation_mask)

        # Clean up the weak mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        weak_mask = cv2.morphologyEx(weak_mask, cv2.MORPH_CLOSE, kernel)

        # Find contours of weak areas
        contours, _ = cv2.findContours(
            weak_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        weak_areas = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_weak_area:
                x_cnt, y_cnt, w_cnt, h_cnt = cv2.boundingRect(cnt)
                weak_areas.append((x + x_cnt, y + y_cnt, w_cnt, h_cnt))

        return weak_areas if weak_areas else None