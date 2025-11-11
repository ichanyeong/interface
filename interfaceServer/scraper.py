from google_play_scraper import app, search
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 한국 Google Play Store 카테고리 목록 (영문 카테고리명과 한국어 검색어 매핑)
KOREAN_CATEGORIES = {
    'GAME': '게임',
    'COMMUNICATION': '커뮤니케이션',
    'SOCIAL': '소셜',
    'PRODUCTIVITY': '생산성',
    'PHOTOGRAPHY': '사진',
    'VIDEO_PLAYERS': '비디오',
    'ENTERTAINMENT': '엔터테인먼트',
    'MUSIC_AUDIO': '음악',
    'SHOPPING': '쇼핑',
    'FOOD_AND_DRINK': '음식',
    'TRAVEL_AND_LOCAL': '여행',
    'NEWS_AND_MAGAZINES': '뉴스',
    'BOOKS_AND_REFERENCE': '도서',
    'EDUCATION': '교육',
    'FINANCE': '금융',
    'BUSINESS': '비즈니스',
    'HEALTH_AND_FITNESS': '건강',
    'LIFESTYLE': '라이프스타일',
    'WEATHER': '날씨',
    'TOOLS': '도구',
    'MEDICAL': '의료',
    'SPORTS': '스포츠',
}

# 한국 Google Play Store 국가 코드
COUNTRY = 'kr'
LANG = 'ko'


def get_appnames_by_packageNames(package_names:list):
    """
    패키지명 목록을 받아 각 앱의 기본 정보를 조회한다.

    Args:
        package_names: Google Play 패키지 이름(iterable)

    Returns:
        각 앱에 대한 dict 리스트. (id, app_name, description, category 포함)
    """
    if not package_names:
        logger.warning("패키지 이름 목록이 비어 있습니다.")
        return []

    results = []
    for pkg in package_names:
        if not pkg:
            continue

        try:
            detail = app(app_id=pkg, lang=LANG, country=COUNTRY)
            results.append(
                {
                    "id": detail.get("appId", pkg),
                    "app_name": detail.get("title") or detail.get("appId", pkg),
                    "description": detail.get("description", ""),
                    "category": detail.get("genreId") or detail.get("genre"),
                }
            )
            logger.info("패키지 '%s' 정보 수집 완료.", pkg)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("패키지 '%s' 정보 수집 실패: %s", pkg, exc)
            continue

        time.sleep(0.2)

    logger.info("총 %d개 패키지 정보 수집 완료.", len(results))
    return results

def get_top_apps_by_category(category_key: str, category_search_term: str, num_results: int = 100):
    """
    특정 카테고리에서 상위 앱들을 수집
    
    Args:
        category_key: 카테고리 키 (예: 'GAME')
        category_search_term: 검색에 사용할 한국어 카테고리명 (예: '게임')
        num_results: 수집할 앱 개수 (기본값: 100)
    
    Returns:
        앱 정보 리스트 (각 앱은 상세 정보 포함)
    """
    try:
        logger.info(f"카테고리 '{category_key}' ({category_search_term})에서 상위 {num_results}개 앱 수집 시작...")
        
        # 카테고리로 검색 (한국어 검색어 사용)
        search_results = search(
            query=category_search_term,
            lang=LANG,
            country=COUNTRY,
            n_hits=num_results
        )
        
        if not search_results:
            logger.warning(f"카테고리 '{category_key}' 검색 결과가 없습니다.")
            return []
        
        logger.info(f"검색 결과: {len(search_results)}개 앱 발견, 상세 정보 수집 중...")
        
        # 각 앱의 상세 정보 가져오기
        apps_data = []
        for idx, result in enumerate(search_results[:num_results], 1):
            try:
                app_id = result.get('appId')
                if not app_id:
                    continue
                
                # 앱 상세 정보 가져오기
                app_detail = app(
                    app_id=app_id,
                    lang=LANG,
                    country=COUNTRY
                )
                
                # 카테고리 정보 추가 (검색 결과의 genre와 상세 정보의 genreId 확인)
                # 상세 정보에 카테고리 정보가 더 정확함
                apps_data.append(app_detail)
                
                if idx % 10 == 0:
                    logger.info(f"  진행 상황: {idx}/{min(len(search_results), num_results)}개 처리 완료")
                
                # API 호출 제한을 피하기 위해 짧은 딜레이
                time.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"앱 '{result.get('title', 'Unknown')}' (ID: {result.get('appId', 'N/A')}) 상세 정보 가져오기 실패: {e}")
                continue
        
        logger.info(f"카테고리 '{category_key}': {len(apps_data)}개 앱 수집 완료")
        return apps_data
        
    except Exception as e:
        logger.error(f"카테고리 '{category_key}' 수집 중 오류 발생: {e}")
        return []


def scrape_all_categories(num_per_category: int = 100):
    """
    모든 카테고리의 상위 앱들을 수집
    
    Args:
        num_per_category: 카테고리당 수집할 앱 개수 (기본값: 100)
    
    Returns:
        카테고리별 앱 정보 딕셔너리
    """
    all_apps = {}
    
    for category_key, category_search_term in KOREAN_CATEGORIES.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"카테고리 처리 중: {category_key} ({category_search_term})")
        logger.info(f"{'='*50}")
        
        # 검색을 통해 카테고리별 앱 수집
        apps = get_top_apps_by_category(category_key, category_search_term, num_per_category)
        
        all_apps[category_key] = apps
        
        # 카테고리 간 딜레이 (API 제한 회피)
        logger.info(f"카테고리 '{category_key}' 완료. 다음 카테고리로 이동하기 전 대기 중...")
        time.sleep(2)
    
    return all_apps
