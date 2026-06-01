import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    SOCIAL_WELFARE_COLUMN,
    SOCIAL_WELFARE_GEOCODED_CSV,
    TARGET_REGION_NAME,
)


FACILITY_ID_COL = "시설ID"
LON_COL = "경도"
LAT_COL = "위도"
GEOCODING_STATUS_COL = "지오코딩상태"


def load_geocoded_social_welfare_facilities(geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV):
    """지오코딩 완료 CSV에서 좌표가 있는 노인의료복지시설만 읽습니다."""
    if not geocoded_csv.exists():
        raise FileNotFoundError(f"노인의료복지시설 지오코딩 CSV를 찾지 못했습니다: {geocoded_csv}")

    facilities_df = pd.read_csv(geocoded_csv, encoding="utf-8-sig")
    required_cols = [FACILITY_ID_COL, LON_COL, LAT_COL]
    missing_cols = [col for col in required_cols if col not in facilities_df.columns]
    if missing_cols:
        raise ValueError(f"노인의료복지시설 지오코딩 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    facilities_df[LON_COL] = pd.to_numeric(facilities_df[LON_COL], errors="coerce")
    facilities_df[LAT_COL] = pd.to_numeric(facilities_df[LAT_COL], errors="coerce")

    before_count = len(facilities_df)
    if GEOCODING_STATUS_COL in facilities_df.columns:
        facilities_df = facilities_df.loc[facilities_df[GEOCODING_STATUS_COL].eq("OK")].copy()

    facilities_df = facilities_df.dropna(subset=[LON_COL, LAT_COL]).copy()
    failed_count = before_count - len(facilities_df)

    print(f"{TARGET_REGION_NAME} 노인의료복지시설 전체 행 수: {before_count:,}")
    print(f"지오코딩 실패 제외 시설 수: {failed_count:,}")

    return gpd.GeoDataFrame(
        facilities_df,
        geometry=gpd.points_from_xy(facilities_df[LON_COL], facilities_df[LAT_COL]),
        crs="EPSG:4326",
    )


def add_social_welfare_facility_counts(
    final_df,
    points_gdf,
    geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV,
    radius_m=300,
    output_col=SOCIAL_WELFARE_COLUMN,
):
    """각 POINT_ID의 300m 반경 안에 있는 노인의료복지시설 개수를 추가합니다."""
    facility_points_gdf = load_geocoded_social_welfare_facilities(
        geocoded_csv=geocoded_csv,
    ).to_crs(points_gdf.crs)

    welfare_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    welfare_buffers_gdf["geometry"] = welfare_buffers_gdf.geometry.buffer(radius_m)

    joined_facilities = gpd.sjoin(
        facility_points_gdf[[FACILITY_ID_COL, "geometry"]],
        welfare_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    facility_summary = (
        joined_facilities.groupby("POINT_ID", as_index=False)[FACILITY_ID_COL]
        .nunique()
        .rename(columns={FACILITY_ID_COL: output_col})
    )

    result_df = final_df.merge(facility_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 노인의료복지시설 사용 좌표 수: {len(facility_points_gdf):,}")
    print(f"반경 {radius_m}m 노인의료복지시설-포인트 매칭 수: {len(joined_facilities):,}")

    return result_df
