"""
이 스크립트는 브라우저 서브에이전트가 로컬 리포트 파일 및 차트 이미지를 
허용된 디렉터리 내에서 안전하게 읽고 검증할 수 있도록 
관련 분석 산출물들을 서브에이전트 영역으로 복사하는 복사 모듈입니다.
"""

import os
import sys
import shutil

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

def main():
    target_dir = r"C:\Users\admin\.gemini\antigravity-ide\brain\e7b680c8-3052-4b5c-a3ec-e67e39a0173c\browser"
    
    src_md = 'seoul-pops/report/eda_report.md'
    src_html = 'seoul-pops/report/eda_report.html'
    src_images = 'seoul-pops/images'
    
    dest_md = os.path.join(target_dir, 'eda_report.md')
    dest_html = os.path.join(target_dir, 'eda_report.html')
    dest_images_dir = os.path.join(target_dir, 'images')
    
    print(f"1. 마크다운 복사 중: {src_md} -> {dest_md}")
    shutil.copy2(src_md, dest_md)
    
    print(f"2. HTML 복사 중: {src_html} -> {dest_html}")
    shutil.copy2(src_html, dest_html)
    
    print(f"3. 이미지 폴더 복사 중: {src_images} -> {dest_images_dir}")
    if os.path.exists(dest_images_dir):
        shutil.rmtree(dest_images_dir)
    shutil.copytree(src_images, dest_images_dir)
    
    print("모든 파일 복사가 성공적으로 완료되었습니다!")

if __name__ == '__main__':
    main()
