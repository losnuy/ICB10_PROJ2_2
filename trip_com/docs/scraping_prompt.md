trip_com 에 다음 방법으로 데이터 수집하고 저장 

https://scrapling.readthedocs.io/en/latest/
을 사용해서 다음 경로의 호텔 리뷰를 모두 수집할 것, 이때, 첫페이지 데이터를 수집하고 리뷰 제목과 내용 별점이 제대로 수집이 되었다면 전체 리뷰를 수집하는 방법으로 진행할 것 https://kr.trip.com/hotels/detail/?cityEnName=Seoul&cityId=274&hotelId=58635410&checkIn=2026-06-22&checkOut=2026-06-23&adult=2&children=0&crn=1&ages=&curr=KRW&barcurr=KRW&hoteluniquekey=H4sIAAAAAAAA_-M6wcTFJMEkdZCJo3XuntdsQoxGBiv5La5mOR7-qhHTX1Tg4Nn6OnCHnGSRQwBPIQMYuDjMYJz08pf0RkbNmP5DXzOsHHYwMp1gbGtmWcD050OzwykWZo6XepdYDjFGVytlp1YqWZnoKJVkluSkKlkpvd7W8GoDCL3ZOeNNyw4lHaWU1OJkoASQlZibX5pXAmSbWloa6xkYAIVKEis8U8AGJCfmJJfmJJakhlQWAA0y01HKLHYuKcosCErNzSwpSQWqSkvMKU4FiQelFgNlksGCSn5AY4qgApn5eRDtBihiYYk5pakQNwAtdEuF2mFYG_uIhSk69hMLwy-gn1a5NrEydLEyTGJl4QB6dhcrR4iRc6CHka7hBdYNJ1ikFA0NDAyMTE2NzHUNEi0Tk40NknRNLE0NjE11DY1NDQ0szDR65y7_8c7YSPYUo5ShuamJpYWpubG5oaWhnqWFuXmeYXBOkkdOiQdjEJuloYWbi1uUDRezd1C4YMam-nlsPEX2UiCeIoynBeIZwniBsjtV9sYFuNpHwkSSWLPzdb2DMlaKFjA2MDJ1MXILMHowRjBWAHmMqxgZNjAy7mD8DwOMrxhB5gEA1rgozBECAAA&masterhotelid_tracelogid=100025527-0a9ac30b-495035-1351086&detailFilters=17%7C1%7E17%7E1*80%7C2%7C1%7E80%7E2*29%7C1%7E29%7E1%7C2&hotelType=normal&display=incavg&subStamp=714&isCT=true&isFlexible=F&locale=ko-KR


1) HTTP 요청정보
Request URL
https://kr.trip.com/restapi/soa2/34308/getHotelCommentInfo
Request Method
POST
Status Code
200 OK
Remote Address
23.32.56.163:443
Referrer Policy
strict-origin-when-cross-origin


2) HTTP 헤더정보
sec-ch-ua
"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
w-payload-source
1.0.9@102!Nudtz1KLhCAbOX4SO6An9PKnG2KLOSqZOlbn+6FaG6OaKSbpKET2OSVbOrK2+ET5+rApbbbpOSknKr42+rG2KlqIbEVbKtb5+rbSOEb2KE4p+rKpOr4nKrq/K5bpOSqL+rk/OSKZKrVpQlVROShDKFO3GVd3hbb=
x-ctx-country
KR
x-ctx-currency
KRW
x-ctx-locale
ko-KR
x-ctx-ubt-pageid
10320668147
x-ctx-ubt-pvid
7
x-ctx-ubt-sid
9
x-ctx-ubt-vid
1754985737191.9877n1SlbHlt
x-ctx-user-recognize
NON_EU
x-ctx-wclient-req
0af33fe7acb74bcfe9f82cf404544b46

3) Payload 정보

{"hotelId":58635410,"commentFilterOptions":{"pageIndex":2,"pageSize":10,"repeatComment":1},"sceneTypes":["CommentList"],"head":{"platform":"PC","cver":"0","cid":"1754985737191.9877n1SlbHlt","bu":"IBU","group":"trip","aid":"","sid":"","ouid":"","locale":"ko-KR","timezone":"9","currency":"KRW","pageId":"10320668147","vid":"1754985737191.9877n1SlbHlt","guid":"","isSSR":false}}

4) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)


data
: 
{commentTagList: 



5) 한페이지가 성공적으로 수집되는지 확인하고 csv 파일로 저장할 것