import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    BUFFER_300M,
    BUSINESS_CATEGORY_COLUMNS,
    TARGET_BUSINESS_SIDO_NAME,
    TARGET_REGION_NAME,
)

###################################################
# 상가 수 컬럼 추가 함수
# 각 POINT_ID의 반경 300m 안에 있는 대상 지역 상가 수를 업종별 컬럼으로 추가합니다.
###################################################

def add_business_category_counts(final_df, points_gdf, business_csv, radius_m=BUFFER_300M):
    """각 POINT_ID의 반경 radius_m 안에 있는 대상 지역 상가 수를 업종별 컬럼으로 추가합니다."""
    required_cols = [
        "상가업소번호",
        "시도명",
        "시군구명",
        "상권업종대분류명",
        "상권업종중분류명",
        "경도",
        "위도",
    ]
    business_df = pd.read_csv(business_csv, usecols=required_cols, encoding="utf-8")

    missing_cols = [col for col in required_cols if col not in business_df.columns]
    if missing_cols:
        raise ValueError(f"상가 데이터에 필요한 컬럼이 없습니다: {missing_cols}")

    business_df = business_df.loc[business_df["시도명"].eq(TARGET_BUSINESS_SIDO_NAME)].copy()
    business_df["경도"] = pd.to_numeric(business_df["경도"], errors="coerce")
    business_df["위도"] = pd.to_numeric(business_df["위도"], errors="coerce")
    business_df = business_df.dropna(subset=["경도", "위도"]).copy()

    for col in ["상권업종대분류명", "상권업종중분류명"]:
        business_df[col] = business_df[col].astype(str).str.strip()

    business_df["업종_중분류"] = business_df["상권업종대분류명"] + "_" + business_df["상권업종중분류명"]

    business_points_gdf = gpd.GeoDataFrame(
        business_df,
        geometry=gpd.points_from_xy(business_df["경도"], business_df["위도"]),
        crs="EPSG:4326",
    ).to_crs(points_gdf.crs)

    business_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    business_buffers_gdf["geometry"] = business_buffers_gdf.geometry.buffer(radius_m)

    # 상가 좌표가 300m 버퍼 안에 들어오면 해당 POINT_ID의 업종별 상가 수로 집계합니다.
    joined_business = gpd.sjoin(
        business_points_gdf[["상권업종대분류명", "업종_중분류", "geometry"]],
        business_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    major_counts = pd.crosstab(joined_business["POINT_ID"], joined_business["상권업종대분류명"])
    middle_counts = pd.crosstab(joined_business["POINT_ID"], joined_business["업종_중분류"])
    business_counts = pd.concat([major_counts, middle_counts], axis=1)
    business_counts = business_counts.reindex(columns=BUSINESS_CATEGORY_COLUMNS, fill_value=0)
    business_counts.index.name = "POINT_ID"
    business_counts = business_counts.reset_index()

    result_df = final_df.merge(business_counts, on="POINT_ID", how="left")
    result_df[BUSINESS_CATEGORY_COLUMNS] = result_df[BUSINESS_CATEGORY_COLUMNS].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 상가 데이터 수: {len(business_points_gdf):,}")
    print(f"반경 {radius_m}m 상가-포인트 매칭 수: {len(joined_business):,}")

    return result_df
