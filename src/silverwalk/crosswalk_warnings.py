import geopandas as gpd

from silverwalk.config import (
    BUFFER_50M,
    CROSSWALK_WARNING_COLUMN,
    CROSSWALK_WARNING_SHP,
    TARGET_REGION_NAME,
)


CROSSWALK_WARNING_ID_COL = "MGRNU"


###################################################
# crosswalk_warnings.py: 횡단보도예고표시 point 데이터를 읽고, 각 도로 구간 포인트에 반경 50m 내의 횡단보도예고표시 존재 여부를 추가하는 기능을 제공합니다.
###################################################

def load_crosswalk_warnings(crosswalk_warning_shp=CROSSWALK_WARNING_SHP):
    """횡단보도예고표시 point 데이터를 읽습니다."""
    if not crosswalk_warning_shp.exists():
        raise FileNotFoundError(f"횡단보도예고표시 shapefile을 찾지 못했습니다: {crosswalk_warning_shp}")

    warnings_gdf = gpd.read_file(crosswalk_warning_shp, encoding="euc-kr")

    if CROSSWALK_WARNING_ID_COL not in warnings_gdf.columns:
        warnings_gdf[CROSSWALK_WARNING_ID_COL] = warnings_gdf.index.astype(str)

    warnings_gdf = warnings_gdf.loc[
        warnings_gdf.geometry.notna() & ~warnings_gdf.geometry.is_empty
    ].copy()

    return warnings_gdf


def add_crosswalk_warning_presence(
    final_df,
    points_gdf,
    crosswalk_warning_shp=CROSSWALK_WARNING_SHP,
    radius_m=BUFFER_50M,
    output_col=CROSSWALK_WARNING_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 횡단보도예고표시가 있으면 1, 없으면 0을 추가합니다."""
    warnings_gdf = load_crosswalk_warnings(
        crosswalk_warning_shp=crosswalk_warning_shp,
    ).to_crs(points_gdf.crs)

    warning_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    warning_buffers_gdf["geometry"] = warning_buffers_gdf.geometry.buffer(radius_m)

    joined_warnings = gpd.sjoin(
        warnings_gdf[[CROSSWALK_WARNING_ID_COL, "geometry"]],
        warning_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    warning_presence = (
        joined_warnings[["POINT_ID"]]
        .drop_duplicates()
        .assign(**{output_col: 1})
    )

    result_df = final_df.merge(warning_presence, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 횡단보도예고표시 point 수: {len(warnings_gdf):,}")
    print(f"반경 {radius_m}m 횡단보도예고표시-포인트 매칭 수: {len(joined_warnings):,}")
    print(f"횡단보도예고표시 포함 POINT 수: {result_df[output_col].sum():,}")

    return result_df
