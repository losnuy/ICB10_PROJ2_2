> 원본 출처: [https://developers.naver.com/docs/common/openapiguide/](https://developers.naver.com/docs/common/openapiguide/)

# API 공통 가이드

네이버 오픈API는 네이버 플랫폼의 기능을 외부 개발자가 쉽게 이용할 수 있게 웹 또는 SDK 형태로 공개한 기술들입니다. 네이버 오픈API로 활용할 수 있는 기술에는 네이버 로그인과 지도, 검색이 있으며, Clova의 음성 인식 기술과 음성 합성 기술, 얼굴 인식 기술, Papago의 기계 번역 기술 등이 있습니다.

## API 공통 가이드 개요

API 공통 가이드는 네이버 오픈API를 사용해 클라이언트 애플리케이션을 개발할 때 미리 알아 두어야 하는 내용을 설명합니다.

> - 최종 수정일: 2021년 8월 27일
>
> 이 문서의 내용은 언제든지 변경될 수 있습니다.

## API 공통 가이드 구성

API 공통 가이드의 내용은 다음과 같습니다.

- [네이버 오픈API 종류](https://developers.naver.com/docs/common/openapiguide/apilist.md)
  - [로그인 방식 오픈 API](https://developers.naver.com/docs/common/openapiguide/apilist.md#%EB%A1%9C%EA%B7%B8%EC%9D%B8-%EB%B0%A9%EC%8B%9D-%EC%98%A4%ED%94%88-api)
  - [비로그인 방식 오픈 API](https://developers.naver.com/docs/common/openapiguide/apilist.md#%EB%B9%84%EB%A1%9C%EA%B7%B8%EC%9D%B8-%EB%B0%A9%EC%8B%9D-%EC%98%A4%ED%94%88-api)
- [사전 준비 사항](https://developers.naver.com/docs/common/openapiguide/appregister.md)
  - [애플리케이션 등록](https://developers.naver.com/docs/common/openapiguide/appregister.md#%EC%95%A0%ED%94%8C%EB%A6%AC%EC%BC%80%EC%9D%B4%EC%85%98-%EB%93%B1%EB%A1%9D)
  - [애플리케이션 등록 세부 정보](https://developers.naver.com/docs/common/openapiguide/appregister.md#%EC%95%A0%ED%94%8C%EB%A6%AC%EC%BC%80%EC%9D%B4%EC%85%98-%EB%93%B1%EB%A1%9D-%EC%84%B8%EB%B6%80-%EC%A0%95%EB%B3%B4)
  - [애플리케이션 등록 확인](https://developers.naver.com/docs/common/openapiguide/appregister.md#%EC%95%A0%ED%94%8C%EB%A6%AC%EC%BC%80%EC%9D%B4%EC%85%98-%EB%93%B1%EB%A1%9D-%ED%99%95%EC%9D%B8)
  - [클라이언트 아이디와 클라이언트 시크릿 확인](https://developers.naver.com/docs/common/openapiguide/appregister.md#%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%96%B8%ED%8A%B8-%EC%95%84%EC%9D%B4%EB%94%94%EC%99%80-%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%96%B8%ED%8A%B8-%EC%8B%9C%ED%81%AC%EB%A6%BF-%ED%99%95%EC%9D%B8)
- [내 애플리케이션 관리](https://developers.naver.com/docs/common/openapiguide/appconf.md)
  - [기본 정보](https://developers.naver.com/docs/common/openapiguide/appconf.md#%EA%B8%B0%EB%B3%B8-%EC%A0%95%EB%B3%B4)
  - [API 설정](https://developers.naver.com/docs/common/openapiguide/appconf.md#api-%EC%84%A4%EC%A0%95)
  - [멤버 관리](https://developers.naver.com/docs/common/openapiguide/appconf.md#%EB%A9%A4%EB%B2%84-%EA%B4%80%EB%A6%AC)
  - [통계 보기](https://developers.naver.com/docs/common/openapiguide/appconf.md#%ED%86%B5%EA%B3%84-%EB%B3%B4%EA%B8%B0)
  - [애플리케이션 삭제](https://developers.naver.com/docs/common/openapiguide/appconf.md#%EC%95%A0%ED%94%8C%EB%A6%AC%EC%BC%80%EC%9D%B4%EC%85%98-%EC%82%AD%EC%A0%9C)
- [용어 정리](https://developers.naver.com/docs/common/openapiguide/apiterms.md)
  - [API의 기본](https://developers.naver.com/docs/common/openapiguide/apiterms.md#api%EC%9D%98-%EA%B8%B0%EB%B3%B8)
  - [API 인증](https://developers.naver.com/docs/common/openapiguide/apiterms.md#api-%EC%9D%B8%EC%A6%9D)
  - [API 호출](https://developers.naver.com/docs/common/openapiguide/apiterms.md#api-%ED%98%B8%EC%B6%9C)
  - [HTTP](https://developers.naver.com/docs/common/openapiguide/apiterms.md#http)
- [샘플 코드](https://developers.naver.com/docs/common/openapiguide/apicall.md)
  - [로그인 방식 오픈 API 호출 예](https://developers.naver.com/docs/common/openapiguide/apicall.md#%EB%A1%9C%EA%B7%B8%EC%9D%B8-%EB%B0%A9%EC%8B%9D-%EC%98%A4%ED%94%88-api-%ED%98%B8%EC%B6%9C-%EC%98%88)
  - [비로그인 방식 오픈 API 호출 예](https://developers.naver.com/docs/common/openapiguide/apicall.md#%EB%B9%84%EB%A1%9C%EA%B7%B8%EC%9D%B8-%EB%B0%A9%EC%8B%9D-%EC%98%A4%ED%94%88-api-%ED%98%B8%EC%B6%9C-%EC%98%88)
- [오류 코드](https://developers.naver.com/docs/common/openapiguide/errorcode.md)
  - [주요 오류 코드](https://developers.naver.com/docs/common/openapiguide/errorcode.md#%EC%A3%BC%EC%9A%94-%EC%98%A4%EB%A5%98-%EC%BD%94%EB%93%9C)
  - [오류 메시지 형식](https://developers.naver.com/docs/common/openapiguide/errorcode.md#%EC%98%A4%EB%A5%98-%EB%A9%94%EC%8B%9C%EC%A7%80-%ED%98%95%EC%8B%9D)