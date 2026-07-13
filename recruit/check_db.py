"""
이 모듈은 planning_mismatch_report.html 내부에 인코딩된 base64 바이너리 데이터를 
디코딩하여 실제 수치형 구직자 공급 및 기업 수요 데이터를 확인하는 임시 도구입니다.
"""

import base64
import numpy as np

def decode_data():
    # 1. 구직자 공급 데이터 디코딩 (int32 / i4)
    y_base64 = "4C4AAHAXAABQRgAAlBEAAEAfAAAoIwAA8FUAAJg6AAC4iAAAYG0AAMivAAA="
    y_bytes = base64.b64decode(y_base64)
    y_data = np.frombuffer(y_bytes, dtype=np.int32)
    
    # 2. 기업 수요 데이터 디코딩 (int16 / i2)
    y2_base64 = "AgACAAcAFAAKAD8AgwABAJkAYQAeAA=="
    y2_bytes = base64.b64decode(y2_base64)
    y2_data = np.frombuffer(y2_bytes, dtype=np.int16)
    
    x_labels = ["ADsP", "CFA", "CPA", "Figma", "GA4", "M&A", "PPT작성법", "SQLD", "데이터분석", "시장조사", "컴퓨터활용능력"]
    
    print("Decoded Data for Planning/Strategy Job:")
    for label, supply, demand in zip(x_labels, y_data, y2_data):
        print(f"  - Skill: {label:12} | Supply (User interest): {supply:5d} | Demand (Job openings): {demand:5d}")

if __name__ == "__main__":
    decode_data()
