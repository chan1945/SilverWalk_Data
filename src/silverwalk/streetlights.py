import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_50M,
    STREETLIGHT_COLUMN,
    STREETLIGHT_CSV,
    TARGET_REGION_NAME,
)

STREETLIGHT_ID_COL = "관리번호"
LAT_COL = "위도"
LON_COL = "경도"
###################################################
# 가로등개수 칼럼에 추가
# 각 POINT_ID의 반경 50m 안에 있는 자산을 기준으로 추가
###################################################
def load_streetlights(streetlight_csv=STREETLIGHT_CSV):
    """가로등 위치 CSV에서 서울 범위의 유효 좌표만 읽습니다."""
    if not streetlight_csv.exists():
        raise FileNotFoundError(f"가로등 CSV를 찾지 못했습니다: {streetlight_csv}")

    streetlights_df = pd.read_csv(streetlight_csv, encoding="cp949")
    required_cols = [STREETLIGHT_ID_COL, LAT_COL, LON_COL]
    missing_cols = [col for col in required_cols if col not in streetlights_df.columns]
    if missing_cols:
        raise ValueError(f"가로등 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(streetlights_df)
    streetlights_df[LAT_COL] = pd.to_numeric(streetlights_df[LAT_COL], errors="coerce")
    streetlights_df[LON_COL] = pd.to_numeric(streetlights_df[LON_COL], errors="coerce")

    swapped_mask = streetlights_df[LAT_COL].between(126, 128) & streetlights_df[LON_COL].between(37, 38)
    if swapped_mask.any():
        streetlights_df.loc[swapped_mask, [LAT_COL, LON_COL]] = (
            streetlights_df.loc[swapped_mask, [LON_COL, LAT_COL]].to_numpy()
        )

    valid_mask = streetlights_df[LAT_COL].between(37, 38) & streetlights_df[LON_COL].between(126, 128)
    streetlights_df = streetlights_df.loc[valid_mask].copy()
    streetlights_df = streetlights_df.dropna(subset=[STREETLIGHT_ID_COL, LAT_COL, LON_COL]).copy()

    print(f"{TARGET_REGION_NAME} 가로등 전체 행 수: {before_count:,}")
    print(f"좌표 뒤집힘 보정 행 수: {int(swapped_mask.sum()):,}")
    print(f"좌표 이상/결측 제외 행 수: {before_count - len(streetlights_df):,}")

    return gpd.GeoDataFrame(
        streetlights_df,
        geometry=gpd.points_from_xy(streetlights_df[LON_COL], streetlights_df[LAT_COL]),
        crs="EPSG:4326",
    )


def add_streetlight_counts(
    final_df,
    points_gdf,
    streetlight_csv=STREETLIGHT_CSV,
    radius_m=BUFFER_50M,
    output_col=STREETLIGHT_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 가로등 수를 추가합니다."""
    streetlights_gdf = load_streetlights(streetlight_csv=streetlight_csv).to_crs(points_gdf.crs)

    streetlight_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    streetlight_buffers_gdf["geometry"] = streetlight_buffers_gdf.geometry.buffer(radius_m)

    joined_streetlights = gpd.sjoin(
        streetlights_gdf[[STREETLIGHT_ID_COL, "geometry"]],
        streetlight_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    streetlight_summary = (
        joined_streetlights.groupby("POINT_ID", as_index=False)[STREETLIGHT_ID_COL]
        .nunique()
        .rename(columns={STREETLIGHT_ID_COL: output_col})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(streetlight_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"반경 {radius_m}m 가로등-포인트 매칭 수: {len(joined_streetlights):,}")

    return result_df
