# Data Processing

서울시 고령보행자 교통사고 위험도 분석을 위한 데이터 수집 및 결합 작업 공간입니다. 도로명주소 도로구간 데이터에서 서울시 도로 포인트를 만들고, 각 포인트별 위험도와 앞으로 필요할 feature 들을 결합합니다.

* 팀원안내서.md 꼭 읽어주세요!!!!!!!

## 실행 방법

### 1. 저장소 클론

```bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_NAME>
```

```bash
cd <PROJECT_DIR>
```

### 2. 데이터 파일 준비

Data 폴더에 데이터들을 넣어주십쇼
압축 푸시고 안에 내용물들을 Data 폴더에 복사붙여넣기 해주세요

```text
Data/
├── (도로명주소)도로구간_서울/
│   ├── TL_SPRD_MANAGE_11_202605.shp
│   ├── TL_SPRD_MANAGE_11_202605.shx
│   ├── TL_SPRD_MANAGE_11_202605.dbf
│   ├── TL_SPRD_MANAGE_11_202605.prj
│   └── TL_SPRD_MANAGE_11_202605.cpg
├── ITS_node_link/
│   ├── MOCT_LINK.shp
│   ├── MOCT_LINK.shx
│   ├── MOCT_LINK.dbf
│   ├── MOCT_LINK.prj
│   ├── MOCT_LINK.cpg
│   ├── MOCT_NODE.shp
│   ├── MOCT_NODE.shx
│   ├── MOCT_NODE.dbf
│   ├── MOCT_NODE.prj
│   └── MOCT_NODE.cpg
├── 소상공인시장진흥공단_상가(상권)정보_서울_202603.csv
├── 서울시_노인의료복지시설현황_geocoded.csv
├── 전통시장여부/
│   ├── 서울시 상권분석서비스(영역-상권)_전통시장.shp
│   ├── 서울시 상권분석서비스(영역-상권)_전통시장.shx
│   ├── 서울시 상권분석서비스(영역-상권)_전통시장.dbf
│   ├── 서울시 상권분석서비스(영역-상권)_전통시장.prj
│   └── 서울시 상권분석서비스(영역-상권)_전통시장.cpg
├── 버스정류장개수/
│   └── 서울시버스정류소위치정보(20241002).xlsx
├── 과속방지턱개수/
│   ├── A067_A.shp
│   ├── A067_A.shx
│   ├── A067_A.dbf
│   ├── A067_A.prj
│   └── A067_A.cpg
├── 교차로개수/
│   └── A008_P_20250814/
│       └── A008_P/
│           ├── A008_P.shp
│           ├── A008_P.shx
│           ├── A008_P.dbf
│           ├── A008_P.prj
│           └── A008_P.cpg
├── 횡단보도개수/
│   └── 횡단보도 위치 및 부착대 정보/
│       └── A004_A_횡단보도/
│           ├── A004_A.shp
│           ├── A004_A.shx
│           ├── A004_A.dbf
│           ├── A004_A.prj
│           └── A004_A.cpg
└── 국토통계_고령인구수/
```

필수 입력 파일:

| 경로 | 설명 |
|---|---|
| `Data/(도로명주소)도로구간_서울/TL_SPRD_MANAGE_11_202605.shp` | 서울 도로명주소 도로구간 |
| `Data/ITS_node_link/MOCT_LINK.shp` | ITS 표준노드링크 링크 데이터 |
| `Data/소상공인시장진흥공단_상가(상권)정보_서울_202603.csv` | 서울 상가 업종 및 위치 데이터 |
| `Data/서울시_노인의료복지시설현황_geocoded.csv` | 서울시 노인의료복지시설 지오코딩 좌표 데이터 |
| `Data/전통시장여부/서울시 상권분석서비스(영역-상권)_전통시장.shp` | 서울시 전통시장 polygon 데이터 |
| `Data/버스정류장개수/서울시버스정류소위치정보(20241002).xlsx` | 서울시 버스정류소 위치 데이터 |
| `Data/과속방지턱개수/A067_A.shp` | 서울시 과속방지턱 polygon 데이터 |
| `Data/교차로개수/A008_P_20250814/A008_P/A008_P.shp` | 서울시 교차로 point 데이터 |
| `Data/횡단보도개수/횡단보도 위치 및 부착대 정보/A004_A_횡단보도/A004_A.shp` | 서울시 횡단보도 polygon 데이터 |
| `Data/국토통계_고령인구수/` | 국토정보플랫폼 서울시 구별 250m 격자 고령인구수 데이터 |

Shapefile은 `.shp`만으로는 실행되지 않습니다. 같은 이름의 `.shx`, `.dbf`, `.prj`, `.cpg` 파일도 반드시 같은 폴더에 있어야 합니다.

### 3. Python 가상환경 생성

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. 패키지 설치

```bash
pip install -r requirements.txt
```

### 5. 노인의료복지시설 지오코딩 CSV 준비

`데이터결합.ipynb`는 `Data/서울시_노인의료복지시설현황_geocoded.csv`를 읽어 `사회복지시설개수`를 계산합니다.
이 파일은 `test.ipynb`에서 VWorld Geocoder API로 미리 생성합니다.

### 6. 사고 데이터 수집 노트북 실행

먼저 실행할 노트북:

```text
노인보행사고데이터.ipynb
```
실행하면 Data 폴더에 csv 파일이 생성됩니다.
```text
Data/seoul_old_pedestrian_individual_accidents_2020_2025.csv
```

이 노트북은 TAAS 웹 내부 요청을 사용하므로 인터넷 연결이 필요합니다.

### 7. 도로 포인트 및 feature 결합 노트북 실행

다음으로 실행할 노트북:

```text
데이터결합.ipynb
```
실행하면 Data 폴더에 csv 파일이 생성됩니다.
```text
Data/seoul_road_points.csv
```

이미 `Data/seoul_road_points.csv`가 있으면 기존 CSV를 읽어서 없는 feature 컬럼만 추가합니다.
도로 shapefile 로드, 25m 포인트 재생성, 이미 계산된 feature 결합은 건너뜁니다.

이 노트북은 다음 feature를 결합합니다.

| feature | 생성 방식 |
|---|---|
| `POINT_ID` | 서울시 도로 라인 위 25m 간격 포인트 |
| `위도`, `경도` | `POINT_ID` 위치를 EPSG:4326으로 변환 |
| `위험도` | 50m 버퍼 내 고령보행자 사고 기반 계산 |
| `제한속도` | ITS 표준노드링크 최근접 링크의 `MAX_SPD` |
| `고령인구수` | 300m 반경 내 65세 이상 거주인구 |
| `사회복지시설개수` | 노인의료복지시설 지오코딩 CSV 기준 300m 반경 내 시설 개수 |
| `전통시장여부` | 50m 반경 내 전통시장 polygon 포함 여부 |
| `버스정류장개수` | 300m 반경 내 버스정류장 수, 가상정류장 제외 |
| `과속방지턱개수` | 50m 반경 내 과속방지턱 수 |
| `교차로개수` | 50m 반경 내 교차로 수 |
| `횡단보도개수` | 50m 반경 내 횡단보도 수 |
| 상가 업종별 개수 | 300m 반경 내 서울시 상가 업종별 개수 |

### 8. 실행 순서 요약

```text
1. 원천 데이터 파일을 Data/ 하위에 배치
2. pip install -r requirements.txt
3. test.ipynb로 Data/서울시_노인의료복지시설현황_geocoded.csv 준비
4. 노인보행사고데이터.ipynb 실행
5. 데이터결합.ipynb 실행
6. Data/seoul_road_points.csv 확인
```

## 주요 산출물

최종 산출 파일:

```text
Data/seoul_road_points.csv
```

현재 최종 CSV 컬럼:

```text
POINT_ID, 위도, 경도, 제한속도, 위험도, 고령인구수, 사회복지시설개수, 전통시장여부, 버스정류장개수, 과속방지턱개수, 교차로개수, 횡단보도개수, 상가 업종별 개수 85개
```

컬럼 설명:

| 컬럼 | 설명 |
|---|---|
| `POINT_ID` | 서울시 도로구간 라인 위에 25m 간격으로 생성한 포인트 ID |
| `위도` | POINT_ID 위치의 위도, EPSG:4326 |
| `경도` | POINT_ID 위치의 경도, EPSG:4326 |
| `제한속도` | ITS 표준노드링크에서 가장 가까운 링크의 `MAX_SPD` 값 |
| `위험도` | 50m 버퍼 내 고령보행자 사고 기반 위험도 |
| `고령인구수` | 국토정보플랫폼 250m 격자 인구 데이터 기준 300m 반경 내 65세 이상 거주인구 |
| `사회복지시설개수` | 노인의료복지시설 지오코딩 CSV 기준 300m 반경 내 시설 개수 |
| `전통시장여부` | 50m 반경 안에 전통시장 polygon이 닿으면 1, 아니면 0 |
| `버스정류장개수` | 300m 반경 안에 있는 실제 버스정류장 수, `정류소타입 == "가상정류장"` 제외 |
| `과속방지턱개수` | 50m 반경 안에 있는 과속방지턱 polygon 수 |
| `교차로개수` | 50m 반경 안에 있는 교차로 point 수 |
| `횡단보도개수` | 50m 반경 안에 있는 횡단보도 polygon 수 |
| 상가 업종 컬럼 | 300m 반경 내 해당 업종 상가 수 |

위험도 계산식:

```text
위험도 = 10 × 사고건수 × (사망자수 + 0.1168 × 중상자수 + 0.0068 × 경상자수)
```

## 디렉터리 구조

```text
.
├── README.md
├── requirements.txt
├── 노인보행사고데이터.ipynb
├── 데이터결합.ipynb
├── src/
│   └── silverwalk/
│       ├── config.py
│       ├── roads.py
│       ├── features.py
│       ├── accidents.py
│       ├── speed.py
│       ├── business.py
│       ├── population.py
│       └── social_welfare.py
├── Data/
│   ├── (도로명주소)도로구간_서울/
│   │   └── TL_SPRD_MANAGE_11_202605.shp 외 부속 파일
│   ├── ITS_node_link/
│   │   └── MOCT_LINK.shp 외 부속 파일
│   ├── seoul_old_pedestrian_individual_accidents_2020_2025.csv
│   ├── 서울시_노인의료복지시설현황_geocoded.csv
│   ├── 전통시장여부/
│   ├── 버스정류장개수/
│   ├── 과속방지턱개수/
│   ├── 교차로개수/
│   ├── 횡단보도개수/
│   ├── 국토통계_고령인구수/
│   └── seoul_road_points.csv
└── example/
```

## 코드 구조

핵심 처리 함수는 `src/silverwalk/`로 분리되어 있고, `데이터결합.ipynb`는 전체 결합 순서를 실행하는 파이프라인 역할을 합니다.

| 파일 | 역할 |
|---|---|
| `src/silverwalk/config.py` | 데이터 경로, 거리 기준, 최종 컬럼 목록 |
| `src/silverwalk/roads.py` | 도로 데이터 로드, 서울시 필터링, 25m 포인트, 50m 버퍼 생성 |
| `src/silverwalk/features.py` | 기본 좌표 feature 생성 |
| `src/silverwalk/accidents.py` | 사고 데이터 결합 및 위험도 계산 |
| `src/silverwalk/speed.py` | ITS 표준노드링크 제한속도 결합 |
| `src/silverwalk/business.py` | 300m 반경 상가 업종별 개수 결합 |
| `src/silverwalk/population.py` | 300m 반경 65세 이상 거주인구 결합 |
| `src/silverwalk/social_welfare.py` | 300m 반경 노인의료복지시설 개수 결합 |
| `src/silverwalk/traditional_market.py` | 50m 반경 전통시장 포함 여부 결합 |
| `src/silverwalk/bus_stops.py` | 300m 반경 버스정류장 개수 결합 |
| `src/silverwalk/speed_bumps.py` | 50m 반경 과속방지턱 개수 결합 |
| `src/silverwalk/intersections.py` | 50m 반경 교차로 개수 결합 |
| `src/silverwalk/crosswalks.py` | 50m 반경 횡단보도 개수 결합 |

## 입력 데이터

### 1. 도로명주소 도로구간 데이터

```text
Data/(도로명주소)도로구간_서울/TL_SPRD_MANAGE_11_202605.shp
```

사용 내용:

- 서울시 필터: `SIG_CD`가 `"11"`로 시작
- 도로 클래스 필터: `ROA_CLS_SE in {"3", "4"}`
  - `3`: 로
  - `4`: 길
- 고속도로/대로는 제외합니다.
- 원본 좌표계: EPSG:5179

처리 결과:

- 서울시 도로 라인 위에 25m 간격 포인트 생성
- 각 포인트 주변 50m 버퍼 생성

### 2. 고령보행자 개별 교통사고 데이터

생성 파일:

```text
Data/seoul_old_pedestrian_individual_accidents_2020_2025.csv
```

생성 노트북:

```text
노인보행사고데이터.ipynb
```

수집 방식:

- 공공데이터포털 다발지역 API가 아니라 TAAS GIS 웹페이지 내부 Ajax 요청을 재현합니다.
- TAAS 초기 페이지에서 CSRF 토큰과 세션 쿠키를 받은 뒤 `selectAccidentInfo.do`에 POST 요청합니다.
- 조회 조건:
  - 지역: 서울시 `11%`
  - 기간: `2020~2022`, `2023~2025`를 각각 조회 후 결합
  - 간편조건 코드 `42`: 고령보행자 사고

주의:

- 이 방식은 공식 OpenAPI가 아니라 TAAS 웹앱 내부 JSON 요청 재현입니다.
- TAAS 웹사이트 구조나 요청 파라미터가 바뀌면 코드 수정이 필요할 수 있습니다.

### 3. ITS 표준노드링크 데이터

```text
Data/ITS_node_link/MOCT_LINK.shp
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `LINK_ID` | 표준 링크 ID |
| `ROAD_NAME` | 도로명 |
| `MAX_SPD` | 제한속도 |
| `geometry` | 링크 라인 geometry |

처리 방식:

- 전국 링크 전체를 직접 최근접 결합하면 무거우므로, 서울시 도로 포인트 범위 주변 bbox로 먼저 자릅니다.
- 링크를 도로 포인트 좌표계인 EPSG:5179로 변환합니다.
- 각 `POINT_ID`에서 가장 가까운 링크 1개를 선택해 `MAX_SPD`를 `제한속도`로 부여합니다.
- 동거리 링크가 여러 개 잡히는 경우 `POINT_ID`, 거리, `LINK_ID` 기준으로 하나만 남깁니다.

### 4. 소상공인시장진흥공단 상가 정보 데이터

```text
Data/소상공인시장진흥공단_상가(상권)정보_서울_202603.csv
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `시도명` | 서울특별시 필터링 |
| `상권업종대분류명` | 상가 업종 대분류 |
| `상권업종중분류명` | 상가 업종 중분류 |
| `경도`, `위도` | 상가 위치, EPSG:4326 |

처리 방식:

- `시도명 == "서울특별시"`만 사용합니다.
- 상가 좌표를 EPSG:4326에서 도로 포인트 좌표계로 변환합니다.
- 각 `POINT_ID` 기준 300m 반경 안에 있는 상가를 업종별로 집계합니다.
- 대분류 컬럼과 `대분류_중분류` 컬럼을 최종 CSV에 추가합니다.

### 5. 국토정보플랫폼 고령인구 격자 데이터

입력 폴더:

```text
Data/국토통계_고령인구수/
```

사용 내용:

- 국토정보플랫폼에서 서울시 구별 250m 격자 고령 인구 수 데이터를 내려받습니다.
- 현재 코드의 기본 입력은 `Data/국토통계_고령인구수/` 하위의 구별 `nlsp_031001010.shp` 파일들입니다.
- 국토통계 고령 인구 수 데이터의 기본 인구수 컬럼은 `val`입니다.

처리 방식:

- 데이터를 도로 포인트 좌표계로 변환합니다.
- 격자 polygon 데이터는 격자 대표점 기준으로 300m 버퍼 안 포함 여부를 판단합니다.
- 각 `POINT_ID` 기준 300m 반경 안에 포함된 격자의 `val`을 합산해 `고령인구수` 컬럼으로 추가합니다.

### 6. 서울시 노인의료복지시설 데이터

입력 파일:

```text
Data/서울시_노인의료복지시설현황_geocoded.csv
```

처리 방식:

- `test.ipynb`에서 VWorld Geocoder API로 생성한 지오코딩 CSV를 사용합니다.
- `지오코딩상태 == "OK"`이고 `경도`, `위도`가 있는 시설만 사용합니다.
- 지오코딩 실패 시설은 `사회복지시설개수` 계산에서 제외합니다.
- 각 `POINT_ID` 기준 300m 반경 안에 있는 시설 수를 `사회복지시설개수` 컬럼으로 추가합니다.

### 7. 서울시 전통시장 데이터

입력 파일:

```text
Data/전통시장여부/서울시 상권분석서비스(영역-상권)_전통시장.shp
```

처리 방식:

- 서울시 상권분석서비스 영역 데이터 중 `TRDAR_SE_1 == "전통시장"`인 polygon을 사용합니다.
- 전통시장 polygon을 도로 포인트 좌표계로 변환합니다.
- 각 `POINT_ID` 기준 50m 버퍼가 전통시장 polygon과 닿으면 `전통시장여부`를 1로 둡니다.
- 반경 50m 안에 전통시장이 없으면 `전통시장여부`를 0으로 둡니다.

### 8. 서울시 버스정류장 데이터

입력 파일:

```text
Data/버스정류장개수/서울시버스정류소위치정보(20241002).xlsx
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `NODE_ID` | 정류장 ID |
| `X좌표` | 정류장 경도, EPSG:4326 |
| `Y좌표` | 정류장 위도, EPSG:4326 |
| `정류소타입` | 정류장 유형 |

처리 방식:

- `정류소타입 == "가상정류장"`인 행은 제외합니다.
- 정류장 좌표를 도로 포인트 좌표계로 변환합니다.
- 각 `POINT_ID` 기준 300m 반경 안에 있는 정류장의 `NODE_ID` 개수를 `버스정류장개수` 컬럼으로 추가합니다.

### 9. 서울시 과속방지턱 데이터

입력 파일:

```text
Data/과속방지턱개수/A067_A.shp
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `MGRNU` | 과속방지턱 객체 ID |
| `geometry` | 과속방지턱 polygon geometry |

처리 방식:

- 과속방지턱 polygon 데이터를 도로 포인트 좌표계로 변환합니다.
- 일부 polygon의 닫히지 않은 링은 읽는 과정에서 보정합니다.
- 각 `POINT_ID` 기준 50m 버퍼와 과속방지턱 polygon이 닿으면 해당 과속방지턱을 집계합니다.
- 각 `POINT_ID`별 고유 `MGRNU` 개수를 `과속방지턱개수` 컬럼으로 추가합니다.

### 10. 서울시 교차로 데이터

입력 파일:

```text
Data/교차로개수/A008_P_20250814/A008_P/A008_P.shp
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `MGRNU` | 교차로 객체 ID |
| `geometry` | 교차로 point geometry |

처리 방식:

- 교차로 point 데이터를 도로 포인트 좌표계로 변환합니다.
- 각 `POINT_ID` 기준 50m 버퍼 안에 포함된 교차로 point를 집계합니다.
- 각 `POINT_ID`별 고유 `MGRNU` 개수를 `교차로개수` 컬럼으로 추가합니다.

### 11. 서울시 횡단보도 데이터

입력 파일:

```text
Data/횡단보도개수/횡단보도 위치 및 부착대 정보/A004_A_횡단보도/A004_A.shp
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `MGRNU` | 횡단보도 객체 ID |
| `geometry` | 횡단보도 polygon geometry |

처리 방식:

- 횡단보도 polygon 데이터를 도로 포인트 좌표계로 변환합니다.
- 일부 polygon의 닫히지 않은 링은 읽는 과정에서 보정합니다.
- 각 `POINT_ID` 기준 50m 버퍼와 횡단보도 polygon이 닿으면 해당 횡단보도를 집계합니다.
- 각 `POINT_ID`별 고유 `MGRNU` 개수를 `횡단보도개수` 컬럼으로 추가합니다.

## 노트북 실행 순서

### 1. 사고 데이터 수집

```text
노인보행사고데이터.ipynb
```

이 노트북을 실행하면 아래 파일이 생성됩니다.

```text
Data/seoul_old_pedestrian_individual_accidents_2020_2025.csv
```

서울시 기준 수집 건수는 노트북 실행 후 출력되는 연도별 요약에서 확인합니다.

### 2. 도로 포인트 생성 및 feature 결합

```text
데이터결합.ipynb
```

처리 흐름:

1. 서울시 도로구간 로드
2. 도로 클래스 `3`, `4`만 필터링
3. 도로 라인 위에 25m 간격 포인트 생성
4. 각 포인트의 50m 버퍼 생성
5. 사고 포인트가 버퍼 안에 들어오면 사고 피해 규모 집계
6. 위험도 계산
7. ITS 표준노드링크에서 최근접 링크 제한속도 결합
8. 300m 반경 내 상가 업종별 개수 결합
9. 300m 반경 내 65세 이상 거주인구 결합
10. 300m 반경 내 노인의료복지시설 개수 결합
11. 최종 CSV 저장

최종 저장 파일:

```text
Data/seoul_road_points.csv
```

서울시 기준 행 수는 `데이터결합.ipynb` 실행 후 출력되는 최종 저장 행 수에서 확인합니다.
