import geopandas as gpd

from silverwalk.config import (
    TARGET_REGION_NAME,
    TRADITIONAL_MARKET_COLUMN,
    TRADITIONAL_MARKET_SHP,
)


MARKET_ID_COL = "TRDAR_CD"
MARKET_TYPE_COL = "TRDAR_SE_1"


def load_traditional_markets(market_shp=TRADITIONAL_MARKET_SHP):
    """전통시장 polygon 데이터를 읽습니다."""
    if not market_shp.exists():
        raise FileNotFoundError(f"전통시장 shapefile을 찾지 못했습니다: {market_shp}")

    markets_gdf = gpd.read_file(market_shp, encoding="utf-8")
    markets_gdf = markets_gdf.loc[
        markets_gdf.geometry.notna() & ~markets_gdf.geometry.is_empty
    ].copy()

    if MARKET_TYPE_COL in markets_gdf.columns:
        markets_gdf = markets_gdf.loc[markets_gdf[MARKET_TYPE_COL].eq("전통시장")].copy()

    if MARKET_ID_COL not in markets_gdf.columns:
        markets_gdf[MARKET_ID_COL] = markets_gdf.index.astype(str)

    return markets_gdf


def add_traditional_market_presence(
    final_df,
    points_gdf,
    market_shp=TRADITIONAL_MARKET_SHP,
    radius_m=50,
    output_col=TRADITIONAL_MARKET_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 전통시장이 있으면 1, 없으면 0을 추가합니다."""
    markets_gdf = load_traditional_markets(market_shp=market_shp).to_crs(points_gdf.crs)

    market_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    market_buffers_gdf["geometry"] = market_buffers_gdf.geometry.buffer(radius_m)

    joined_markets = gpd.sjoin(
        market_buffers_gdf[["POINT_ID", "geometry"]],
        markets_gdf[[MARKET_ID_COL, "geometry"]],
        how="inner",
        predicate="intersects",
    )

    market_presence = (
        joined_markets[["POINT_ID"]]
        .drop_duplicates()
        .assign(**{output_col: 1})
    )

    result_df = final_df.merge(market_presence, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 전통시장 polygon 수: {len(markets_gdf):,}")
    print(f"반경 {radius_m}m 전통시장-포인트 매칭 수: {len(joined_markets):,}")
    print(f"전통시장 포함 POINT 수: {result_df[output_col].sum():,}")

    return result_df
