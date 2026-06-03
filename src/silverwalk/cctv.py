import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_50M,
    CCTV_COLUMN,
    CCTV_CSV,
    TARGET_REGION_NAME,
)

CCTV_ADDRESS_COL = "고정형CCTV지번주소"
CCTV_LOCATION_COL = "단속지점명"
LAT_COL = "위도"
LON_COL = "경도"
###################################################
# CCTV 개수 칼럼에 추가
# 각 POINT_ID의 반경 50m 안에 있는 자산을 기준으로 추가
###################################################


def load_cctv_points(cctv_csv=CCTV_CSV):
    """CCTV 위치 CSV에서 서울 범위의 유효 좌표만 읽습니다."""
    if not cctv_csv.exists():
        raise FileNotFoundError(f"CCTV CSV를 찾지 못했습니다: {cctv_csv}")

    cctv_df = pd.read_csv(cctv_csv, encoding="cp949")
    required_cols = [CCTV_ADDRESS_COL, LAT_COL, LON_COL]
    missing_cols = [col for col in required_cols if col not in cctv_df.columns]
    if missing_cols:
        raise ValueError(f"CCTV CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(cctv_df)
    cctv_df[LAT_COL] = pd.to_numeric(cctv_df[LAT_COL], errors="coerce")
    cctv_df[LON_COL] = pd.to_numeric(cctv_df[LON_COL], errors="coerce")

    swapped_mask = cctv_df[LAT_COL].between(126, 128) & cctv_df[LON_COL].between(37, 38)
    if swapped_mask.any():
        cctv_df.loc[swapped_mask, [LAT_COL, LON_COL]] = (
            cctv_df.loc[swapped_mask, [LON_COL, LAT_COL]].to_numpy()
        )

    valid_mask = cctv_df[LAT_COL].between(37, 38) & cctv_df[LON_COL].between(126, 128)
    cctv_df = cctv_df.loc[valid_mask].copy()
    cctv_df = cctv_df.dropna(subset=[CCTV_ADDRESS_COL, LAT_COL, LON_COL]).copy()
    cctv_df = cctv_df.reset_index(drop=True)
    cctv_df["CCTV_ID"] = (
        cctv_df[CCTV_ADDRESS_COL].astype(str).str.strip()
        + "_"
        + cctv_df.get(CCTV_LOCATION_COL, pd.Series("", index=cctv_df.index)).astype(str).str.strip()
        + "_"
        + cctv_df.index.astype(str)
    )

    print(f"{TARGET_REGION_NAME} CCTV 전체 행 수: {before_count:,}")
    print(f"좌표 뒤집힘 보정 행 수: {int(swapped_mask.sum()):,}")
    print(f"좌표 이상/결측 제외 행 수: {before_count - len(cctv_df):,}")

    return gpd.GeoDataFrame(
        cctv_df,
        geometry=gpd.points_from_xy(cctv_df[LON_COL], cctv_df[LAT_COL]),
        crs="EPSG:4326",
    )


def add_cctv_counts(
    final_df,
    points_gdf,
    cctv_csv=CCTV_CSV,
    radius_m=BUFFER_50M,
    output_col=CCTV_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 CCTV 수를 추가합니다."""
    cctv_gdf = load_cctv_points(cctv_csv=cctv_csv).to_crs(points_gdf.crs)

    cctv_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    cctv_buffers_gdf["geometry"] = cctv_buffers_gdf.geometry.buffer(radius_m)

    joined_cctv = gpd.sjoin(
        cctv_gdf[["CCTV_ID", "geometry"]],
        cctv_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    cctv_summary = (
        joined_cctv.groupby("POINT_ID", as_index=False)["CCTV_ID"]
        .nunique()
        .rename(columns={"CCTV_ID": output_col})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(cctv_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"반경 {radius_m}m CCTV-포인트 매칭 수: {len(joined_cctv):,}")

    return result_df
