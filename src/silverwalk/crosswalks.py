import warnings

import geopandas as gpd


from silverwalk.config import (
    BUFFER_50M,
    CROSSWALK_COLUMN,
    CROSSWALK_SHP,
    TARGET_REGION_NAME,
)

###################################################
# crosswalks.py: 횡단보도 polygon 데이터를 읽고, 각 도로 구간 포인트에 반경 50m 내의 횡단보도 수를 합산하여 추가하는 기능을 제공합니다.
###################################################

CROSSWALK_ID_COL = "MGRNU"


def load_crosswalks(crosswalk_shp=CROSSWALK_SHP):
    """횡단보도 polygon 데이터를 읽습니다."""
    if not crosswalk_shp.exists():
        raise FileNotFoundError(f"횡단보도 shapefile을 찾지 못했습니다: {crosswalk_shp}")

    # 일부 geometry에 닫히지 않은 링이 있어 pyogrio의 on_invalid='fix'로 보정해 읽습니다.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Non closed ring detected.*")
        crosswalks_gdf = gpd.read_file(
            crosswalk_shp,
            encoding="euc-kr",
            on_invalid="fix",
        )

    if CROSSWALK_ID_COL not in crosswalks_gdf.columns:
        crosswalks_gdf[CROSSWALK_ID_COL] = crosswalks_gdf.index.astype(str)

    crosswalks_gdf = crosswalks_gdf.loc[
        crosswalks_gdf.geometry.notna() & ~crosswalks_gdf.geometry.is_empty
    ].copy()

    return crosswalks_gdf


def add_crosswalk_counts(
    final_df,
    points_gdf,
    crosswalk_shp=CROSSWALK_SHP,
    radius_m=BUFFER_50M,
    output_col=CROSSWALK_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 횡단보도 수를 추가합니다."""
    crosswalks_gdf = load_crosswalks(crosswalk_shp=crosswalk_shp).to_crs(points_gdf.crs)

    crosswalk_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    crosswalk_buffers_gdf["geometry"] = crosswalk_buffers_gdf.geometry.buffer(radius_m)

    joined_crosswalks = gpd.sjoin(
        crosswalks_gdf[[CROSSWALK_ID_COL, "geometry"]],
        crosswalk_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    crosswalk_summary = (
        joined_crosswalks.groupby("POINT_ID", as_index=False)[CROSSWALK_ID_COL]
        .nunique()
        .rename(columns={CROSSWALK_ID_COL: output_col})
    )

    result_df = final_df.merge(crosswalk_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 횡단보도 polygon 수: {len(crosswalks_gdf):,}")
    print(f"반경 {radius_m}m 횡단보도-포인트 매칭 수: {len(joined_crosswalks):,}")

    return result_df
