import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    PUBLIC_PARKING_COLUMN,
    PUBLIC_PARKING_CSV,
    TARGET_REGION_NAME,
)

PARKING_ID_COL = "주차장코드"
PARKING_LAT_COL = "위도"
PARKING_LON_COL = "경도"


###################################################
# 공영주차장개수 칼럼 추가
# 각 POINT_ID의 반경 300m 안에 있는 공영주차장을 기준으로 추가
###################################################


def load_public_parking(public_parking_csv=PUBLIC_PARKING_CSV):
    """서울시 공영주차장 안내 CSV에서 유효 좌표가 있는 주차장만 읽습니다."""
    if not public_parking_csv.exists():
        raise FileNotFoundError(f"공영주차장 CSV를 찾지 못했습니다: {public_parking_csv}")

    parking_df = pd.read_csv(public_parking_csv, encoding="cp949")
    required_cols = [PARKING_ID_COL, PARKING_LAT_COL, PARKING_LON_COL]
    missing_cols = [col for col in required_cols if col not in parking_df.columns]
    if missing_cols:
        raise ValueError(f"공영주차장 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(parking_df)
    parking_df[PARKING_LAT_COL] = pd.to_numeric(parking_df[PARKING_LAT_COL], errors="coerce")
    parking_df[PARKING_LON_COL] = pd.to_numeric(parking_df[PARKING_LON_COL], errors="coerce")

    swapped_mask = parking_df[PARKING_LAT_COL].between(126, 128) & parking_df[PARKING_LON_COL].between(37, 38)
    if swapped_mask.any():
        parking_df.loc[swapped_mask, [PARKING_LAT_COL, PARKING_LON_COL]] = (
            parking_df.loc[swapped_mask, [PARKING_LON_COL, PARKING_LAT_COL]].to_numpy()
        )

    valid_mask = parking_df[PARKING_LAT_COL].between(37, 38) & parking_df[PARKING_LON_COL].between(126, 128)
    parking_df = parking_df.loc[valid_mask].copy()
    parking_df = parking_df.dropna(subset=[PARKING_ID_COL, PARKING_LAT_COL, PARKING_LON_COL]).copy()

    print(f"{TARGET_REGION_NAME} 공영주차장 전체 행 수: {before_count:,}")
    print(f"좌표 뒤집힘 보정 행 수: {int(swapped_mask.sum()):,}")
    print(f"좌표 이상/결측 제외 행 수: {before_count - len(parking_df):,}")

    return gpd.GeoDataFrame(
        parking_df,
        geometry=gpd.points_from_xy(parking_df[PARKING_LON_COL], parking_df[PARKING_LAT_COL]),
        crs="EPSG:4326",
    )


def add_public_parking_counts(
    final_df,
    points_gdf,
    public_parking_csv=PUBLIC_PARKING_CSV,
    radius_m=BUFFER_300M,
    output_col=PUBLIC_PARKING_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 공영주차장 수를 추가합니다."""
    parking_gdf = load_public_parking(public_parking_csv=public_parking_csv).to_crs(points_gdf.crs)

    parking_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    parking_buffers_gdf["geometry"] = parking_buffers_gdf.geometry.buffer(radius_m)

    joined_parking = gpd.sjoin(
        parking_gdf[[PARKING_ID_COL, "geometry"]],
        parking_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    parking_summary = (
        joined_parking.groupby("POINT_ID", as_index=False)[PARKING_ID_COL]
        .nunique()
        .rename(columns={PARKING_ID_COL: output_col})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(parking_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 사용 공영주차장 수: {len(parking_gdf):,}")
    print(f"반경 {radius_m}m 공영주차장-포인트 매칭 수: {len(joined_parking):,}")

    return result_df
