#!/bin/bash

# App Classification API 테스트 스크립트
# 사용법: bash test_curl.sh

BASE_URL="http://localhost:8000"

# JSON 포맷팅 함수 (jq 또는 python3 json.tool 사용)
format_json() {
    if command -v jq &> /dev/null; then
        jq .
    elif command -v python3 &> /dev/null; then
        python3 -m json.tool
    else
        cat
    fi
}

echo "=========================================="
echo "App Classification API 테스트"
echo "=========================================="
echo ""

# 1. 헬스 체크
echo "1. 헬스 체크 테스트"
echo "------------------------------------------"
curl -s -X GET "${BASE_URL}/health" | format_json
echo ""
echo ""

# 2. 단일 앱 조회 테스트
echo "2. 단일 앱 조회 테스트 (com.roblox.client)"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "package_name": "com.roblox.client"
      }
    ]
  }' | format_json
echo ""
echo ""

# 3. 여러 앱 조회 테스트
echo "3. 여러 앱 조회 테스트"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/classify" \
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
  }' | format_json
echo ""
echo ""

# 4. 존재하지 않는 앱 테스트
echo "4. 존재하지 않는 앱 테스트"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "package_name": "com.invalid.nonexistent.app"
      }
    ]
  }' | format_json
echo ""
echo ""

# 5. 잘못된 요청 형식 테스트
echo "5. 잘못된 요청 형식 테스트 (apps 필드 누락)"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "invalid_field": "test"
  }' | format_json
echo ""
echo ""

# 6. package_name 누락 테스트
echo "6. package_name 누락 테스트"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "apps": [
      {
        "invalid_field": "test"
      }
    ]
  }' | format_json
echo ""
echo ""

echo "=========================================="
echo "테스트 완료"
echo "=========================================="

