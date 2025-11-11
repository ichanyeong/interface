# !apt-get install texlive texlive-xetex texlive-latex-extra pandoc
# !pip install pypandoc
# !pip install datascience
# !pip install langchain-community
# !pip install langchain chromadb sentence-transformers transformers
# !pip install langchain-openai
# !pip install langchain-core
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import Client, create_client

from scraper import get_appnames_by_packageNames

# 전역 로거 설정: 서버 전반의 진단 로그를 출력한다.
logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# 주요 환경 변수들: 값이 없으면 기본값을 사용한다.
SUPABASE_TABLE = os.getenv("SUPABASE_APPS_TABLE", "apps")

@dataclass
class AppRecord:
    """Represents a row from the Supabase `apps` table."""

    id: str
    app_name: str
    description: str
    category: Optional[str] = None
    category_ko:Optional[str]=None



def init_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase credentials are not configured. "
            "Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)."
        )

    logger.info("Supabase client initialised.")
    return create_client(url, key)


def get_app_records_batch(client: Client, package_names: List[str]) -> Dict[str, AppRecord]:
    """Supabase에서 여러 패키지명을 한 번에 조회한다.
    
    Args:
        client: Supabase 클라이언트
        package_names: 조회할 패키지명 리스트
    
    Returns:
        패키지명을 키로 하는 AppRecord 딕셔너리 (조회된 것만 포함)
    """
    if not package_names:
        return {}

    try:
        response = client.table(SUPABASE_TABLE).select(
            "id,app_name,description,category,category_ko"
        ).in_("id", package_names).execute()

        if getattr(response, "error", None):
            raise RuntimeError(f"Supabase batch lookup failed: {response.error}")

        data = response.data or []
        records_map: Dict[str, AppRecord] = {}

        for row in data:
            try:
                record = AppRecord(
                    id=row["id"],
                    app_name=row.get("app_name") or row["id"],
                    description=row["description"],
                    category=row.get("category"),
                    category_ko=row.get("category_ko"),
                )
                records_map[record.id] = record
            except KeyError as exc:
                logger.warning("Supabase row missing required columns: %s", exc)
                continue

        logger.info("Fetched %d app records from Supabase (requested %d).", len(records_map), len(package_names))
        return records_map

    except Exception as exc:
        logger.exception("Error during batch lookup")
        raise RuntimeError(f"Failed to fetch app records from Supabase: {exc}") from exc


def upsert_app_record(client: Client, record: AppRecord) -> None:
    """카테고리 결과를 Supabase에 저장(Upsert)한다."""
    payload = {
        "id": record.id,
        "app_name": record.app_name,
        "description": record.description,
        "category": record.category,
        "category_ko": record.category_ko,
    }

    response = client.table(SUPABASE_TABLE).upsert(payload, on_conflict="id").execute()

    if getattr(response, "error", None):
        raise RuntimeError(f"Failed to upsert record into Supabase: {response.error}")

    logger.info("Record for %s upserted into Supabase.", record.id)


supabase_client = init_supabase_client()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 한글 등 유니코드 문자를 이스케이프하지 않음
CORS(app)


@app.get("/health")
def health_check() -> Any:
    """헬스 체크용 엔드포인트."""
    return jsonify({"status": "ok"}), 200


@app.post("/classify")
def classify() -> Any:
    """여러 앱의 패키지명을 받아 카테고리를 분류하고 Supabase에 저장한다.
    
    요청 형식:
    {
        "apps": [
            {
                "package_name": "com.example.app1"
            },
            {
                "package_name": "com.example.app2"
            },
            ...
        ]
    }
    
    응답 형식:
    {
        "results": [
            {
                "package_name": "...",
                "app_name": "...",
                "description": "...",
                "category": "...",
                "category_ko": "...",
                "source": "supabase" | "scraper" | "error"
            },
            ...
        ]
    }
    """
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    apps = payload.get("apps", [])

    if not apps or not isinstance(apps, list):
        return (
            jsonify(
                {"error": "Request must contain 'apps' field with a non-empty array."}
            ),
            400,
        )

    # 유효한 package_name 추출
    valid_package_names = []
    results = []

    for app_data in apps:
        package_name = app_data.get("package_name")

        if not package_name:
            results.append(
                {
                    "package_name": "unknown",
                    "app_name": None,
                    "description": None,
                    "category": None,
                    "category_ko": None,
                    "source": "error",
                    "error": "'package_name' field is required.",
                }
            )
            continue

        valid_package_names.append(package_name)

    if not valid_package_names:
        return jsonify({"results": results}), 200

    # 1단계: Supabase에서 모든 package_name을 한 번에 배치 조회
    try:
        existing_records_map = get_app_records_batch(supabase_client, valid_package_names)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error during batch Supabase lookup")
        # 배치 조회 실패 시 모든 항목을 에러로 처리
        for package_name in valid_package_names:
            results.append(
                {
                    "package_name": package_name,
                    "app_name": None,
                    "description": None,
                    "category": None,
                    "category_ko": None,
                    "source": "error",
                    "error": f"Supabase lookup failed: {str(exc)}",
                }
            )
        return jsonify({"results": results}), 200

    # 조회된 것과 조회되지 않은 것 분류
    package_names_to_scrape = []
    temp_results = {}  # package_name을 키로 하는 임시 결과 저장

    for package_name in valid_package_names:
        existing = existing_records_map.get(package_name)

        if existing and existing.category:
            logger.info("Category for %s found in Supabase.", package_name)
            temp_results[package_name] = {
                "package_name": package_name,
                "app_name": existing.app_name,
                "description": existing.description,
                "category": existing.category,
                "category_ko": existing.category_ko,
                "source": "supabase",
            }
        else:
            # Supabase에 없거나 카테고리가 없는 경우 scraper 사용
            package_names_to_scrape.append(package_name)

    # 2단계: Scraper로 조회 (조회되지 않은 것들만)
    if package_names_to_scrape:
        try:
            logger.info(
                "Fetching app info for %d apps from Google Play Store.",
                len(package_names_to_scrape),
            )
            scraper_results = get_appnames_by_packageNames(package_names_to_scrape)

            # Scraper 결과를 패키지명으로 매핑
            scraper_map = {result["id"]: result for result in scraper_results}

            for package_name in package_names_to_scrape:
                scraper_data = scraper_map.get(package_name)

                if not scraper_data:
                    temp_results[package_name] = {
                        "package_name": package_name,
                        "app_name": None,
                        "description": None,
                        "category": None,
                        "category_ko": None,
                        "source": "error",
                        "error": f"Could not find app information for package '{package_name}' in Google Play Store.",
                    }
                    continue

                scraped_category = scraper_data.get("category")
                scraped_app_name = scraper_data.get("app_name") or package_name
                scraped_description = scraper_data.get("description") or ""

                if not scraped_category:
                    logger.warning(
                        "Google Play Store data for %s does not contain category information.",
                        package_name,
                    )
                    temp_results[package_name] = {
                        "package_name": package_name,
                        "app_name": scraped_app_name,
                        "description": scraped_description,
                        "category": None,
                        "category_ko": None,
                        "source": "error",
                        "error": f"Category information not available for package '{package_name}'.",
                    }
                    continue

                record = AppRecord(
                    id=package_name,
                    app_name=scraped_app_name,
                    description=scraped_description,
                    category=scraped_category,
                    category_ko=None,  # scraper에서 category_ko는 제공하지 않음
                )

                upsert_app_record(supabase_client, record)

                temp_results[package_name] = {
                    "package_name": package_name,
                    "app_name": scraped_app_name,
                    "description": scraped_description,
                    "category": scraped_category,
                    "category_ko": None,
                    "source": "scraper",
                }

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error during scraping")
            # Scraper 실패 시 에러 결과 추가
            for package_name in package_names_to_scrape:
                temp_results[package_name] = {
                    "package_name": package_name,
                    "app_name": None,
                    "description": None,
                    "category": None,
                    "category_ko": None,
                    "source": "error",
                    "error": f"Scraping failed: {str(exc)}",
                }

    # 원래 순서대로 결과 구성
    for package_name in valid_package_names:
        if package_name in temp_results:
            results.append(temp_results[package_name])
        else:
            # 이 경우는 발생하지 않아야 하지만 안전장치
            results.append(
                {
                    "package_name": package_name,
                    "app_name": None,
                    "description": None,
                    "category": None,
                    "category_ko": None,
                    "source": "error",
                    "error": "Unexpected error: result not found.",
                }
            )

    return jsonify({"results": results}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug_enabled = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_enabled)