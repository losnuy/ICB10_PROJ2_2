# 1) HTTP 요청정보
- **Target URL**: `https://www.yes24.com/Product/Category/BestSeller`
- **HTTP Method**: GET
- **Headers**:
  - `User-Agent`: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

# 2) Payload 정보
- **Query Parameters**:
  - `categoryNumber`: `001` (종합 베스트셀러 기본값)
  - `pageNumber`: 수집 대상 페이지 번호 (예: `1`, `2`, `3` 등)
  - `pageSize`: `24` (한 페이지당 출력 개수 기본값)

# 3) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)
```html
<li class="" data-goods-no="192145622" data-iy-no="0" data-statgb="01">
 <div class="itemUnit">
  <div class="item_img">
   <div class="img_canvas">
    <div class="img_upper">
     <em class="ico rank">1</em>
    </div>
    <span class="img_item">
     <span class="img_grp">
      <a class="lnk_img" href="/product/goods/192145622">
       <img alt="도서 제목" class="lazy" data-original="https://image.yes24.com/goods/192145622/L"/>
      </a>
     </span>
    </span>
   </div>
  </div>
  <div class="item_info">
   <div class="info_row info_name">
    <a class="gd_name" href="/product/goods/192145622">도서 제목</a>
   </div>
   <div class="info_row info_pubGrp">
    <span class="authPub info_auth"><a href="...">저자 이름</a></span>
    <span class="authPub info_pub"><a href="...">출판사</a></span>
    <span class="authPub info_date">출판일</span>
   </div>
   <div class="info_row info_price">
    <span class="txt_sale"><em class="num">10</em>%</span>
    <strong class="txt_num"><em class="yes_b">7,650</em>원</strong>
    <span class="txt_num dash"><em class="yes_m">8,500</em>원</strong>
   </div>
   <div class="info_row info_rating">
    <span class="saleNum">판매 145,650</span>
    <span class="rating_rvCount"><em class="txC_blue">5</em>건</span>
    <span class="rating_grade"><em class="yes_b">10.0</em></span>
   </div>
  </div>
 </div>
</li>
```

# 4) 한페이지가 성공적으로 수집되는지 확인하기
- **검증 스크립트 실행 결과**:
  - `status_code`: 200 OK
  - `BeautifulSoup` 선택자 `#yesBestList > li`를 통해 총 24개의 도서 아이템 목록이 정상적으로 식별됨.
  - 개별 도서 항목의 `a.gd_name` 선택자를 활용해 1페이지의 도서명이 정상 파싱됨을 확인.
