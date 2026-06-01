import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    BUS_STOP_COLUMN,
    BUS_STOP_XLSX,
    TARGET_REGION_NAME,
)

###################################################
# bus_stops.py: 서울시 버스정류소 위치 엑셀에서 가상정류장을 제외한 정류장 좌표를 읽고, 각 도로 구간 포인트에 반경 300m 내의 실제 버스정류장 수를 합산하여 추가하는 기능을 제공합니다.
###################################################

BUS_STOP_ID_COL = "NODE_ID"
BUS_STOP_LON_COL = "X좌표"
BUS_STOP_LAT_COL = "Y좌표"
BUS_STOP_TYPE_COL = "정류소타입"
VIRTUAL_BUS_STOP_TYPE = "가상정류장"


def load_bus_stops(bus_stop_xlsx=BUS_STOP_XLSX):
    """서울시 버스정류소 위치 엑셀에서 가상정류장을 제외한 정류장 좌표를 읽습니다."""
    if not bus_stop_xlsx.exists():
        raise FileNotFoundError(f"버스정류장 엑셀 파일을 찾지 못했습니다: {bus_stop_xlsx}")

    required_cols = [
        BUS_STOP_ID_COL,
        BUS_STOP_LON_COL,
        BUS_STOP_LAT_COL,
        BUS_STOP_TYPE_COL,
    ]
    bus_stops_df = pd.read_excel(bus_stop_xlsx)
    missing_cols = [col for col in required_cols if col not in bus_stops_df.columns]
    if missing_cols:
        raise ValueError(f"버스정류장 데이터에 필요한 컬럼이 없습니다: {missing_cols}")
    bus_stops_df = bus_stops_df[required_cols].copy()

    before_count = len(bus_stops_df)
    bus_stops_df[BUS_STOP_TYPE_COL] = bus_stops_df[BUS_STOP_TYPE_COL].astype(str).str.strip()
    bus_stops_df = bus_stops_df.loc[
        ~bus_stops_df[BUS_STOP_TYPE_COL].eq(VIRTUAL_BUS_STOP_TYPE)
    ].copy()

    bus_stops_df[BUS_STOP_LON_COL] = pd.to_numeric(bus_stops_df[BUS_STOP_LON_COL], errors="coerce")
    bus_stops_df[BUS_STOP_LAT_COL] = pd.to_numeric(bus_stops_df[BUS_STOP_LAT_COL], errors="coerce")
    bus_stops_df = bus_stops_df.dropna(subset=[BUS_STOP_LON_COL, BUS_STOP_LAT_COL]).copy()

    excluded_count = before_count - len(bus_stops_df)
    print(f"{TARGET_REGION_NAME} 버스정류장 전체 행 수: {before_count:,}")
    print(f"가상정류장 및 좌표 결측 제외 수: {excluded_count:,}")

    return gpd.GeoDataFrame(
        bus_stops_df,
        geometry=gpd.points_from_xy(bus_stops_df[BUS_STOP_LON_COL], bus_stops_df[BUS_STOP_LAT_COL]),
        crs="EPSG:4326",
    )


def add_bus_stop_counts(
    final_df,
    points_gdf,
    bus_stop_xlsx=BUS_STOP_XLSX,
    radius_m=BUFFER_300M,
    output_col=BUS_STOP_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 실제 버스정류장 수를 추가합니다."""
    bus_stops_gdf = load_bus_stops(bus_stop_xlsx=bus_stop_xlsx).to_crs(points_gdf.crs)

    bus_stop_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    bus_stop_buffers_gdf["geometry"] = bus_stop_buffers_gdf.geometry.buffer(radius_m)

    joined_bus_stops = gpd.sjoin(
        bus_stops_gdf[[BUS_STOP_ID_COL, "geometry"]],
        bus_stop_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    bus_stop_summary = (
        joined_bus_stops.groupby("POINT_ID", as_index=False)[BUS_STOP_ID_COL]
        .nunique()
        .rename(columns={BUS_STOP_ID_COL: output_col})
    )

    result_df = final_df.merge(bus_stop_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 사용 버스정류장 수: {len(bus_stops_gdf):,}")
    print(f"반경 {radius_m}m 버스정류장-포인트 매칭 수: {len(joined_bus_stops):,}")

    return result_df
