import warnings

import geopandas as gpd

from silverwalk.config import (
    BUFFER_50M,
    INTERSECTION_COLUMN,
    INTERSECTION_SHP,
    TARGET_REGION_NAME,
)

###################################################
# intersections.py: 교차로 point 데이터를 읽고, 각 도로 구간 포인트에 반경 50m 내의 교차로 수를 합산하여 추가하는 기능을 제공합니다.
###################################################

INTERSECTION_ID_COL = "MGRNU"


def load_intersections(intersection_shp=INTERSECTION_SHP):
    """교차로 point 데이터를 읽습니다."""
    if not intersection_shp.exists():
        raise FileNotFoundError(f"교차로 shapefile을 찾지 못했습니다: {intersection_shp}")

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="One or several characters couldn't be converted.*")
        intersections_gdf = gpd.read_file(intersection_shp, encoding="euc-kr")

    if INTERSECTION_ID_COL not in intersections_gdf.columns:
        intersections_gdf[INTERSECTION_ID_COL] = intersections_gdf.index.astype(str)

    intersections_gdf = intersections_gdf.loc[
        intersections_gdf.geometry.notna() & ~intersections_gdf.geometry.is_empty
    ].copy()

    return intersections_gdf


def add_intersection_counts(
    final_df,
    points_gdf,
    intersection_shp=INTERSECTION_SHP,
    radius_m=BUFFER_50M,
    output_col=INTERSECTION_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 교차로 수를 추가합니다."""
    intersections_gdf = load_intersections(intersection_shp=intersection_shp).to_crs(points_gdf.crs)

    intersection_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    intersection_buffers_gdf["geometry"] = intersection_buffers_gdf.geometry.buffer(radius_m)

    joined_intersections = gpd.sjoin(
        intersections_gdf[[INTERSECTION_ID_COL, "geometry"]],
        intersection_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    intersection_summary = (
        joined_intersections.groupby("POINT_ID", as_index=False)[INTERSECTION_ID_COL]
        .nunique()
        .rename(columns={INTERSECTION_ID_COL: output_col})
    )

    result_df = final_df.merge(intersection_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 교차로 point 수: {len(intersections_gdf):,}")
    print(f"반경 {radius_m}m 교차로-포인트 매칭 수: {len(joined_intersections):,}")

    return result_df
