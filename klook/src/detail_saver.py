"""
이 모듈은 브라우저 서브에이전트가 임시 덤프해 둔 Klook 상세페이지 텍스트 데이터를 
정밀 분석 및 파싱하여 구조화된 필드(상세 설명, 하이라이트, 포함/불포함 사항 등)를 
추출하고, SQLite 데이터베이스의 klook_product_details 테이블에 적재하는 파이프라인 스크립트입니다.
"""

import os
import json
import sqlite3

def init_detail_db(db_path, table_name="klook_product_details"):
    """
    상세페이지 데이터를 담을 SQLite 테이블을 생성 및 초기화합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        activity_id INTEGER PRIMARY KEY,
        description TEXT,
        highlights TEXT,
        inclusions TEXT,
        exclusions TEXT,
        how_to_use TEXT,
        cancellation_policy TEXT,
        FOREIGN KEY(activity_id) REFERENCES klook_products(activity_id)
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

def extract_section(text, start_keywords, end_keywords):
    """
    텍스트 본문에서 특정 시작 키워드군과 종료 키워드군 사이의 텍스트 파트를 스마트하게 추출합니다.
    """
    start_pos = -1
    found_keyword = ""
    for kw in start_keywords:
        pos = text.find(kw)
        if pos != -1:
            if start_pos == -1 or pos < start_pos:
                start_pos = pos
                found_keyword = kw
                
    if start_pos == -1:
        return ""
        
    start_idx = start_pos + len(found_keyword)
    
    end_pos = -1
    for kw in end_keywords:
        pos = text.find(kw, start_idx)
        if pos != -1:
            if end_pos == -1 or pos < end_pos:
                end_pos = pos
                
    if end_pos == -1:
        return text[start_idx:].strip()
    else:
        return text[start_idx:end_pos].strip()

def clean_extracted_text(text):
    """
    추출된 텍스트에서 특수문자나 중복 줄바꿈을 청소합니다.
    """
    if not text:
        return "N/A"
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return "\n".join(lines)

def process_and_save():
    db_path = "klook/data/klook_products.db"
    scratchpad_path = "C:/Users/admin/.gemini/antigravity-ide/brain/32f0d3cb-b679-471c-8b0b-fdd4947184f2/browser/scratchpad_sv6njr39.md"
    
    # 1. DB 초기화
    init_detail_db(db_path)
    
    # 2. 임시 덤프 데이터 읽기
    if not os.path.exists(scratchpad_path):
        print(f"[에러] 스크래치패드 파일이 존재하지 않습니다: {scratchpad_path}")
        return
        
    with open(scratchpad_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # JSON 영역 찾기
    json_start = content.find("```json")
    json_end = content.find("```", json_start + 7)
    
    if json_start == -1 or json_end == -1:
        print("[에러] 스크래치패드에서 JSON 데이터를 찾을 수 없습니다.")
        return
        
    json_str = content[json_start + 7 : json_end].strip()
    
    # 느슨한 JSON / 수동 정규 추출
    scraped_data = {}
    keys = ["1163", "14421", "16469", "17677", "18054", "29707", "35301", "39587", "43073"]
    for i, k in enumerate(keys):
        start_str = f'"{k}": "'
        start_idx = json_str.find(start_str)
        if start_idx == -1:
            continue
        val_start = start_idx + len(start_str)
        if i < len(keys) - 1:
            next_key = keys[i+1]
            end_idx = json_str.find(f'"{next_key}":', val_start)
        else:
            end_idx = len(json_str)
            
        if end_idx != -1:
            val_text = json_str[val_start:end_idx].strip()
            if val_text.endswith(','):
                val_text = val_text[:-1].strip()
            if val_text.endswith('"'):
                val_text = val_text[:-1].strip()
            # 이스케이프 해제
            val_text = val_text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            scraped_data[k] = val_text

    print(f"[정보] 총 {len(scraped_data)}개 상품의 수동 파싱 완료.")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for act_id_str, raw_text in scraped_data.items():
        activity_id = int(act_id_str)
        
        # 1. 상세 설명 (Description)
        # 타이틀 아래 본문 또는 OG Description 파트 추출
        description = extract_section(raw_text, ["OG Description:"], ["# "])
        if not description:
            description = extract_section(raw_text, ["# "], ["## 패키지 옵션", "## 여행스토리"])
            
        # 2. 하이라이트 (Highlights)
        # 상품의 특장점 불릿 포인트
        highlights = extract_section(raw_text, ["# "], ["## 패키지 옵션", "## 여행스토리"])
        if not highlights:
            highlights = extract_section(raw_text, ["# "], ["## 위치"])
            
        # 3. 포함 사항 (Inclusions)
        inclusions = extract_section(raw_text, ["포함 사항", "포함사항", "패키지 포함"], ["불포함", "사용방법", "이용안내", "## 위치"])
        
        # 4. 불포함 사항 (Exclusions)
        exclusions = extract_section(raw_text, ["불포함 사항", "불포함사항", "패키지 불포함"], ["사용방법", "이용안내", "## 위치"])
        
        # 5. 사용 방법 (How to use)
        how_to_use = extract_section(raw_text, ["사용방법", "이용방법", "사용 방법", "이용 방법", "이용안내", "충전 안내"], ["## 위치", "## Tip"])
        
        # 6. 취소/환불 규정 (Cancellation Policy)
        cancellation_policy = extract_section(raw_text, ["취소 규정", "환불 규정", "취소 및 환불 규정"], ["## 위치", "## Tip"])
        
        # 텍스트 청소 및 N/A 기본값 부여
        data = {
            "description": clean_extracted_text(description),
            "highlights": clean_extracted_text(highlights),
            "inclusions": clean_extracted_text(inclusions),
            "exclusions": clean_extracted_text(exclusions),
            "how_to_use": clean_extracted_text(how_to_use),
            "cancellation_policy": clean_extracted_text(cancellation_policy)
        }
        
        # 만약 포함사항이나 사용방법이 비어있다면, 전체 텍스트에서 간이 매칭을 통해 보완
        if data["inclusions"] == "N/A" and "포함" in raw_text:
            data["inclusions"] = "본문 텍스트 내 포함사항 확인 가능 (상세 정보 덤프 참조)"
            
        # DB 적재 (INSERT OR REPLACE)
        query = """
        INSERT OR REPLACE INTO klook_product_details (
            activity_id, description, highlights, inclusions, exclusions, how_to_use, cancellation_policy
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (
            activity_id,
            data["description"],
            data["highlights"],
            data["inclusions"],
            data["exclusions"],
            data["how_to_use"],
            data["cancellation_policy"]
        ))
        
        print(f"[성공] 상품 ID {activity_id} 데이터 파싱 및 SQLite 적재 완료.")
        
    conn.commit()
    conn.close()
    print("[정보] 최종 DB 연동 적재 완료!")

if __name__ == "__main__":
    process_and_save()
