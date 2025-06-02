import pandas as pd
import tabula
import sys
import os

# 使い方
if len(sys.argv) < 3:
    print("Usage: python pdf2csv.py <pdf_file> <output_dir>")
    sys.exit(1)

pdf_file = sys.argv[1]
output_dir = sys.argv[2]

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

dfs = tabula.read_pdf(pdf_file, lattice=True, pages='all')
for i, df in enumerate(dfs):
    df.to_csv(f"{output_dir}/{i+1:03}.csv", index=False)