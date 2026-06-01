from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt

from silverwalk.config import (
    ELDERLY_POPULATION_COLUMN,
    DATA_DIR,
    POPULATION_GRID_CANDIDATES,
    TARGET_REGION_NAME,
)


ELDERLY_POPULATION_COL_CANDIDATES = [
    "고령인구",
    "고령인구수",
    "고령_인구",
    "65세이상",
    "65세 이상",
    "65세이상인구",
    "65세 이상 인구",
    "65세이상인구수",
    "65세 이상 인구수",
    "elderly_pop",
    "elderly_population",
    "pop_65_over",
    "pop_65plus",
    "age_65_over",
]

X_COL_CANDIDATES = ["x", "X", "xcoord", "X_COORD", "coord_x", "경도", "lon", "lng", "longitude"]
Y_COL_CANDIDATES = ["y", "Y", "ycoord", "Y_COORD", "coord_y", "위도", "lat", "latitude"]
POPULATION_FILE_SUFFIXES = {".shp", ".geojson", ".gpkg", ".csv"}
POPULATION_FILE_KEYWORDS = ["고령", "65", "인구", "population", "elderly"]


def _normalize_name(value):
    return str(value).lower().replace(" ", "").replace("_", "")


def _find_column(columns, candidates):
    normalized_columns = {_normalize_name(col): col for col in columns}
    for candidate in candidates:
        matched_col = normalized_columns.get(_normalize_name(candidate))
        if matched_col is not None:
            return matched_col
    return None


def _is_numeric_like(series):
    try:
        numeric_series = pd.to_numeric(series, errors="coerce")
    except (TypeError, ValueError):
        return False
    return numeric_series.notna().any()


def _resolve_population_path(candidates=POPULATION_GRID_CANDIDATES):
    path = next((candidate for candidate in candidates if Path(candidate).exists()), None)
    if path is not None:
        return path

    detected_paths = []
    for candidate in DATA_DIR.rglob("*"):
        if candidate.suffix.lower() not in POPULATION_FILE_SUFFIXES:
            continue
        name = candidate.name.lower()
        if any(keyword.lower() in name for keyword in POPULATION_FILE_KEYWORDS):
            detected_paths.append(candidate)

    if len(detected_paths) == 1:
        return detected_paths[0]

    if len(detected_paths) > 1:
        raise FileNotFoundError(
            "국토정보플랫폼 고령인구 격자 데이터 후보가 여러 개입니다. "
            "add_elderly_population_300m(..., population_path='파일경로')로 하나를 지정하십시오. "
            f"후보: {detected_paths}"
        )

    raise FileNotFoundError(
        "국토정보플랫폼 고령인구 격자 데이터를 찾지 못했습니다. "
        "Data/seoul_elderly_population_grid.shp 또는 "
        "Data/국토정보플랫폼_서울_고령인구_격자.shp 형태로 배치하거나 "
        "population_path를 직접 지정하십시오."
    )


def _infer_elderly_population_col(df, population_col=None):
    if population_col is not None:
        if population_col not in df.columns:
            raise ValueError(f"지정한 고령인구 컬럼이 데이터에 없습니다: {population_col}")
        return population_col

    matched_col = _find_column(df.columns, ELDERLY_POPULATION_COL_CANDIDATES)
    if matched_col is not None:
        return matched_col

    elderly_like_cols = [
        col
        for col in df.columns
        if ("고령" in str(col) or "65" in str(col))
        and _is_numeric_like(df[col])
    ]
    if len(elderly_like_cols) == 1:
        return elderly_like_cols[0]

    numeric_cols = [
        col
        for col in df.columns
        if _is_numeric_like(df[col])
    ]
    raise ValueError(
        "고령인구 컬럼을 자동으로 찾지 못했습니다. "
        "add_elderly_population_300m(..., population_col='실제컬럼명')으로 지정하십시오. "
        f"숫자형 후보 컬럼: {numeric_cols[:30]}"
    )


def _read_population_grid(population_path, population_col=None, source_crs="EPSG:5179"):
    population_path = Path(population_path)
    suffix = population_path.suffix.lower()

    if suffix in {".shp", ".geojson", ".gpkg"}:
        population_gdf = gpd.read_file(population_path)
        if population_gdf.crs is None:
            population_gdf = population_gdf.set_crs(source_crs)
    elif suffix == ".csv":
        population_df = pd.read_csv(population_path, encoding="utf-8")
        if "geometry" in population_df.columns:
            population_gdf = gpd.GeoDataFrame(
                population_df,
                geometry=population_df["geometry"].apply(wkt.loads),
                crs=source_crs,
            )
        else:
            x_col = _find_column(population_df.columns, X_COL_CANDIDATES)
            y_col = _find_column(population_df.columns, Y_COL_CANDIDATES)
            if x_col is None or y_col is None:
                raise ValueError(
                    "CSV 인구 데이터에서 geometry 또는 x/y 좌표 컬럼을 찾지 못했습니다. "
                    "geometry WKT 컬럼 또는 x/y 좌표 컬럼이 필요합니다."
                )

            population_df[x_col] = pd.to_numeric(population_df[x_col], errors="coerce")
            population_df[y_col] = pd.to_numeric(population_df[y_col], errors="coerce")
            population_df = population_df.dropna(subset=[x_col, y_col]).copy()

            # 경도/위도 컬럼이면 EPSG:4326, 그 외 국토정보플랫폼 격자 좌표는 기본 EPSG:5179로 봅니다.
            csv_crs = "EPSG:4326" if x_col in {"경도", "lon", "lng", "longitude"} else source_crs
            population_gdf = gpd.GeoDataFrame(
                population_df,
                geometry=gpd.points_from_xy(population_df[x_col], population_df[y_col]),
                crs=csv_crs,
            )
    else:
        raise ValueError(f"지원하지 않는 인구 데이터 형식입니다: {population_path}")

    elderly_pop_col = _infer_elderly_population_col(population_gdf, population_col=population_col)
    population_gdf[elderly_pop_col] = pd.to_numeric(population_gdf[elderly_pop_col], errors="coerce").fillna(0)

    population_gdf = population_gdf.loc[
        population_gdf.geometry.notna() & ~population_gdf.geometry.is_empty
    ].copy()
    return population_gdf, elderly_pop_col


def add_elderly_population_300m(
    final_df,
    points_gdf,
    population_path=None,
    population_col=None,
    radius_m=300,
    source_crs="EPSG:5179",
    output_col=ELDERLY_POPULATION_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 65세 이상 거주인구 합계를 추가합니다.

    국토정보플랫폼의 격자 인구 데이터가 polygon이면 격자 중심점 기준으로 집계합니다.
    CSV는 geometry WKT 또는 x/y 좌표 컬럼이 있어야 합니다.
    """
    if population_path is None:
        population_path = _resolve_population_path()

    population_gdf, elderly_pop_col = _read_population_grid(
        population_path=population_path,
        population_col=population_col,
        source_crs=source_crs,
    )
    population_gdf = population_gdf.to_crs(points_gdf.crs)

    population_points_gdf = population_gdf[[elderly_pop_col, "geometry"]].copy()
    non_point_mask = ~population_points_gdf.geometry.geom_type.isin(["Point", "MultiPoint"])
    if non_point_mask.any():
        population_points_gdf.loc[non_point_mask, "geometry"] = population_points_gdf.loc[
            non_point_mask, "geometry"
        ].representative_point()

    population_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    population_buffers_gdf["geometry"] = population_buffers_gdf.geometry.buffer(radius_m)

    joined_population = gpd.sjoin(
        population_points_gdf[[elderly_pop_col, "geometry"]],
        population_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    population_summary = (
        joined_population.groupby("POINT_ID", as_index=False)[elderly_pop_col]
        .sum()
        .rename(columns={elderly_pop_col: output_col})
    )

    result_df = final_df.merge(population_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).round().astype(int)

    print(f"{TARGET_REGION_NAME} 고령인구 격자 데이터 수: {len(population_points_gdf):,}")
    print(f"반경 {radius_m}m 고령인구 격자-포인트 매칭 수: {len(joined_population):,}")
    print(f"고령인구 원본 컬럼: {elderly_pop_col}")

    return result_df
