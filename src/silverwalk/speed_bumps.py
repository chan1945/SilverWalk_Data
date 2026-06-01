import warnings

import geopandas as gpd

from silverwalk.config import (
    SPEED_BUMP_COLUMN,
    SPEED_BUMP_RADIUS_M,
    SPEED_BUMP_SHP,
    TARGET_REGION_NAME,
)

###################################################
# speed_bumps.py: 과속방지턱 polygon 데이터를 읽고, 각 도로 구간 포인트에 반경 300m 내의 과속방지턱 수를 합산하여 추가하는 기능을 제공합니다.
###################################################

SPEED_BUMP_ID_COL = "MGRNU"


def load_speed_bumps(speed_bump_shp=SPEED_BUMP_SHP):
    """과속방지턱 polygon 데이터를 읽습니다."""
    if not speed_bump_shp.exists():
        raise FileNotFoundError(f"과속방지턱 shapefile을 찾지 못했습니다: {speed_bump_shp}")

    # 일부 geometry에 닫히지 않은 링이 있어 pyogrio의 on_invalid='fix'로 보정해 읽습니다.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Non closed ring detected.*")
        speed_bumps_gdf = gpd.read_file(
            speed_bump_shp,
            encoding="euc-kr",
            on_invalid="fix",
        )

    if SPEED_BUMP_ID_COL not in speed_bumps_gdf.columns:
        speed_bumps_gdf[SPEED_BUMP_ID_COL] = speed_bumps_gdf.index.astype(str)

    speed_bumps_gdf = speed_bumps_gdf.loc[
        speed_bumps_gdf.geometry.notna() & ~speed_bumps_gdf.geometry.is_empty
    ].copy()

    return speed_bumps_gdf


def add_speed_bump_counts(
    final_df,
    points_gdf,
    speed_bump_shp=SPEED_BUMP_SHP,
    radius_m=SPEED_BUMP_RADIUS_M,
    output_col=SPEED_BUMP_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 과속방지턱 수를 추가합니다."""
    speed_bumps_gdf = load_speed_bumps(speed_bump_shp=speed_bump_shp).to_crs(points_gdf.crs)

    speed_bump_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    speed_bump_buffers_gdf["geometry"] = speed_bump_buffers_gdf.geometry.buffer(radius_m)

    joined_speed_bumps = gpd.sjoin(
        speed_bumps_gdf[[SPEED_BUMP_ID_COL, "geometry"]],
        speed_bump_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    speed_bump_summary = (
        joined_speed_bumps.groupby("POINT_ID", as_index=False)[SPEED_BUMP_ID_COL]
        .nunique()
        .rename(columns={SPEED_BUMP_ID_COL: output_col})
    )

    result_df = final_df.merge(speed_bump_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 과속방지턱 polygon 수: {len(speed_bumps_gdf):,}")
    print(f"반경 {radius_m}m 과속방지턱-포인트 매칭 수: {len(joined_speed_bumps):,}")

    return result_df
