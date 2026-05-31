import geopandas as gpd
import pandas as pd


###################################################
# 위험도 컬럼 추가 함수
# 위험도 = 10 * 사고건수 * (사망자수 + 0.1168 * 중상자수 + 0.0068 * 경상자수)
###################################################

def add_accident_risk(final_df, points_gdf, point_buffers_gdf, accident_csv):
    """50m 버퍼 내 고령보행자 사고를 집계해 위험도 컬럼을 추가합니다."""
    accidents_df = pd.read_csv(accident_csv, encoding="utf-8-sig")

    required_cols = ["x_crdnt", "y_crdnt", "dprs_cnt", "sep_cnt", "slp_cnt"]
    missing_cols = [col for col in required_cols if col not in accidents_df.columns]
    if missing_cols:
        raise ValueError(f"사고 데이터에 필요한 컬럼이 없습니다: {missing_cols}")

    for col in required_cols:
        accidents_df[col] = pd.to_numeric(accidents_df[col], errors="coerce")

    accidents_df = accidents_df.dropna(subset=["x_crdnt", "y_crdnt"]).copy()

    accident_points_gdf = gpd.GeoDataFrame(
        accidents_df,
        geometry=gpd.points_from_xy(accidents_df["x_crdnt"], accidents_df["y_crdnt"]),
        crs=points_gdf.crs,
    )

    if accident_points_gdf.crs != point_buffers_gdf.crs:
        accident_points_gdf = accident_points_gdf.to_crs(point_buffers_gdf.crs)

    # 한 사고가 여러 POINT_ID의 50m 버퍼에 들어가면 각 POINT_ID에 각각 집계됩니다.
    joined_accidents = gpd.sjoin(
        accident_points_gdf[["dprs_cnt", "sep_cnt", "slp_cnt", "geometry"]],
        point_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    accident_summary = (
        joined_accidents.groupby("POINT_ID", as_index=False)
        .agg(
            사고건수=("POINT_ID", "size"),
            사망자수=("dprs_cnt", "sum"),
            중상자수=("sep_cnt", "sum"),
            경상자수=("slp_cnt", "sum"),
        )
    )

    result_df = final_df.merge(accident_summary, on="POINT_ID", how="left")
    count_cols = ["사고건수", "사망자수", "중상자수", "경상자수"]
    result_df[count_cols] = result_df[count_cols].fillna(0).astype(int)
    result_df["위험도"] = (
        10
        * result_df["사고건수"]
        * (
            result_df["사망자수"]
            + 0.1168 * result_df["중상자수"]
            + 0.0068 * result_df["경상자수"]
        )
    )

    print(f"사고 데이터 수: {len(accident_points_gdf):,}")
    print(f"버퍼 안에 포함된 사고-포인트 매칭 수: {len(joined_accidents):,}")

    return result_df.drop(columns=count_cols)

