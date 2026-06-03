import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_50M,
    PEDESTRIAN_SIGNAL_CSV,
    TARGET_REGION_NAME,
    TRAFFIC_SIGNAL_COLUMN,
)


PEDESTRIAN_SIGNAL_ID_COL = "보행자신호등ID"
PEDESTRIAN_SIGNAL_X_COL = "X좌표"
PEDESTRIAN_SIGNAL_Y_COL = "Y좌표"


def load_pedestrian_signals(pedestrian_signal_csv=PEDESTRIAN_SIGNAL_CSV):
    """보행자신호등 CSV를 EPSG:5186 좌표계의 point 데이터로 읽습니다."""
    if not pedestrian_signal_csv.exists():
        raise FileNotFoundError(f"보행자신호등 CSV를 찾지 못했습니다: {pedestrian_signal_csv}")

    signal_df = pd.read_csv(pedestrian_signal_csv, encoding="cp949")
    required_cols = [PEDESTRIAN_SIGNAL_X_COL, PEDESTRIAN_SIGNAL_Y_COL]
    missing_cols = [col for col in required_cols if col not in signal_df.columns]
    if missing_cols:
        raise ValueError(f"보행자신호등 데이터에 필요한 컬럼이 없습니다: {missing_cols}")

    signal_df[PEDESTRIAN_SIGNAL_X_COL] = pd.to_numeric(
        signal_df[PEDESTRIAN_SIGNAL_X_COL],
        errors="coerce",
    )
    signal_df[PEDESTRIAN_SIGNAL_Y_COL] = pd.to_numeric(
        signal_df[PEDESTRIAN_SIGNAL_Y_COL],
        errors="coerce",
    )
    signal_df = signal_df.dropna(subset=[PEDESTRIAN_SIGNAL_X_COL, PEDESTRIAN_SIGNAL_Y_COL]).copy()
    signal_df[PEDESTRIAN_SIGNAL_ID_COL] = signal_df.index.astype(int)

    return gpd.GeoDataFrame(
        signal_df,
        geometry=gpd.points_from_xy(
            signal_df[PEDESTRIAN_SIGNAL_X_COL],
            signal_df[PEDESTRIAN_SIGNAL_Y_COL],
        ),
        crs="EPSG:5186",
    )


def add_traffic_signal_presence(
    final_df,
    points_gdf,
    pedestrian_signal_csv=PEDESTRIAN_SIGNAL_CSV,
    radius_m=BUFFER_50M,
    output_col=TRAFFIC_SIGNAL_COLUMN,
):
    """각 POINT_ID의 반경 radius_m 안에 보행자신호등이 있으면 1, 없으면 0을 추가합니다."""
    signals_gdf = load_pedestrian_signals(
        pedestrian_signal_csv=pedestrian_signal_csv,
    ).to_crs(points_gdf.crs)

    signal_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    signal_buffers_gdf["geometry"] = signal_buffers_gdf.geometry.buffer(radius_m)

    joined_signals = gpd.sjoin(
        signals_gdf[[PEDESTRIAN_SIGNAL_ID_COL, "geometry"]],
        signal_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    signal_presence = (
        joined_signals[["POINT_ID"]]
        .drop_duplicates()
        .assign(**{output_col: 1})
    )

    result_df = final_df.merge(signal_presence, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 보행자신호등 point 수: {len(signals_gdf):,}")
    print(f"반경 {radius_m}m 보행자신호등-포인트 매칭 수: {len(joined_signals):,}")
    print(f"보행자신호등 포함 POINT 수: {result_df[output_col].sum():,}")

    return result_df
