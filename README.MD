# Data Processing

진주시 고령보행자 교통사고 위험도 분석을 위한 데이터 수집 및 결합 작업 공간입니다. 도로명주소 도로구간 데이터에서 진주시 도로 포인트를 만들고, 각 포인트별 위험도와 앞으로 필요할 feature 들을 결합합니다.

## 주요 산출물

최종 산출 파일:

```text
Data/jinju_road_points.csv
```

현재 최종 CSV 컬럼:

```text
POINT_ID, 위도, 경도, 제한속도, 위험도
```

컬럼 설명:

| 컬럼 | 설명 |
|---|---|
| `POINT_ID` | 진주시 도로구간 라인 위에 25m 간격으로 생성한 포인트 ID |
| `위도` | POINT_ID 위치의 위도, EPSG:4326 |
| `경도` | POINT_ID 위치의 경도, EPSG:4326 |
| `제한속도` | ITS 표준노드링크에서 가장 가까운 링크의 `MAX_SPD` 값 |
| `위험도` | 50m 버퍼 내 고령보행자 사고 기반 위험도 |

위험도 계산식:

```text
위험도 = 10 × 사고건수 × (사망자수 + 0.1168 × 중상자수 + 0.0068 × 경상자수)
```

## 디렉터리 구조

```text
.
├── README.MD
├── requirements.txt
├── 노인보행사고데이터.ipynb
├── 데이터결합.ipynb
├── Data/
│   ├── (도로명주소)도로구간_경남/
│   │   └── TL_SPRD_MANAGE_48_202605.shp 외 부속 파일
│   ├── ITS_node_link/
│   │   └── MOCT_LINK.shp 외 부속 파일
│   ├── jinju_old_pedestrian_individual_accidents_2020_2025.csv
│   └── jinju_road_points.csv
└── example/
```

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
8. 최종 CSV 저장

최종 저장 파일:

```text
Data/jinju_road_points.csv
```

검증된 행 수:

```text
109,795
```


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

```text
Data/
├── (도로명주소)도로구간_경남/
│   ├── TL_SPRD_MANAGE_48_202605.shp
│   ├── TL_SPRD_MANAGE_48_202605.shx
│   ├── TL_SPRD_MANAGE_48_202605.dbf
│   ├── TL_SPRD_MANAGE_48_202605.prj
│   └── TL_SPRD_MANAGE_48_202605.cpg
└── ITS_node_link/
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
```

필수 입력 파일:

| 경로 | 설명 |
|---|---|
| `Data/(도로명주소)도로구간_경남/TL_SPRD_MANAGE_48_202605.shp` | 경남 도로명주소 도로구간 |
| `Data/ITS_node_link/MOCT_LINK.shp` | ITS 표준노드링크 링크 데이터 |

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

### 5. Jupyter Notebook 실행

```bash
jupyter notebook
```

브라우저가 열리면 아래 순서대로 노트북을 실행합니다.

### 6. 사고 데이터 수집 노트북 실행

먼저 실행할 노트북:

```text
노인보행사고데이터.ipynb
```

실행 방법:

1. 노트북을 엽니다.
2. 메뉴에서 `Kernel > Restart & Run All`을 실행합니다.
3. 실행이 끝나면 아래 파일이 생성되었는지 확인합니다.

```text
Data/jinju_old_pedestrian_individual_accidents_2020_2025.csv
```

이 노트북은 TAAS 웹 내부 요청을 사용하므로 인터넷 연결이 필요합니다. TAAS 페이지 구조가 바뀌면 수집 코드가 실패할 수 있습니다.

### 7. 도로 포인트 및 feature 결합 노트북 실행

다음으로 실행할 노트북:

```text
데이터결합.ipynb
```

실행 방법:

1. 노트북을 엽니다.
2. 메뉴에서 `Kernel > Restart & Run All`을 실행합니다.
3. 실행이 끝나면 아래 최종 파일이 생성되었는지 확인합니다.

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


### 9. 실행 순서 요약

```text
1. 원천 데이터 파일을 Data/ 하위에 배치
2. pip install -r requirements.txt
3. 노인보행사고데이터.ipynb 실행
4. 데이터결합.ipynb 실행
5. Data/jinju_road_points.csv 확인
```
