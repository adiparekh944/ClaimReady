import os
import time
from ultralytics import YOLO
import cv2

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'Room3_yolo11n_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load model
model = YOLO(MODEL_PATH)

# Read image
img = cv2.imread(IMAGE_PATH)
if img is None:
    raise FileNotFoundError(f'Could not load image: {IMAGE_PATH}')

# Run inference and time it
start = time.time()
results = model(img, verbose=True)
elapsed = time.time() - start

# Visualize results (masks + boxes)
for r in results:
    r.save(filename=OUTPUT_IMAGE, boxes=True, masks=True)

print(f'Inference completed in {elapsed:.2f} seconds.')
print(f'Results saved to: {OUTPUT_IMAGE}')

# Print detection summary
for r in results:
    print(r) 