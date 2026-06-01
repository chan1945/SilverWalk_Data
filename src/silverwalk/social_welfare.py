import geopandas as gpd
import pandas as pd

from silverwalk.config import (
    SOCIAL_WELFARE_ADDRESS_CSV,
    SOCIAL_WELFARE_COLUMN,
    SOCIAL_WELFARE_GEOCODED_CSV,
    SOCIAL_WELFARE_XLSX,
    TARGET_REGION_NAME,
)


FACILITY_ID_COL = "시설ID"
FACILITY_ADDRESS_COL = "기관소재지"


def load_elderly_welfare_facilities(facility_xlsx=SOCIAL_WELFARE_XLSX, include_inactive=False):
    """서울시 노인의료복지시설현황 엑셀에서 시설명과 주소 목록을 읽습니다."""
    if not facility_xlsx.exists():
        raise FileNotFoundError(f"노인의료복지시설 엑셀 파일을 찾지 못했습니다: {facility_xlsx}")

    rows = []
    for sheet_name in pd.ExcelFile(facility_xlsx).sheet_names:
        sheet_df = pd.read_excel(facility_xlsx, sheet_name=sheet_name, header=2)
        sheet_df = sheet_df.loc[pd.to_numeric(sheet_df["연번"], errors="coerce").notna()].copy()

        if not include_inactive and "휴업시설\n(미운영)" in sheet_df.columns:
            sheet_df = sheet_df.loc[sheet_df["휴업시설\n(미운영)"].isna()].copy()

        sheet_df = sheet_df.rename(
            columns={
                "관할\n자치구": "자치구",
                "기관소재지\n(새주소)": FACILITY_ADDRESS_COL,
            }
        )
        sheet_df["시설유형"] = sheet_name
        rows.append(
            sheet_df[
                [
                    "시설유형",
                    "자치구",
                    "장기요양기관기호",
                    "기관명칭",
                    "전화",
                    FACILITY_ADDRESS_COL,
                ]
            ]
        )

    facilities_df = pd.concat(rows, ignore_index=True)
    facilities_df[FACILITY_ADDRESS_COL] = facilities_df[FACILITY_ADDRESS_COL].astype(str).str.strip()
    facilities_df = facilities_df.loc[facilities_df[FACILITY_ADDRESS_COL].ne("")].copy()
    facilities_df[FACILITY_ID_COL] = facilities_df.index.astype(int)

    return facilities_df[
        [
            FACILITY_ID_COL,
            "시설유형",
            "자치구",
            "장기요양기관기호",
            "기관명칭",
            "전화",
            FACILITY_ADDRESS_COL,
        ]
    ]


def _load_geocoded_facility_points(
    facility_xlsx=SOCIAL_WELFARE_XLSX,
    geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV,
    address_csv=SOCIAL_WELFARE_ADDRESS_CSV,
):
    facilities_df = load_elderly_welfare_facilities(facility_xlsx=facility_xlsx)

    if not geocoded_csv.exists():
        address_csv.parent.mkdir(parents=True, exist_ok=True)
        facilities_df.to_csv(address_csv, index=False, encoding="utf-8-sig")
        raise FileNotFoundError(
            f"노인의료복지시설 좌표 파일이 없습니다: {geocoded_csv}\n"
            f"주소 목록을 생성했습니다: {address_csv}\n"
            "주소 목록에 경도, 위도 컬럼을 추가해 geocoded CSV로 저장한 뒤 다시 실행하십시오."
        )

    geocoded_df = pd.read_csv(geocoded_csv, encoding="utf-8-sig")
    required_cols = [FACILITY_ID_COL, "경도", "위도"]
    missing_cols = [col for col in required_cols if col not in geocoded_df.columns]
    if missing_cols:
        raise ValueError(f"노인의료복지시설 좌표 파일에 필요한 컬럼이 없습니다: {missing_cols}")

    geocoded_df["경도"] = pd.to_numeric(geocoded_df["경도"], errors="coerce")
    geocoded_df["위도"] = pd.to_numeric(geocoded_df["위도"], errors="coerce")
    geocoded_df = geocoded_df.dropna(subset=["경도", "위도"]).copy()

    facilities_df = facilities_df.merge(
        geocoded_df[[FACILITY_ID_COL, "경도", "위도"]],
        on=FACILITY_ID_COL,
        how="inner",
    )

    return gpd.GeoDataFrame(
        facilities_df,
        geometry=gpd.points_from_xy(facilities_df["경도"], facilities_df["위도"]),
        crs="EPSG:4326",
    )


def add_social_welfare_facility_counts(
    final_df,
    points_gdf,
    facility_xlsx=SOCIAL_WELFARE_XLSX,
    geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV,
    radius_m=300,
    output_col=SOCIAL_WELFARE_COLUMN,
):
    """각 POINT_ID의 300m 반경 안에 있는 노인의료복지시설 개수를 추가합니다."""
    facility_points_gdf = _load_geocoded_facility_points(
        facility_xlsx=facility_xlsx,
        geocoded_csv=geocoded_csv,
    ).to_crs(points_gdf.crs)

    welfare_buffers_gdf = points_gdf[["POINT_ID", "geometry"]].copy()
    welfare_buffers_gdf["geometry"] = welfare_buffers_gdf.geometry.buffer(radius_m)

    joined_facilities = gpd.sjoin(
        facility_points_gdf[[FACILITY_ID_COL, "geometry"]],
        welfare_buffers_gdf[["POINT_ID", "geometry"]],
        how="inner",
        predicate="within",
    )

    facility_summary = (
        joined_facilities.groupby("POINT_ID", as_index=False)[FACILITY_ID_COL]
        .nunique()
        .rename(columns={FACILITY_ID_COL: output_col})
    )

    result_df = final_df.merge(facility_summary, on="POINT_ID", how="left")
    result_df[output_col] = result_df[output_col].fillna(0).astype(int)

    print(f"{TARGET_REGION_NAME} 노인의료복지시설 좌표 수: {len(facility_points_gdf):,}")
    print(f"반경 {radius_m}m 노인의료복지시설-포인트 매칭 수: {len(joined_facilities):,}")

    return result_df

