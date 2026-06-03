import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    CCTV_COLUMN,
    CCTV_CSV,
    STREETLIGHT_COLUMN,
    STREETLIGHT_CSV,
    TARGET_REGION_NAME,
)

LAT_COL = "위도"
LON_COL = "경도"
STREETLIGHT_ID_COL = "관리번호"
CCTV_ADDRESS_COL = "고정형CCTV지번주소"
CCTV_LOCATION_COL = "단속지점명"


def _load_point_csv(csv_path, id_col, dataset_name, encoding="cp949"):
    if not csv_path.exists():
        raise FileNotFoundError(f"{dataset_name} CSV를 찾지 못했습니다: {csv_path}")

    df = pd.read_csv(csv_path, encoding=encoding)
    required_cols = [id_col, LAT_COL, LON_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"{dataset_name} CSV에 필요한 컬럼이 없습니다: {missing_cols}")

    before_count = len(df)
    df[LAT_COL] = pd.to_numeric(df[LAT_COL], errors="coerce")
    df[LON_COL] = pd.to_numeric(df[LON_COL], errors="coerce")

    swapped_mask = df[LAT_COL].between(126, 128) & df[LON_COL].between(37, 38)
    if swapped_mask.any():
        df.loc[swapped_mask, [LAT_COL, LON_COL]] = df.loc[swapped_mask, [LON_COL, LAT_COL]].to_numpy()

    valid_mask = df[LAT_COL].between(37, 38) & df[LON_COL].between(126, 128)
    df = df.loc[valid_mask].copy()
    df = df.dropna(subset=[id_col, LAT_COL, LON_COL]).copy()

    print(f"{TARGET_REGION_NAME} {dataset_name} 전체 행 수: {before_count:,}")
    print(f"좌표 뒤집힘 보정 행 수: {int(swapped_mask.sum()):,}")
    print(f"좌표 이상/결측 제외 행 수: {before_count - len(df):,}")

    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[LON_COL], df[LAT_COL]),
        crs="EPSG:4326",
    )


def _add_point_asset_counts(final_df, points_gdf, assets_gdf, id_col, output_col, radius_m):
    assets_gdf = assets_gdf.to_crs(points_gdf.crs)

    buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    buffers_gdf["geometry"] = buffers_gdf.geometry.buffer(radius_m)

    joined_assets = gpd.sjoin(
        assets_gdf[[id_col, "geometry"]],
        buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    asset_summary = (
        joined_assets.groupby("POINT_ID", as_index=False)[id_col]
        .nunique()
        .rename(columns={id_col: output_col})
    )

    result_df = final_df.drop(columns=[output_col], errors="ignore")
    result_df = result_df.merge(asset_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"반경 {radius_m}m {output_col}-포인트 매칭 수: {len(joined_assets):,}")

    return result_df


def add_streetlight_counts(
    final_df,
    points_gdf,
    streetlight_csv=STREETLIGHT_CSV,
    radius_m=BUFFER_300M,
    output_col=STREETLIGHT_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 가로등 수를 추가합니다."""
    streetlights_gdf = _load_point_csv(
        csv_path=streetlight_csv,
        id_col=STREETLIGHT_ID_COL,
        dataset_name="가로등",
    )

    return _add_point_asset_counts(
        final_df=final_df,
        points_gdf=points_gdf,
        assets_gdf=streetlights_gdf,
        id_col=STREETLIGHT_ID_COL,
        output_col=output_col,
        radius_m=radius_m,
    )


def add_cctv_counts(
    final_df,
    points_gdf,
    cctv_csv=CCTV_CSV,
    radius_m=BUFFER_300M,
    output_col=CCTV_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 있는 CCTV 수를 추가합니다."""
    cctv_gdf = _load_cctv_points(cctv_csv=cctv_csv)

    return _add_point_asset_counts(
        final_df=final_df,
        points_gdf=points_gdf,
        assets_gdf=cctv_gdf,
        id_col="CCTV_ID",
        output_col=output_col,
        radius_m=radius_m,
    )


def _load_cctv_points(cctv_csv=CCTV_CSV):
    cctv_gdf = _load_point_csv(
        csv_path=cctv_csv,
        id_col=CCTV_ADDRESS_COL,
        dataset_name="CCTV",
    )
    cctv_gdf = cctv_gdf.reset_index(drop=True)
    cctv_gdf["CCTV_ID"] = (
        cctv_gdf[CCTV_ADDRESS_COL].astype(str).str.strip()
        + "_"
        + cctv_gdf.get(CCTV_LOCATION_COL, pd.Series("", index=cctv_gdf.index)).astype(str).str.strip()
        + "_"
        + cctv_gdf.index.astype(str)
    )
    return cctv_gdf
