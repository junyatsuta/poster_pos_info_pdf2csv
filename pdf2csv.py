import pandas as pd
import tabula
import sys
import os
import requests
import urllib
import folium

GeospatialUrl = "https://msearch.gsi.go.jp/address-search/AddressSearch?q=" #国土地理院APIを使用 
keys = ["場所", "説明", "緯度", "経度"] # CSVのカラム名
pos_words = ["ポスター掲示場の設置場所"] # PDF内のポスター掲示場の設置場所を表すカラム名
exp_words = ["設置場所の目標"] # PDF内の設置場所の目標を表すカラム名


# 使い方
if len(sys.argv) < 3:
    print("Usage: python pdf2csv.py <pdf_file> <output_csv>")
    sys.exit(1)

pdf_file = sys.argv[1]
output_csv = sys.argv[2]

pdf_dfs = tabula.read_pdf(pdf_file, lattice=True, pages='all')

df = pd.DataFrame()

for key in keys:
    df[key] = None

for pdf_df in pdf_dfs[1:]:
    found_pos_word = None
    for pos_word in pos_words:
        if pos_word in pdf_df.columns:
            found_pos_word = pos_word
            break
    if found_pos_word is None:
        print("Error: No position word found in the PDF.")
        sys.exit(1)
    
    found_exp_word = None
    for exp_word in exp_words:
        if exp_word in pdf_df.columns:
            found_exp_word = exp_word
            break
    
    for i, pos in enumerate(pdf_df[found_pos_word].values):
        s_quote = urllib.parse.quote(pos)
        response = requests.get(GeospatialUrl + s_quote)
        try:
            lat = response.json()[0]["geometry"]["coordinates"][1]
            lng = response.json()[0]["geometry"]["coordinates"][0]
        except Exception as e:
            print(f"Error fetching coordinates for {pos}: {e}")
            lat = None
            lng = None
        
        new_row = {
            "場所": pos,
            "説明": None if found_exp_word is None else pdf_df[found_exp_word].values[i],
            "緯度": lat,
            "経度": lng,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

df.to_csv(output_csv, index=False)