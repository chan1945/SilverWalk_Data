import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    SENIOR_DISABLED_PROTECTION_ZONE_COLUMN,
    SENIOR_DISABLED_PROTECTION_ZONE_CSV,
    TARGET_REGION_NAME,
)

SIDO_COL = "시도명"
FACILITY_NAME_COL = "대상시설명"
LAT_COL = "위도"
LON_COL = "경도"
PROTECTION_ZONE_ID_COL = "노인장애인보호구역ID"


###################################################
# 노인장애인보호구역여부 칼럼 추가
# 서울특별시 보호구역 시설점이 각 POINT_ID의 반경 300m 안에 있으면 1로 표시
###################################################


def load_senior_disabled_protection_zones(
    protection_zone_csv=SENIOR_DISABLED_PROTECTION_ZONE_CSV,
):
    """전국 노인장애인보호구역 표준데이터에서 서울특별시의 유효 좌표만 읽습니다."""
    if not protection_zone_csv.exists():
        raise FileNotFoundError(f"노인장애인보호구역 CSV를 찾지 못했습니다: {protection_zone_csv}")

    zones_df = pd.read_csv(protection_zone_csv, encoding="cp949")
    required_cols = [SIDO_COL, FACILITY_NAME_COL, LAT_COL, LON_COL]
    missing_cols = [col for col in required_cols if col not in zones_df.columns]
    if missing_cols:
        raise ValueError(f"노인장애인보호구역 CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(zones_df)
    zones_df = zones_df.loc[zones_df[SIDO_COL].astype(str).str.strip() == "서울특별시"].copy()
    seoul_count = len(zones_df)
    zones_df[LAT_COL] = pd.to_numeric(zones_df[LAT_COL], errors="coerce")
    zones_df[LON_COL] = pd.to_numeric(zones_df[LON_COL], errors="coerce")

    swapped_mask = zones_df[LAT_COL].between(126, 128) & zones_df[LON_COL].between(37, 38)
    if swapped_mask.any():
        zones_df.loc[swapped_mask, [LAT_COL, LON_COL]] = (
            zones_df.loc[swapped_mask, [LON_COL, LAT_COL]].to_numpy()
        )

    valid_mask = zones_df[LAT_COL].between(37, 38) & zones_df[LON_COL].between(126, 128)
    zones_df = zones_df.loc[valid_mask].copy()
    zones_df = zones_df.dropna(subset=[FACILITY_NAME_COL, LAT_COL, LON_COL]).copy()
    zones_df = zones_df.reset_index(drop=True)
    zones_df[PROTECTION_ZONE_ID_COL] = zones_df.index.astype(int)

    print(f"노인장애인보호구역 전체 행 수: {before_count:,}")
    print(f"{TARGET_REGION_NAME} 노인장애인보호구역 행 수: {seoul_count:,}")
    print(f"좌표 뒤집힘 보정 행 수: {int(swapped_mask.sum()):,}")
    print(f"좌표 이상/결측 제외 행 수: {seoul_count - len(zones_df):,}")

    return gpd.GeoDataFrame(
        zones_df,
        geometry=gpd.points_from_xy(zones_df[LON_COL], zones_df[LAT_COL]),
        crs="EPSG:4326",
    )


def add_senior_disabled_protection_zone_presence(
    final_df,
    points_gdf,
    protection_zone_csv=SENIOR_DISABLED_PROTECTION_ZONE_CSV,
    radius_m=BUFFER_300M,
    output_col=SENIOR_DISABLED_PROTECTION_ZONE_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 노인장애인보호구역이 있으면 1, 없으면 0을 추가합니다."""
    zones_gdf = load_senior_disabled_protection_zones(
        protection_zone_csv=protection_zone_csv,
    ).to_crs(points_gdf.crs)

    zone_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    zone_buffers_gdf["geometry"] = zone_buffers_gdf.geometry.buffer(radius_m)

    joined_zones = gpd.sjoin(
        zones_gdf[[PROTECTION_ZONE_ID_COL, "geometry"]],
        zone_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    zone_presence = (
        joined_zones[["POINT_ID"]]
        .drop_duplicates()
        .assign(**{output_col: 1})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(zone_presence, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 사용 노인장애인보호구역 수: {len(zones_gdf):,}")
    print(f"반경 {radius_m}m 노인장애인보호구역-포인트 매칭 수: {len(joined_zones):,}")
    print(f"노인장애인보호구역 포함 POINT 수: {result_df[output_col].sum():,}")

    return result_df
