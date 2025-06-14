from openai import OpenAI
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
import requests
import urllib
import pandas as pd
import json
import sys, os
import base64

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="your_openrouter_api_key"  # OpenRouterのAPIキーをここに入力,
)

GeospatialUrl = "https://msearch.gsi.go.jp/address-search/AddressSearch?q=" #国土地理院APIを使用 

keys = ["場所", "説明", "緯度", "経度"] # CSVのカラム名

model_name = "gpt-4.1-mini"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    
def extract_images_from_pdf(pdf_path, dpi=300):
    return convert_from_path(pdf_path, dpi=dpi)
    
# 使い方
if len(sys.argv) < 3:
    print("Usage: python pdf2csv.py <pdf_file> <output_csv>")
    sys.exit(1)

pdf_file = sys.argv[1]
output_csv = sys.argv[2]

images = extract_images_from_pdf(pdf_file)

df = pd.DataFrame()

for key in keys:
    df[key] = None

for i, image in enumerate(images):
    print(f"[INFO] Processing page {i+1}/{len(images)}")
    image_path = f"temp_image_{i+1}.jpg"
    image.save(image_path, "JPEG")
    
    # 画像をエンコードしてbase64形式に変換
    base64_image = encode_image(image_path)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {
            "role": "user",
            "content": [{"type": "text", "text": "この画像から住所を重複を許して抽出し、説明を加えてリスト化し、「住所」と「説明」をkeyとしたjson形式で出力してください。日本語が文字化けしないように気を付けてください。"},  # ここに質問を書く
                        {"type": "image_url", "image_url":{"url": f"data:image/jpeg;base64,{base64_image}"}},
                ]
            }
        ]
    )
    # 画像を削除
    os.remove(image_path)

    new_row = {key: None for key in keys}
    texts = completion.choices[0].message.content
    start = texts.find('[')
    end = texts.rfind(']')
    if start != -1 and end != -1 and end > start:
        texts = texts[start:end+1]
    pos_dir_list = json.loads(texts)
    for pos_dir in pos_dir_list:
        address = pos_dir.get("住所", "")
        if len(address) < 3: # 数字を送るとresponseが返ってくるため
            continue
        s_quote = urllib.parse.quote(address)
        response = requests.get(GeospatialUrl + s_quote)
        try:
            lat = response.json()[0]["geometry"]["coordinates"][1]
            lng = response.json()[0]["geometry"]["coordinates"][0]
            pos_detected = True
        except Exception as e:
            print(f"[ERROR] Could not find position for address '{address}': {e}")
            pos_detected = False
            lat = None
            lng = None
    
        if pos_detected:
            new_row["場所"] = address
            new_row["緯度"] = lat
            new_row["経度"] = lng
            new_row["説明"] = pos_dir.get("説明", "")
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
df.to_csv(output_csv, index=False)