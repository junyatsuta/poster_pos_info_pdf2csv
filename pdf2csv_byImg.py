import pandas as pd
import tabula
import sys
import os
import requests
import urllib
import folium
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from PIL import Image

GeospatialUrl = "https://msearch.gsi.go.jp/address-search/AddressSearch?q=" #国土地理院APIを使用 
keys = ["場所", "説明", "緯度", "経度"] # CSVのカラム名

def extract_lines_from_pdf(pdf_path, dpi=300):
    images = convert_from_path(pdf_path, dpi=dpi)
    lines = []

    for i, img in enumerate(images):
        print(f"[INFO] Detecting lines on page {i+1}/{len(images)}")

        open_cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        _, binary_inv = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        binary = cv2.bitwise_not(binary_inv) 
        
        # 水平・垂直線検出
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        horizontal_lines = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, vertical_kernel)

        table_mask = cv2.add(horizontal_lines, vertical_lines)

        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        page_lines = []

        for cnt in contours[::-1]:  # 逆順に処理
            x, y, w, h = cv2.boundingRect(cnt)
            roi = binary[y:y+h, x:x+w]
            roi_pil = Image.fromarray(roi)
            cell_text = pytesseract.image_to_string(roi_pil, config='--psm 6', lang='jpn')
            page_lines.append(cell_text.strip())
        
        lines.extend(page_lines)

    return lines


# 使い方
if len(sys.argv) < 3:
    print("Usage: python pdf2csv.py <pdf_file> <output_csv>")
    sys.exit(1)

pdf_file = sys.argv[1]
output_csv = sys.argv[2]

pdf_lines = extract_lines_from_pdf(pdf_file)

df = pd.DataFrame()

for key in keys:
    df[key] = None

for line in pdf_lines:
    new_row = {key: None for key in keys}
    texts = [t for t in line.split(" ") if t]
    for i, text in enumerate(texts):
        if len(text) < 5: # 数字を送るとresponseが返ってくるため
            continue
        s_quote = urllib.parse.quote(text)
        response = requests.get(GeospatialUrl + s_quote)
        try:
            lat = response.json()[0]["geometry"]["coordinates"][1]
            lng = response.json()[0]["geometry"]["coordinates"][0]
            pos_detected = True
        except Exception as e:
            pos_detected = False
            lat = None
            lng = None
        
        if pos_detected:
            new_row["場所"] = text
            new_row["緯度"] = lat
            new_row["経度"] = lng
            if i < len(texts) - 1:
                new_row["説明"] = " ".join(texts[i+1:])
            else:
                new_row["説明"] = None
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            break
df.to_csv(output_csv, index=False)