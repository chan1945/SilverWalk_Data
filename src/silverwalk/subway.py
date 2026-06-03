import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    SUBWAY_STATION_COLUMN,
    SUBWAY_STATION_CSV,
    TARGET_REGION_NAME,
)

STATION_ID_COL = "고유역번호(외부역코드)"
STATION_LON_COL = "경도"
STATION_LAT_COL = "위도"


def load_subway_stations(subway_station_csv=SUBWAY_STATION_CSV):
    """서울교통공사 역사 좌표 CSV에서 좌표가 있는 역사를 읽습니다."""
    if not subway_station_csv.exists():
        raise FileNotFoundError(f"지하철 역사 좌표 CSV를 찾지 못했습니다: {subway_station_csv}")

    stations_df = pd.read_csv(subway_station_csv, encoding="cp949")
    required_cols = [STATION_ID_COL, STATION_LON_COL, STATION_LAT_COL]
    missing_cols = [col for col in required_cols if col not in stations_df.columns]
    if missing_cols:
        raise ValueError(f"지하철 역사 좌표 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(stations_df)
    stations_df[STATION_LON_COL] = pd.to_numeric(stations_df[STATION_LON_COL], errors="coerce")
    stations_df[STATION_LAT_COL] = pd.to_numeric(stations_df[STATION_LAT_COL], errors="coerce")
    stations_df = stations_df.dropna(subset=[STATION_ID_COL, STATION_LON_COL, STATION_LAT_COL]).copy()

    print(f"{TARGET_REGION_NAME} 지하철 역사 전체 행 수: {before_count:,}")
    print(f"좌표 결측 제외 역사 수: {before_count - len(stations_df):,}")

    return gpd.GeoDataFrame(
        stations_df,
        geometry=gpd.points_from_xy(stations_df[STATION_LON_COL], stations_df[STATION_LAT_COL]),
        crs="EPSG:4326",
    )


def add_subway_station_counts(
    final_df,
    points_gdf,
    subway_station_csv=SUBWAY_STATION_CSV,
    radius_m=BUFFER_300M,
    output_col=SUBWAY_STATION_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 지하철 역사 수를 추가합니다."""
    stations_gdf = load_subway_stations(subway_station_csv=subway_station_csv).to_crs(points_gdf.crs)

    station_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    station_buffers_gdf["geometry"] = station_buffers_gdf.geometry.buffer(radius_m)

    joined_stations = gpd.sjoin(
        stations_gdf[[STATION_ID_COL, "geometry"]],
        station_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    station_summary = (
        joined_stations.groupby("POINT_ID", as_index=False)[STATION_ID_COL]
        .nunique()
        .rename(columns={STATION_ID_COL: output_col})
    )

    result_df = final_df.merge(station_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 사용 지하철 역사 수: {len(stations_gdf):,}")
    print(f"반경 {radius_m}m 지하철 역사-포인트 매칭 수: {len(joined_stations):,}")

    return result_df
