1) HTTP 요청정보

요청 URL

https://www.klook.com/v1/cardinfocenterservicesrv/search/platform/complete_search_v3?sort=most_relevant&tab_key=0&start=2&query=%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD&size=15&search_scope=main_search&k_lang=ko_KR&k_currency=KRW

요청 메서드

GET

상태 코드

200 OK

원격 주소

리퍼러 정책

strict-origin-when-cross-origin

1. HTTP 헤더정보

accept-language

ko_KR

baggage

sentry-environment=production,sentry-release=web_ssr-platform_20260623_7acde2fb,sentry-public_key=919ae3dd598137e1aa2a88c31e161bb3,sentry-trace_id=1c6db08e2faf4ea8a73d1cc7f085f152,sentry-transaction=SearchResult,sentry-sampled=false,sentry-sample_rand=0.2335752950523433,sentry-sample_rate=0

cache-control

no-cache

cookie

_cfuvid=HJ2CSa9a4ovDFxM6WCXfG67ERackBjJJEAo7of0aO9Q-1782301453.2290957-1.0.1.1-VBkXYwaaBGb8OcPAGtIXrZ6Ro1uQSe0gt5Def9H5SiU; kepler_id=2cdd3af6-1db0-4cdb-93c4-b276737adfe1; klk_currency=KRW; klk_rdc=KR; klk_ps=1; _gcl_au=1.1.138209614.1782301464; __lt__cid=98578f95-5d49-44c8-a06f-d5f7a3ac9028; __lt__cid.c83939be=98578f95-5d49-44c8-a06f-d5f7a3ac9028; __lt__sid=b5f51369-7724be65; __lt__sid.c83939be=b5f51369-7724be65; _cq_duid=1.1782301467.DVLqjGc3icmqEIdq; _cq_suid=1.1782301467.TEP0ZcyJYUjb4usz; _twpid=tw.1782301467611.563098177178714437; _yjsu_yjad=1782301467.c4449df4-6b25-441a-bd04-d352cb2ef11b; _fwb=253GCp1FDfpcyr0lCQLBUUL.1782301467957; wcs_bt=s_2cb388a4aa34:1782301467; _cq_s=dQHJ0iWoymbFDxRZ:LFpAL1QgiyuVMGg5qcRRbtFhIAbSpacuBa+ZxkOKW068CJIhodFEypCEVLZlUI/WP7DVyG/OfiJrhvYT5HMVJHAW+ZcZhBnXYrOXEpYTzp8XaEJUcOLu8+ixZQhaLKVeyNegdA==:TLNv14kQ2shElDXxsecoPQ==; _uetsid=0f9c98b06fc211f1b39567825dc417d0; _uetvid=0f9cda206fc211f18522a50192f29db6; _tguatd=eyJzYyI6IihkaXJlY3QpIiwiZnRzIjoiKGRpcmVjdCkifQ==; _tgpc=162d7123-f6b8-4949-bee9-d5437d6f7989; _tgidts=eyJzaCI6ImQ0MWQ4Y2Q5OGYwMGIyMDRlOTgwMDk5OGVjZjg0MjdlIiwiY2kiOiJmMjJmMjVjNS00ZGY2LTQxNTAtYTRjNy02NjA4M2Y4ZDgxODciLCJzaSI6ImNiODRhZGM5LWJiMmYtNDNlZi04N2JjLTliMGM0ZGVhZTFiZCJ9; _tglksd=eyJzIjoiY2I4NGFkYzktYmIyZi00M2VmLTg3YmMtOWIwYzRkZWFlMWJkIiwic3QiOjE3ODIzMDE0NzExMDUsInNvZCI6IihkaXJlY3QpIiwic29kdCI6MTc4MjMwMTQ3MTEwNSwic29kcyI6Im8iLCJzb2RzdCI6MTc4MjMwMTQ3MTEwNX0=; _tt_enable_cookie=1; _ttp=01KVWQ4CRMX3HF191WK1JGS6T4_.tt.1; _ga=GA1.1.1034969751.1782301473; _ga_HSY7KJ18X2=GS2.1.s1782301469$o1$g0$t1782301469$j60$l0$h0; dable_uid=23109638.1782301468427; klk_sessionid=MQ.b53d9bfb0e2348fc5ca6e90f3673f018; JSESSIONID=A6A419EAAAD6DFD59EDB27CD4FF05E8C; KOUNT_SESSION_ID=A6A419EAAAD6DFD59EDB27CD4FF05E8C; clientside-cookie=4e53035018d73abab97c1ca730ef7bc949759303215a110451ab8aec96d0b7fa03e615c5d777d992dbd3b54954f7a7c4977a41372451bc4d2b34d39b1ccc22fc523ece66995049dc6358a4a9a9543d176174afa994401f1b58ba78d1ac46c26a2583547d379846e7e7b5a1a412a0e9c57cd6f91e023cc07147c3b6323311944fdbf27d50fc17d1e3b8243f4d363dfb8bdf3efef9ea2bac4d39cf; forterToken=a40ec7b19ca04c3c94a74f3519b933fb_1782301475433__UDF43-m4_21ck_; _tgsid=eyJscGQiOiJ7XCJscHVcIjpcImh0dHBzOi8vd3d3Lmtsb29rLmNvbSUyRmtvJTJGc2VhcmNoJTJGcmVzdWx0JTJGXCIsXCJscHRcIjpcIktsb29rJTIwVHJhdmVsXCIsXCJscHJcIjpcIlwifSIsInBzIjoiOWQyMmU2OGUtZWE1OS00MGUyLWEzMTctODBkMTc4YTBkNjczIiwicHZjIjoiMSIsInNjIjoiY2I4NGFkYzktYmIyZi00M2VmLTg3YmMtOWIwYzRkZWFlMWJkOi0xIiwiZWMiOiIzIiwicHYiOiIxIiwidGltIjoiY2I4NGFkYzktYmIyZi00M2VmLTg3YmMtOWIwYzRkZWFlMWJkOjE3ODIzMDE0NzQxMjQ6LTEifQ==; klk_gl_sess=c46ff7640b89..1782301473975..1782301780298; klk_i_sn=9451298682..1782301792310; _ga_FW3CMDM313=GS2.1.s1782301469$o1$g1$t1782301793$j60$l0$h0; _cq_session=1.1782301467302.kHA5ftT6PUWuf8CG.1782301801127; datadome=WIS~6SUahcDU6TdvFJVjfpChE7oavuwf3t6Eyd1si_IcSz2Ff1CgdNu4on9S2Z51AP4Zw0aB_VdnIZ84tEteeacDPb4KMDo8GUm9lZQsutCQmIvdzq6MAfg3nyieFKLX; klk_ga_sn=0791210182..1782301804487; ttcsid_C1SIFQUHLSU5AAHCT7H0=1782301471519::0m8Xg1g_z7vkhTJxHmN-.1.1782301804517.1; ttcsid=1782301471521::fQV44Y_i-WwiKOUgiyVZ.1.1782301804517.0::1.332967.0::332528.3.941.2119::332809.14.484; _ga_V8S4KC8ZXR=GS2.1.s1782301466$o1$g1$t1782301804$j49$l0$h2135634172

currency

KRW

priority

u=1, i

referer

https://www.klook.com/ko/search/result/?query=%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD&search_scope=main_search&sort=most_relevant&tab_key=0&start=2

sec-ch-device-memory

16

sec-ch-ua

"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"

sec-ch-ua-arch

"x86"

sec-ch-ua-full-version-list

"Google Chrome";v="149.0.7827.158", "Chromium";v="149.0.7827.158", "Not)A;Brand";v="24.0.0.0"

sec-ch-ua-mobile

?0

sec-ch-ua-model

""

sec-ch-ua-platform

"Windows"

sec-fetch-dest

empty

sec-fetch-mode

cors

sec-fetch-site

same-origin

sentry-trace

1c6db08e2faf4ea8a73d1cc7f085f152-b1ace28d04f1ad2c-0

token

user-agent

Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36

version

5.6

x-klook-affiliate-aid

x-klook-affiliate-pid

x-klook-channel-level-one

Direct

x-klook-host

www.klook.com

x-klook-kepler-id

2cdd3af6-1db0-4cdb-93c4-b276737adfe1

x-klook-market

global

x-klook-page-open-id

x-klook-tint

{"kepler":["253:861","669:3215","684:3546","694:3666","695:3674","706:3783","732:4304","741:4469","761:4623","768:4732","778:4887","779:4897","780:4904","787:4996","788:5005","818:5278","822:5363","851:5735","853:5740","854:5751","855:5752","871:5974","877:6067","885:6185","901:6288","910:6455","931:6736","933:6751","936:9309","948:7023","969:7423","970:7425","978:7536","980:7551","994:7879","1006:8210","1016:8314","1017:8338","1020:8414","1038:8663","1058:9017","1084:9630","1091:9724","1128:10287","1147:10834","1171:11684","1172:11691","1180:11872","1191:12047","1193:12099","1205:12358","1206:12362","1209:12385","1219:12858","1226:13132","1229:13466","1233:13338","1243:13403","1245:13481","1264:13863","1295:15296","1298:15429","1304:15491","1309:15662","1315:15687","1334:16011","1339:16217","1340:16222","1350:16662","1351:16664","1358:16742","1364:16919","1369:17000","1371:17010","1372:17052","1375:17136","1378:17204","1379:17207","1382:17315","1386:17615","1397:18048","1487:20706","1522:22730","1533:21689","1537:21796","1572:22732","1573:22735","1574:22738","1599:23643","1600:23647","1602:24273","1604:24849","1605:24270","1606:24267","1664:24744","1665:24751","1666:24760","1691:26210","1692:26200","1693:26203","1694:26859","1695:26856","1696:26853","1697:26193","1702:25542","1741:26400","1748:26626","1749:30652","1887:30172","1901:30291","1903:30331","1909:30461","1914:32288","1915:32292","1916:32296","1918:30619","1919:30623","1921:30870","1922:30755","1926:30897","1930:30926","1956:31533","1963:31519","1992:32257","2003:32588","2014:32761","2016:32825","2018:32881","2019:32887","2022:32948","2031:33250","2058:33418","2074:33686","2078:33785","2079:33788","2080:33790","2081:33794","2082:33833"]}

x-klook-user-residence

10_KR

x-platform

desktop

x-requested-with

XMLHttpRequest

5) Payload 정보

sort=most_relevant&tab_key=0&start=2&query=%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD&size=15&search_scope=main_search&k_lang=ko_KR&k_currency=KRW

7) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)

{
    "success": true,
    "error": {
        "code": "",
        "message": ""
    },
    "result": {
        "search_result": {
            "total": 1000,
            "cards": [
                {
                    "data": {

9) 한페이지가 성공적으로 수집되는지 확인하고 csv 파일로 저장할 것
