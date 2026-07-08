"""
이 스크립트는 생성된 마크다운 보고서(eda_report.md)를 HTML 파일로 변환하여
브라우저 서브에이전트가 시각적으로 레이아웃, 차트 렌더링, 테이블 정합성을 
쉽게 검증할 수 있도록 돕는 렌더링 모듈입니다.
"""

import os
import sys
from markdown_it import MarkdownIt

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

def main():
    md_path = 'seoul-pops/report/eda_report.md'
    html_path = 'seoul-pops/report/eda_report.html'
    
    if not os.path.exists(md_path):
        print(f"Error: 마크다운 파일이 존재하지 않습니다. ({md_path})", file=sys.stderr)
        sys.exit(1)
        
    print(f"1. 마크다운 보고서 읽는 중: {md_path}")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
        
    print("2. HTML 렌더링 수행 중 (markdown-it-py)...")
    parser = MarkdownIt()
    rendered_body = parser.render(md_text)
    
    # 깃허브 마크다운 느낌의 깔끔한 스타일 적용
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>서울시 생활인구 EDA 보고서 검증</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 0 auto;
            padding: 45px;
            color: #24292e;
            background-color: #ffffff;
        }}
        h1, h2, h3, h4 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        table {{
            border-spacing: 0;
            border-collapse: collapse;
            margin-top: 0;
            margin-bottom: 16px;
            width: 100%;
        }}
        table th, table td {{
            padding: 6px 13px;
            border: 1px solid #dfe2e5;
        }}
        table tr {{
            background-color: #ffffff;
            border-top: 1px solid #c6cbd1;
        }}
        table tr:nth-child(2n) {{
            background-color: #f6f8fa;
        }}
        img {{
            max-width: 100%;
            box-sizing: border-box;
            border: 1px solid #dfe2e5;
            border-radius: 4px;
            margin: 15px 0;
        }}
        blockquote {{
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            margin: 0 0 16px 0;
            background-color: #f6f8fa;
        }}
        pre {{
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: #f6f8fa;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    {rendered_body}
</body>
</html>
"""
    
    print(f"3. HTML 파일 저장 중: {html_path}")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(styled_html)
        
    print("HTML 렌더링 작업이 완료되었습니다!")

if __name__ == '__main__':
    main()
