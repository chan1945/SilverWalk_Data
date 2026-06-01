from pathlib import Path

import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    ELDERLY_POPULATION_COLUMN,
    POPULATION_GRID_DIR,
    TARGET_REGION_NAME,
)


###################################################
# population.py: 국토통계 고령인구수 250m 격자 데이터를 읽고, 각 도로 구간 포인트에 반경 300m 내의 고령인구수를 합산하여 추가하는 기능을 제공합니다.
###################################################


POPULATION_VALUE_COLUMN = "val"


def _read_population_grid(population_dir=POPULATION_GRID_DIR, source_crs="EPSG:5179"):
    """Data/국토통계_고령인구수 하위의 구별 250m 격자 shapefile을 모두 읽습니다."""
    population_dir = Path(population_dir)
    if not population_dir.exists():
        raise FileNotFoundError(f"국토통계 고령인구수 데이터 경로가 없습니다: {population_dir}")

    file_paths = sorted(population_dir.rglob("*.shp"))
    if not file_paths:
        raise FileNotFoundError(f"국토통계 고령인구수 shapefile을 찾지 못했습니다: {population_dir}")

    gdfs = []
    for file_path in file_paths:
        gdf = gpd.read_file(file_path, encoding="utf-8")
        if gdf.crs is None:
            gdf = gdf.set_crs(source_crs)
        if POPULATION_VALUE_COLUMN not in gdf.columns:
            raise ValueError(f"{file_path}에 {POPULATION_VALUE_COLUMN} 컬럼이 없습니다.")

        gdf["source_file"] = str(file_path)
        gdfs.append(gdf)

    base_crs = gdfs[0].crs or source_crs
    aligned_gdfs = [
        gdf.set_crs(base_crs) if gdf.crs is None else gdf.to_crs(base_crs)
        for gdf in gdfs
    ]
    population_gdf = pd.concat(aligned_gdfs, ignore_index=True)
    population_gdf = gpd.GeoDataFrame(population_gdf, geometry="geometry", crs=base_crs)
    population_gdf[POPULATION_VALUE_COLUMN] = (
        pd.to_numeric(population_gdf[POPULATION_VALUE_COLUMN], errors="coerce")
        .fillna(0)
    )

    population_gdf = population_gdf.loc[
        population_gdf.geometry.notna() & ~population_gdf.geometry.is_empty
    ].copy()
    return population_gdf


def add_elderly_population_300m(
    final_df,
    points_gdf,
    population_dir=POPULATION_GRID_DIR,
    radius_m=300,
    output_col=ELDERLY_POPULATION_COLUMN,
):
    """각 POINT_ID의 300m 반경 안에 있는 국토통계 250m 격자 고령인구수를 합산합니다."""
    population_gdf = _read_population_grid(population_dir=population_dir)
    population_gdf = population_gdf.to_crs(points_gdf.crs)

    population_points_gdf = population_gdf[[POPULATION_VALUE_COLUMN, "geometry"]].copy()
    population_points_gdf["geometry"] = population_points_gdf.geometry.representative_point()

    population_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    population_buffers_gdf["geometry"] = population_buffers_gdf.geometry.buffer(radius_m)

    joined_population = gpd.sjoin(
        population_points_gdf[[POPULATION_VALUE_COLUMN, "geometry"]],
        population_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    population_summary = (
        joined_population.groupby("POINT_ID", as_index=False)[POPULATION_VALUE_COLUMN]
        .sum()
        .rename(columns={POPULATION_VALUE_COLUMN: output_col})
    )

    result_df = final_df.merge(population_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).round().astype(int)

    print(f"{TARGET_REGION_NAME} 고령인구 250m 격자 수: {len(population_points_gdf):,}")
    print(f"반경 {radius_m}m 고령인구 격자-포인트 매칭 수: {len(joined_population):,}")
    print(f"고령인구수 원본 컬럼: {POPULATION_VALUE_COLUMN}")

    return result_df

