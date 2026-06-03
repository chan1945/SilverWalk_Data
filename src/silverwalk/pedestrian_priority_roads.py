import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from silverwalk.config import (
    BUFFER_50M,
    PEDESTRIAN_PRIORITY_ROAD_COLUMN,
    PEDESTRIAN_PRIORITY_ROAD_CSV,
    TARGET_REGION_NAME,
)

SIDO_COL = "시도명"
ROAD_NAME_COL = "보행자우선도로명"
START_LAT_COL = "보행자우선도로시작점위도"
START_LON_COL = "보행자우선도로시작점경도"
END_LAT_COL = "보행자우선도로종료점위도"
END_LON_COL = "보행자우선도로종료점경도"
PRIORITY_ROAD_ID_COL = "보행자우선도로ID"


###################################################
# 보행자우선도로여부 칼럼 추가
# 서울특별시 보행자우선도로 선분이 각 POINT_ID의 반경 50m 안에 있으면 1로 표시
###################################################


def load_pedestrian_priority_roads(pedestrian_priority_road_csv=PEDESTRIAN_PRIORITY_ROAD_CSV):
    """전국 보행자우선도로 표준데이터에서 서울특별시의 유효 선형 데이터만 읽습니다."""
    if not pedestrian_priority_road_csv.exists():
        raise FileNotFoundError(f"보행자우선도로 CSV를 찾지 못했습니다: {pedestrian_priority_road_csv}")

    roads_df = pd.read_csv(pedestrian_priority_road_csv, encoding="cp949")
    required_cols = [
        SIDO_COL,
        ROAD_NAME_COL,
        START_LAT_COL,
        START_LON_COL,
        END_LAT_COL,
        END_LON_COL,
    ]
    missing_cols = [col for col in required_cols if col not in roads_df.columns]
    if missing_cols:
        raise ValueError(f"보행자우선도로 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(roads_df)
    roads_df = roads_df.loc[roads_df[SIDO_COL].astype(str).str.strip() == "서울특별시"].copy()
    seoul_count = len(roads_df)

    coord_cols = [START_LAT_COL, START_LON_COL, END_LAT_COL, END_LON_COL]
    for col in coord_cols:
        roads_df[col] = pd.to_numeric(roads_df[col], errors="coerce")

    valid_mask = (
        roads_df[START_LAT_COL].between(37, 38)
        & roads_df[END_LAT_COL].between(37, 38)
        & roads_df[START_LON_COL].between(126, 128)
        & roads_df[END_LON_COL].between(126, 128)
    )
    roads_df = roads_df.loc[valid_mask].dropna(subset=coord_cols).copy()
    roads_df = roads_df.reset_index(drop=True)
    roads_df[PRIORITY_ROAD_ID_COL] = roads_df.index.astype(int)
    roads_df["geometry"] = roads_df.apply(
        lambda row: LineString(
            [
                (row[START_LON_COL], row[START_LAT_COL]),
                (row[END_LON_COL], row[END_LAT_COL]),
            ]
        ),
        axis=1,
    )

    print(f"보행자우선도로 전체 행 수: {before_count:,}")
    print(f"{TARGET_REGION_NAME} 보행자우선도로 행 수: {seoul_count:,}")
    print(f"좌표 이상/결측 제외 행 수: {seoul_count - len(roads_df):,}")

    return gpd.GeoDataFrame(roads_df, geometry="geometry", crs="EPSG:4326")


def add_pedestrian_priority_road_presence(
    final_df,
    points_gdf,
    pedestrian_priority_road_csv=PEDESTRIAN_PRIORITY_ROAD_CSV,
    radius_m=BUFFER_50M,
    output_col=PEDESTRIAN_PRIORITY_ROAD_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 보행자우선도로가 있으면 1, 없으면 0을 추가합니다."""
    priority_roads_gdf = load_pedestrian_priority_roads(
        pedestrian_priority_road_csv=pedestrian_priority_road_csv,
    ).to_crs(points_gdf.crs)

    priority_road_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    priority_road_buffers_gdf["geometry"] = priority_road_buffers_gdf.geometry.buffer(radius_m)

    joined_priority_roads = gpd.sjoin(
        priority_roads_gdf[[PRIORITY_ROAD_ID_COL, "geometry"]],
        priority_road_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    priority_road_presence = (
        joined_priority_roads[["POINT_ID"]]
        .drop_duplicates()
        .assign(**{output_col: 1})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(priority_road_presence, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 사용 보행자우선도로 수: {len(priority_roads_gdf):,}")
    print(f"반경 {radius_m}m 보행자우선도로-포인트 매칭 수: {len(joined_priority_roads):,}")
    print(f"보행자우선도로 포함 POINT 수: {result_df[output_col].sum():,}")

    return result_df
