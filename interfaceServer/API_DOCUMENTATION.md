# App Classification API 문서

## 개요

이 API는 Android 앱의 패키지명을 받아 Google Play Store에서 앱 정보를 조회하고, 카테고리를 분류하여 Supabase에 저장하는 서비스입니다.

## Base URL
```
http://localhost:8000
```

기본 포트는 8000이며, `PORT` 환경 변수로 변경할 수 있습니다.


### 1. 헬스 체크

#### GET `/health`

서버 상태를 확인하는 엔드포인트입니다.

**요청 예시:**
```bash
curl -X GET http://localhost:8000/health
```

**응답 예시:**
```json
{
  "status": "ok"
}
```
**요청 본문 (Request Body):**

```json
{
  "apps": [
    {
      "package_name": "com.example.app1"
    },
    {
      "package_name": "com.example.app2"
    }
  ]
}
```
**응답 형식:**

**성공 응답 (200 OK):**

```json
{
  "results": [
    {
      "package_name": "com.roblox.client",
      "app_name": "Roblox",
      "description": "Virtual universe where you can create and share experiences.",
      "category": "GAME",
      "category_ko": null,
      "source": "supabase"
    },
    {
      "package_name": "com.whatsapp",
      "app_name": "WhatsApp",
      "description": "WhatsApp Messenger is a FREE messaging app available for Android.",
      "category": "COMMUNICATION",
      "category_ko": null,
      "source": "scraper"
    }
  ]
}
```
