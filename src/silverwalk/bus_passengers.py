import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    BUS_ALIGHTING_TOTAL_COLUMN,
    BUS_BOARDING_TOTAL_COLUMN,
    BUS_RIDE_ALIGHT_TOTAL_COLUMN,
    BUS_STOP_PASSENGER_CSV,
    BUS_STOP_XLSX,
    TARGET_REGION_NAME,
)

BUS_STOP_ID_COL = "NODE_ID"
BUS_STOP_LON_COL = "X좌표"
BUS_STOP_LAT_COL = "Y좌표"
BUS_STOP_TYPE_COL = "정류소타입"
VIRTUAL_BUS_STOP_TYPE = "가상정류장"
 
PASSENGER_STOP_ID_COL = "표준버스정류장ID"
USE_DATE_COL = "사용일자"
BOARDING_COL = "승차총승객수"
ALIGHTING_COL = "하차총승객수"

###################################################
# 버스 승하차 인원을 칼럼에 '승차총승객수', '하차총승객수', '승하차통승객수' 추가
# 각 POINT_ID의 반경 300m 안에 있는 대상 정류장을 기준으로 추가합니다.
###################################################


def load_bus_passenger_stops(
    bus_stop_xlsx=BUS_STOP_XLSX,
    passenger_csv=BUS_STOP_PASSENGER_CSV,
):
    """정류장 위치와 승하차 인원 CSV를 정류장 ID 기준으로 결합해 좌표가 있는 승하차 지점을 만듭니다."""
    if not bus_stop_xlsx.exists():
        raise FileNotFoundError(f"버스정류장 엑셀 파일을 찾지 못했습니다: {bus_stop_xlsx}")
    if not passenger_csv.exists():
        raise FileNotFoundError(f"버스 승하차 인원 CSV를 찾지 못했습니다: {passenger_csv}")

    stop_required_cols = [
        BUS_STOP_ID_COL,
        BUS_STOP_LON_COL,
        BUS_STOP_LAT_COL,
        BUS_STOP_TYPE_COL,
    ]
    stops_df = pd.read_excel(bus_stop_xlsx)
    missing_stop_cols = [col for col in stop_required_cols if col not in stops_df.columns]
    if missing_stop_cols:
        raise ValueError(f"버스정류장 위치 데이터에 필요한 컬럼이 없습니다: {missing_stop_cols}")

    stops_df = stops_df[stop_required_cols].copy()
    stops_df[BUS_STOP_TYPE_COL] = stops_df[BUS_STOP_TYPE_COL].astype(str).str.strip()
    stops_df = stops_df.loc[~stops_df[BUS_STOP_TYPE_COL].eq(VIRTUAL_BUS_STOP_TYPE)].copy()
    stops_df[BUS_STOP_ID_COL] = pd.to_numeric(stops_df[BUS_STOP_ID_COL], errors="coerce")
    stops_df[BUS_STOP_LON_COL] = pd.to_numeric(stops_df[BUS_STOP_LON_COL], errors="coerce")
    stops_df[BUS_STOP_LAT_COL] = pd.to_numeric(stops_df[BUS_STOP_LAT_COL], errors="coerce")
    stops_df = stops_df.dropna(subset=[BUS_STOP_ID_COL, BUS_STOP_LON_COL, BUS_STOP_LAT_COL]).copy()
    stops_df[BUS_STOP_ID_COL] = stops_df[BUS_STOP_ID_COL].astype("int64")

    passenger_required_cols = [
        USE_DATE_COL,
        PASSENGER_STOP_ID_COL,
        BOARDING_COL,
        ALIGHTING_COL,
    ]
    passengers_df = pd.read_csv(passenger_csv, encoding="cp949", usecols=passenger_required_cols)
    missing_passenger_cols = [col for col in passenger_required_cols if col not in passengers_df.columns]
    if missing_passenger_cols:
        raise ValueError(f"버스 승하차 인원 CSV에 필요한 컬럼이 없습니다: {missing_passenger_cols}")

    passengers_df[PASSENGER_STOP_ID_COL] = pd.to_numeric(
        passengers_df[PASSENGER_STOP_ID_COL],
        errors="coerce",
    )
    passengers_df[BOARDING_COL] = pd.to_numeric(passengers_df[BOARDING_COL], errors="coerce").fillna(0)
    passengers_df[ALIGHTING_COL] = pd.to_numeric(passengers_df[ALIGHTING_COL], errors="coerce").fillna(0)
    passengers_df = passengers_df.dropna(subset=[PASSENGER_STOP_ID_COL]).copy()
    passengers_df[PASSENGER_STOP_ID_COL] = passengers_df[PASSENGER_STOP_ID_COL].astype("int64")

    date_min = passengers_df[USE_DATE_COL].min()
    date_max = passengers_df[USE_DATE_COL].max()
    date_count = passengers_df[USE_DATE_COL].nunique()

    passenger_summary = (
        passengers_df.groupby(PASSENGER_STOP_ID_COL, as_index=False)[[BOARDING_COL, ALIGHTING_COL]]
        .sum()
        .rename(
            columns={
                PASSENGER_STOP_ID_COL: BUS_STOP_ID_COL,
                BOARDING_COL: BUS_BOARDING_TOTAL_COLUMN,
                ALIGHTING_COL: BUS_ALIGHTING_TOTAL_COLUMN,
            }
        )
    )
    passenger_summary[BUS_RIDE_ALIGHT_TOTAL_COLUMN] = (
        passenger_summary[BUS_BOARDING_TOTAL_COLUMN] + passenger_summary[BUS_ALIGHTING_TOTAL_COLUMN]
    )

    passenger_stops_df = stops_df.merge(passenger_summary, on=BUS_STOP_ID_COL, how="inner")
    numeric_cols = [
        BUS_BOARDING_TOTAL_COLUMN,
        BUS_ALIGHTING_TOTAL_COLUMN,
        BUS_RIDE_ALIGHT_TOTAL_COLUMN,
    ]
    passenger_stops_df[numeric_cols] = passenger_stops_df[numeric_cols].round().astype("int64")

    print(f"{TARGET_REGION_NAME} 버스 승하차 원본 행 수: {len(passengers_df):,}")
    print(f"버스 승하차 집계 기간: {date_min}~{date_max} ({date_count:,}일)")
    print(f"위치 매칭된 버스정류장 수: {len(passenger_stops_df):,}")

    return gpd.GeoDataFrame(
        passenger_stops_df,
        geometry=gpd.points_from_xy(passenger_stops_df[BUS_STOP_LON_COL], passenger_stops_df[BUS_STOP_LAT_COL]),
        crs="EPSG:4326",
    )


def add_bus_passenger_totals(
    final_df,
    points_gdf,
    bus_stop_xlsx=BUS_STOP_XLSX,
    passenger_csv=BUS_STOP_PASSENGER_CSV,
    radius_m=BUFFER_300M,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 정류장의 승하차 총승객수를 합산합니다."""
    passenger_stops_gdf = load_bus_passenger_stops(
        bus_stop_xlsx=bus_stop_xlsx,
        passenger_csv=passenger_csv,
    ).to_crs(points_gdf.crs)

    passenger_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    passenger_buffers_gdf["geometry"] = passenger_buffers_gdf.geometry.buffer(radius_m)

    passenger_cols = [
        BUS_BOARDING_TOTAL_COLUMN,
        BUS_ALIGHTING_TOTAL_COLUMN,
        BUS_RIDE_ALIGHT_TOTAL_COLUMN,
    ]
    joined_passengers = gpd.sjoin(
        passenger_stops_gdf[[BUS_STOP_ID_COL, *passenger_cols, "geometry"]],
        passenger_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    passenger_point_summary = (
        joined_passengers.groupby("POINT_ID", as_index=False)[passenger_cols]
        .sum()
    )

    result_df = final_df.drop(columns=[col for col in passenger_cols if col in final_df.columns], errors="ignore")
    result_df = result_df.merge(passenger_point_summary, on="POINT_ID", how="left")
    result_df[passenger_cols] = result_df[passenger_cols].fillna(0).round().astype("int64")

    print(f"반경 {radius_m}m 버스 승하차 정류장-포인트 매칭 수: {len(joined_passengers):,}")

    return result_df
