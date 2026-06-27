"""
이 모듈은 scrapling 라이브러리를 사용하여 trip.com 호텔 리뷰 API에 데이터를 요청하고 
정상적으로 응답을 받는지 테스트하는 스크립트입니다.

주요 기능:
- trip.com 리뷰 API(POST) 호출
- 요청 헤더 및 페이로드 데이터 전달 테스트
- 응답 데이터 수신 및 파싱 성공 여부 확인
"""

import json
from scrapling import Fetcher

# 테스트용 URL과 헤더, 페이로드 설정
url = "https://kr.trip.com/restapi/soa2/34308/getHotelCommentInfo"

headers = {
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "w-payload-source": "1.0.9@102!Nudtz1KLhCAbOX4SO6An9PKnG2KLOSqZOlbn+6FaG6OaKSbpKET2OSVbOrK2+ET5+rApbbbpOSknKr42+rG2KlqIbEVbKtb5+rbSOEb2KE4p+rKpOr4nKrq/K5bpOSqL+rk/OSKZKrVpQlVROShDKFO3GVd3hbb=",
    "x-ctx-country": "KR",
    "x-ctx-currency": "KRW",
    "x-ctx-locale": "ko-KR",
    "x-ctx-ubt-pageid": "10320668147",
    "x-ctx-ubt-pvid": "7",
    "x-ctx-ubt-sid": "9",
    "x-ctx-ubt-vid": "1754985737191.9877n1SlbHlt",
    "x-ctx-user-recognize": "NON_EU",
    "x-ctx-wclient-req": "0af33fe7acb74bcfe9f82cf404544b46",
    "content-type": "application/json"
}

payload = {
    "hotelId": 58635410,
    "commentFilterOptions": {
        "pageIndex": 1,
        "pageSize": 10,
        "repeatComment": 1
    },
    "sceneTypes": ["CommentList"],
    "head": {
        "platform": "PC",
        "cver": "0",
        "cid": "1754985737191.9877n1SlbHlt",
        "bu": "IBU",
        "group": "trip",
        "aid": "",
        "sid": "",
        "ouid": "",
        "locale": "ko-KR",
        "timezone": "9",
        "currency": "KRW",
        "pageId": "10320668147",
        "vid": "1754985737191.9877n1SlbHlt",
        "guid": "",
        "isSSR": False
    }
}

def main():
    # scrapling Fetcher 생성
    fetcher = Fetcher(auto_match=False)
    
    print("데이터 수집 요청을 보냅니다...")
    try:
        # scrapling의 fetcher.post()를 이용해 API 요청
        response = fetcher.post(url, headers=headers, json=payload)
        
        print("Response attributes:", dir(response))
        # status 혹은 status_code 확인을 위해 둘 다 출력 시도
        if hasattr(response, 'status'):
            print("response.status:", response.status)
        if hasattr(response, 'status_code'):
            print("response.status_code:", response.status_code)
            
        print("url:", response.url)
        print("headers:", response.headers)
        
        # response.json() 사용을 먼저 시도
        try:
            data = response.json()
            print("response.json() 성공!")
            
            # 데이터를 파일로 저장
            import os
            os.makedirs("trip_com/data", exist_ok=True)
            with open("trip_com/data/sample_comment.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("샘플 데이터를 trip_com/data/sample_comment.json 파일에 저장했습니다.")
            
            # 구조 파악을 위해 최상위 키들 출력
            if "data" in data:
                print("data 키의 서브 키들:", data["data"].keys())
                # 예시로 몇 개의 리뷰 정보 출력
                # 리뷰 리스트가 어느 키에 들어있는지 확인하기 위해 키 목록을 기반으로 추정 가능
        except Exception as json_e:
            print("response.json() 실패:", json_e)
            
    except Exception as e:
        print("요청 중 오류 발생:", e)

if __name__ == "__main__":
    main()
