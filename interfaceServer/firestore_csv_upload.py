import os
import logging
import csv
import json
import sys
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------------------------------------------------
# 1. 전역 로거 설정 (사용자 요청)
# -----------------------------------------------------------------
# LOG_LEVEL 환경 변수가 없으면 "INFO" 레벨로 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format='%(asctime)s - %(levelname)s - %(message)s')

# -----------------------------------------------------------------
# 2. 환경 변수 로드 (사용자 요청)
# -----------------------------------------------------------------
# FIRESTORE_APPS_COLLECTION이 없으면 "apps"가 기본값
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_APPS_COLLECTION", "apps")

# 서비스 계정 키 (파일 경로 또는 JSON 문자열)
FIREBASE_SERVICE_ACCOUNT = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# 프로젝트 ID (선택 사항, GCloud 환경용)
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

# -----------------------------------------------------------------
# 3. CSV 파일 정보
# -----------------------------------------------------------------
CSV_FILE_PATH = 'playstore_apps.csv'  # 업로드할 CSV 파일
DOCUMENT_ID_COLUMN = 'id'             # 문서 ID로 사용할 CSV 열 이름

# -----------------------------------------------------------------
# 4. Firebase Admin SDK 초기화
# -----------------------------------------------------------------
try:
    if not firebase_admin._apps:  # 앱이 아직 초기화되지 않았을 때만 초기화
        cred = None
        options = {}

        if not FIREBASE_SERVICE_ACCOUNT:
            # 환경 변수가 없으면 ADC(Application Default Credentials) 시도
            logger.info("FIREBASE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS 미설정. ADC로 초기화를 시도합니다.")
            cred = credentials.ApplicationDefault()
        elif os.path.exists(FIREBASE_SERVICE_ACCOUNT):
            # 시나리오 1: 파일 경로일 경우
            logger.info("파일 경로에서 서비스 계정을 로드합니다.")
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
        else:
            # 시나리오 2: JSON 문자열일 경우
            logger.info("JSON 문자열에서 서비스 계정을 로드합니다.")
            try:
                service_account_dict = json.loads(FIREBASE_SERVICE_ACCOUNT)
                cred = credentials.Certificate(service_account_dict)
            except json.JSONDecodeError:
                logger.critical("FIREBASE_SERVICE_ACCOUNT_JSON이 올바른 JSON 문자열이 아닙니다.")
                sys.exit(1)
        
        if FIREBASE_PROJECT_ID:
            options["projectId"] = FIREBASE_PROJECT_ID

        firebase_admin.initialize_app(credential=cred, options=options or None)

    db = firestore.client()
    logger.info(f"Firestore 클라이언트가 성공적으로 초기화되었습니다. (Project ID: {db.project})")

except Exception as e:
    logger.critical(f"Firebase Admin SDK 초기화 실패: {e}")
    logger.critical("서비스 계정 키(JSON)가 올바른지, 또는 파일 경로가 맞는지 확인하세요.")
    sys.exit(1) # 스크립트 중지

# -----------------------------------------------------------------
# 5. CSV 읽기 및 Firestore에 일괄 쓰기
# -----------------------------------------------------------------
def upload_csv_to_firestore():
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as file:
            # 'utf-8-sig'는 CSV 파일의 BOM(Byte Order Mark)을 처리합니다.
            csv_reader = csv.DictReader(file)
            
            logger.info(f"'{CSV_FILE_PATH}' 파일 읽기 시작... -> '{FIRESTORE_COLLECTION}' 컬렉션에 업로드합니다.")
            
            batch = db.batch()
            doc_count = 0
            total_doc_count = 0

            for row in csv_reader:
                try:
                    # CSV에서 문서 ID 가져오기
                    doc_id = row.get(DOCUMENT_ID_COLUMN)
                    if not doc_id:
                        logger.warning(f"'{DOCUMENT_ID_COLUMN}' 열이 없는 행을 건너뜁니다: {row}")
                        continue
                    
                    # Firestore에 저장할 데이터 (row 딕셔너리 전체)
                    data = dict(row) # 원본 row 복사
                    
                    # [데이터 전처리 예시] 'installs' 열을 숫자형으로 변환
                    installs_str = data.get('installs', '0').strip()
                    if installs_str:
                        # "1,000,000,000+" -> "1000000000"
                        clean_installs_str = installs_str.replace(',', '').replace('+', '')
                        try:
                            # 새 필드 'installs_numeric'에 숫자형으로 저장
                            data['installs_numeric'] = int(clean_installs_str)
                        except ValueError:
                            logger.warning(f"'{installs_str}'를 숫자로 변환할 수 없습니다. (ID: {doc_id})")
                            data['installs_numeric'] = 0
                    
                    # 배치에 쓰기 작업 추가
                    doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_id)
                    batch.set(doc_ref, data) # .set()은 덮어쓰기 (없으면 생성)
                    
                    doc_count += 1
                    total_doc_count += 1

                    # Firestore는 배치당 500개 쓰기를 권장합니다.
                    if doc_count >= 499:
                        logger.info(f"{doc_count}개 문서를 커밋합니다...")
                        batch.commit()
                        batch = db.batch() # 새 배치 시작
                        doc_count = 0

                except Exception as e:
                    logger.error(f"{doc_id} 처리 중 오류 발생: {e}")

            # 남은 배치 커밋
            if doc_count > 0:
                logger.info(f"남은 {doc_count}개 문서를 커밋합니다...")
                batch.commit()

            logger.info(f"CSV 파일 처리 완료. 총 {total_doc_count}개 문서가 '{FIRESTORE_COLLECTION}' 컬렉션에 업로드되었습니다.")

    except FileNotFoundError:
        logger.critical(f"[치명적 오류] CSV 파일을 찾을 수 없습니다: {CSV_FILE_PATH}")
    except Exception as e:
        logger.critical(f"[치명적 오류] 스크립트 실행 중 오류: {e}")

# -----------------------------------------------------------------
# 6. 스크립트 실행
# -----------------------------------------------------------------
if __name__ == "__main__":
    upload_csv_to_firestore()

