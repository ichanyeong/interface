# cURL 테스트 예제

## 기본 설정

```bash
BASE_URL="http://localhost:8000"
```

---

## 1. 헬스 체크

```bash
curl -X GET http://localhost:8000/health
```

**예상 응답:**
```json
{
  "status": "ok"
}
```

---

## 2. 단일 앱 조회

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "package_name": "com.roblox.client"
      }
    ]
  }'
```

---

## 3. 여러 앱 조회

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "package_name": "com.roblox.client"
      },
      {
        "package_name": "com.whatsapp"
      },
      {
        "package_name": "com.instagram.android"
      }
    ]
  }'
```

---

## 4. 실제 앱 예제들

### 게임 앱
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.roblox.client"},
      {"package_name": "com.supercell.clashofclans"},
      {"package_name": "com.mojang.minecraftpe"}
    ]
  }'
```

### 소셜/커뮤니케이션 앱
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.whatsapp"},
      {"package_name": "com.instagram.android"},
      {"package_name": "com.facebook.katana"}
    ]
  }'
```

### 생산성 앱
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.microsoft.office.word"},
      {"package_name": "com.google.android.apps.docs"},
      {"package_name": "com.dropbox.android"}
    ]
  }'
```

---

## 5. 에러 케이스 테스트

### 존재하지 않는 앱
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "package_name": "com.invalid.nonexistent.app"
      }
    ]
  }'
```

### 잘못된 요청 형식 (apps 필드 누락)
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "invalid_field": "test"
  }'
```

### package_name 누락
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "invalid_field": "test"
      }
    ]
  }'
```

---

## 6. 응답 포맷팅 (jq 사용)

jq가 설치되어 있다면 응답을 보기 좋게 포맷팅할 수 있습니다:

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.roblox.client"},
      {"package_name": "com.whatsapp"}
    ]
  }' | jq '.'
```

특정 필드만 추출:

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.roblox.client"}
    ]
  }' | jq '.results[] | {package_name, category, source}'
```

---

## 7. 전체 테스트 스크립트 실행

```bash
chmod +x test_curl.sh
./test_curl.sh
```

---

## 8. 포트가 다른 경우

포트가 8000이 아닌 경우:

```bash
curl -X POST http://localhost:YOUR_PORT/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.roblox.client"}
    ]
  }'
```

---

## 9. 원격 서버 테스트

원격 서버인 경우:

```bash
curl -X POST https://your-server.com/classify \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {"package_name": "com.roblox.client"}
    ]
  }'
```

