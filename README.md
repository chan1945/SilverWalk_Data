# Data Processing

진주시 고령보행자 교통사고 위험도 분석을 위한 데이터 수집 및 결합 작업 공간입니다. 도로명주소 도로구간 데이터에서 진주시 도로 포인트를 만들고, 각 포인트별 위험도와 앞으로 필요할 feature 들을 결합합니다.

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
├── (도로명주소)도로구간_경남/
│   ├── TL_SPRD_MANAGE_48_202605.shp
│   ├── TL_SPRD_MANAGE_48_202605.shx
│   ├── TL_SPRD_MANAGE_48_202605.dbf
│   ├── TL_SPRD_MANAGE_48_202605.prj
│   └── TL_SPRD_MANAGE_48_202605.cpg
├── ITS_node_link/
    ├── MOCT_LINK.shp
    ├── MOCT_LINK.shx
    ├── MOCT_LINK.dbf
    ├── MOCT_LINK.prj
    ├── MOCT_LINK.cpg
    ├── MOCT_NODE.shp
    ├── MOCT_NODE.shx
    ├── MOCT_NODE.dbf
    ├── MOCT_NODE.prj
    └── MOCT_NODE.cpg
└── 소상공인시장진흥공단_상가(상권)정보_경남_202603.csv
```

필수 입력 파일:

| 경로 | 설명 |
|---|---|
| `Data/(도로명주소)도로구간_경남/TL_SPRD_MANAGE_48_202605.shp` | 경남 도로명주소 도로구간 |
| `Data/ITS_node_link/MOCT_LINK.shp` | ITS 표준노드링크 링크 데이터 |
| `Data/소상공인시장진흥공단_상가(상권)정보_경남_202603.csv` | 경남 상가 업종 및 위치 데이터 |

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

### 5. 사고 데이터 수집 노트북 실행

먼저 실행할 노트북:

```text
노인보행사고데이터.ipynb
```
실행하면 Data 폴더에 csv 파일이 생성됩니다.
```text
Data/jinju_old_pedestrian_individual_accidents_2020_2025.csv
```

이 노트북은 TAAS 웹 내부 요청을 사용하므로 인터넷 연결이 필요합니다.

### 6. 도로 포인트 및 feature 결합 노트북 실행

다음으로 실행할 노트북:

```text
데이터결합.ipynb
```
실행하면 Data 폴더에 csv 파일이 생성됩니다.
```text
Data/jinju_road_points.csv
```

이 노트북은 다음 feature를 결합합니다.

| feature | 생성 방식 |
|---|---|
| `POINT_ID` | 진주시 도로 라인 위 25m 간격 포인트 |
| `위도`, `경도` | `POINT_ID` 위치를 EPSG:4326으로 변환 |
| `위험도` | 50m 버퍼 내 고령보행자 사고 기반 계산 |
| `제한속도` | ITS 표준노드링크 최근접 링크의 `MAX_SPD` |
| 상가 업종별 개수 | 300m 반경 내 진주시 상가 업종별 개수 |

### 7. 실행 순서 요약

```text
1. 원천 데이터 파일을 Data/ 하위에 배치
2. pip install -r requirements.txt
3. 노인보행사고데이터.ipynb 실행
4. 데이터결합.ipynb 실행
5. Data/jinju_road_points.csv 확인
```

## 주요 산출물

최종 산출 파일:

```text
Data/jinju_road_points.csv
```

현재 최종 CSV 컬럼:

```text
POINT_ID, 위도, 경도, 제한속도, 위험도, 상가 업종별 개수 컬럼 85개
```

컬럼 설명:

| 컬럼 | 설명 |
|---|---|
| `POINT_ID` | 진주시 도로구간 라인 위에 25m 간격으로 생성한 포인트 ID |
| `위도` | POINT_ID 위치의 위도, EPSG:4326 |
| `경도` | POINT_ID 위치의 경도, EPSG:4326 |
| `제한속도` | ITS 표준노드링크에서 가장 가까운 링크의 `MAX_SPD` 값 |
| `위험도` | 50m 버퍼 내 고령보행자 사고 기반 위험도 |
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
│       └── business.py
├── Data/
│   ├── (도로명주소)도로구간_경남/
│   │   └── TL_SPRD_MANAGE_48_202605.shp 외 부속 파일
│   ├── ITS_node_link/
│   │   └── MOCT_LINK.shp 외 부속 파일
│   ├── jinju_old_pedestrian_individual_accidents_2020_2025.csv
│   └── jinju_road_points.csv
└── example/
```

## 코드 구조

핵심 처리 함수는 `src/silverwalk/`로 분리되어 있고, `데이터결합.ipynb`는 전체 결합 순서를 실행하는 파이프라인 역할을 합니다.

| 파일 | 역할 |
|---|---|
| `src/silverwalk/config.py` | 데이터 경로, 거리 기준, 최종 컬럼 목록 |
| `src/silverwalk/roads.py` | 도로 데이터 로드, 진주시 필터링, 25m 포인트, 50m 버퍼 생성 |
| `src/silverwalk/features.py` | 기본 좌표 feature 생성 |
| `src/silverwalk/accidents.py` | 사고 데이터 결합 및 위험도 계산 |
| `src/silverwalk/speed.py` | ITS 표준노드링크 제한속도 결합 |
| `src/silverwalk/business.py` | 300m 반경 상가 업종별 개수 결합 |

## 입력 데이터

### 1. 도로명주소 도로구간 데이터

```text
Data/(도로명주소)도로구간_경남/TL_SPRD_MANAGE_48_202605.shp
```

사용 내용:

- 진주시 필터: `SIG_CD == "48170"`
- 도로 클래스 필터: `ROA_CLS_SE in {"3", "4"}`
  - `3`: 로
  - `4`: 길
- 고속도로/대로는 제외합니다.
- 원본 좌표계: EPSG:5179

처리 결과:

- 진주시 도로 라인 위에 25m 간격 포인트 생성
- 각 포인트 주변 50m 버퍼 생성

### 2. 고령보행자 개별 교통사고 데이터

생성 파일:

```text
Data/jinju_old_pedestrian_individual_accidents_2020_2025.csv
```

생성 노트북:

```text
노인보행사고데이터.ipynb
```

수집 방식:

- 공공데이터포털 다발지역 API가 아니라 TAAS GIS 웹페이지 내부 Ajax 요청을 재현합니다.
- TAAS 초기 페이지에서 CSRF 토큰과 세션 쿠키를 받은 뒤 `selectAccidentInfo.do`에 POST 요청합니다.
- 조회 조건:
  - 지역: 진주시 `48170%`
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

- 전국 링크 전체를 직접 최근접 결합하면 무거우므로, 진주시 도로 포인트 범위 주변 bbox로 먼저 자릅니다.
- 링크를 도로 포인트 좌표계인 EPSG:5179로 변환합니다.
- 각 `POINT_ID`에서 가장 가까운 링크 1개를 선택해 `MAX_SPD`를 `제한속도`로 부여합니다.
- 동거리 링크가 여러 개 잡히는 경우 `POINT_ID`, 거리, `LINK_ID` 기준으로 하나만 남깁니다.

### 4. 소상공인시장진흥공단 상가 정보 데이터

```text
Data/소상공인시장진흥공단_상가(상권)정보_경남_202603.csv
```

사용 컬럼:

| 컬럼 | 설명 |
|---|---|
| `시군구명` | 진주시 필터링 |
| `상권업종대분류명` | 상가 업종 대분류 |
| `상권업종중분류명` | 상가 업종 중분류 |
| `경도`, `위도` | 상가 위치, EPSG:4326 |

처리 방식:

- `시군구명 == "진주시"`만 사용합니다.
- 상가 좌표를 EPSG:4326에서 도로 포인트 좌표계로 변환합니다.
- 각 `POINT_ID` 기준 300m 반경 안에 있는 상가를 업종별로 집계합니다.
- 대분류 컬럼과 `대분류_중분류` 컬럼을 최종 CSV에 추가합니다.

## 노트북 실행 순서

### 1. 사고 데이터 수집

```text
노인보행사고데이터.ipynb
```

이 노트북을 실행하면 아래 파일이 생성됩니다.

```text
Data/jinju_old_pedestrian_individual_accidents_2020_2025.csv
```

검증된 수집 건수:

```text
2020    69
2021    81
2022    77
2023    68
2024    80
2025    81
총계    456
```

### 2. 도로 포인트 생성 및 feature 결합

```text
데이터결합.ipynb
```

처리 흐름:

1. 진주시 도로구간 로드
2. 도로 클래스 `3`, `4`만 필터링
3. 도로 라인 위에 25m 간격 포인트 생성
4. 각 포인트의 50m 버퍼 생성
5. 사고 포인트가 버퍼 안에 들어오면 사고 피해 규모 집계
6. 위험도 계산
7. ITS 표준노드링크에서 최근접 링크 제한속도 결합
8. 300m 반경 내 상가 업종별 개수 결합
9. 최종 CSV 저장

최종 저장 파일:

```text
Data/jinju_road_points.csv
```

검증된 행 수:

```text
109,795
```
