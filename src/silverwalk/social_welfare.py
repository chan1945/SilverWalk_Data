import os
import re
import time

import geopandas as gpd
import pandas as pd
import requests

from silverwalk.config import (
    SOCIAL_WELFARE_ADDRESS_CSV,
    SOCIAL_WELFARE_COLUMN,
    SOCIAL_WELFARE_GEOCODED_CSV,
    SOCIAL_WELFARE_XLSX,
    TARGET_REGION_NAME,
    VWORLD_API_KEY_ENV,
)


FACILITY_ID_COL = "시설ID"
FACILITY_ADDRESS_COL = "기관소재지"
VWORLD_GEOCODE_URL = "https://api.vworld.kr/req/address"
VWORLD_KEY_ERROR_CODES = {"INVALID_KEY", "INCORRECT_KEY", "UNAVAILABLE_KEY", "OVER_REQUEST_LIMIT"}


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


def _get_vworld_api_key(vworld_api_key=None):
    api_key = vworld_api_key or os.environ.get(VWORLD_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            "VWorld 지오코딩 인증키가 필요합니다. "
            f"환경변수 {VWORLD_API_KEY_ENV}에 인증키를 설정하거나 "
            "add_social_welfare_facility_counts(..., vworld_api_key='인증키') 형태로 전달하십시오."
        )
    return api_key


def _normalize_address_candidates(address):
    address = str(address).strip()
    if not address or address.lower() == "nan":
        return []

    candidates = [address]
    cleaned = re.sub(r"\([^)]*\)", " ", address)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.replace("서울시 ", "서울특별시 ")
    cleaned = re.sub(r"^서울\s+", "서울특별시 ", cleaned)

    if "," in cleaned:
        candidates.append(cleaned.split(",", maxsplit=1)[0].strip())
    candidates.append(cleaned)

    unique_candidates = []
    for candidate in candidates:
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return unique_candidates


def _request_vworld_geocode(session, address, api_key, address_type="road", timeout=10):
    params = {
        "service": "address",
        "request": "getcoord",
        "version": "2.0",
        "crs": "EPSG:4326",
        "address": address,
        "format": "json",
        "type": address_type,
        "key": api_key,
    }
    response = session.get(VWORLD_GEOCODE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def geocode_address_vworld(address, api_key, session=None, timeout=10):
    """VWorld Geocoder API로 주소 1건의 EPSG:4326 경도/위도를 조회합니다."""
    session = session or requests.Session()

    last_status = None
    last_error = None
    for candidate in _normalize_address_candidates(address):
        for address_type in ["road", "parcel"]:
            response_json = _request_vworld_geocode(
                session=session,
                address=candidate,
                api_key=api_key,
                address_type=address_type,
                timeout=timeout,
            )
            response_body = response_json.get("response", {})
            status = response_body.get("status")
            last_status = status

            if status == "OK":
                point = response_body.get("result", {}).get("point", {})
                return {
                    "경도": float(point["x"]),
                    "위도": float(point["y"]),
                    "지오코딩주소": candidate,
                    "지오코딩유형": address_type,
                    "지오코딩상태": status,
                }

            error = response_body.get("error", {})
            error_code = error.get("code")
            error_text = error.get("text")
            if error_code in VWORLD_KEY_ERROR_CODES:
                raise RuntimeError(f"VWorld API 오류: {error_code} - {error_text}")

            last_error = error_text or status

    return {
        "경도": pd.NA,
        "위도": pd.NA,
        "지오코딩주소": pd.NA,
        "지오코딩유형": pd.NA,
        "지오코딩상태": last_error or last_status or "NOT_FOUND",
    }


def geocode_elderly_welfare_facilities_vworld(
    facility_xlsx=SOCIAL_WELFARE_XLSX,
    vworld_api_key=None,
    sleep_seconds=0.05,
    timeout=10,
):
    """서울시 노인의료복지시설 주소를 VWorld Geocoder API로 실시간 좌표 변환합니다."""
    facilities_df = load_elderly_welfare_facilities(facility_xlsx=facility_xlsx)
    api_key = _get_vworld_api_key(vworld_api_key)
    session = requests.Session()

    geocoded_rows = []
    for idx, row in facilities_df.iterrows():
        geocoded = geocode_address_vworld(
            address=row[FACILITY_ADDRESS_COL],
            api_key=api_key,
            session=session,
            timeout=timeout,
        )
        geocoded_rows.append({**row.to_dict(), **geocoded})

        if (idx + 1) % 50 == 0:
            print(f"VWorld 지오코딩 진행: {idx + 1:,}/{len(facilities_df):,}")
        if sleep_seconds:
            time.sleep(sleep_seconds)

    geocoded_df = pd.DataFrame(geocoded_rows)
    geocoded_df["경도"] = pd.to_numeric(geocoded_df["경도"], errors="coerce")
    geocoded_df["위도"] = pd.to_numeric(geocoded_df["위도"], errors="coerce")
    return geocoded_df


def _load_geocoded_facility_csv(geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV):
    geocoded_df = pd.read_csv(geocoded_csv, encoding="utf-8-sig")
    required_cols = [FACILITY_ID_COL, "경도", "위도"]
    missing_cols = [col for col in required_cols if col not in geocoded_df.columns]
    if missing_cols:
        raise ValueError(f"노인의료복지시설 좌표 파일에 필요한 컬럼이 없습니다: {missing_cols}")

    geocoded_df["경도"] = pd.to_numeric(geocoded_df["경도"], errors="coerce")
    geocoded_df["위도"] = pd.to_numeric(geocoded_df["위도"], errors="coerce")
    return geocoded_df


def _make_facility_points_gdf(geocoded_df, address_csv=SOCIAL_WELFARE_ADDRESS_CSV):
    failed_df = geocoded_df.loc[geocoded_df[["경도", "위도"]].isna().any(axis=1)].copy()
    if not failed_df.empty:
        address_csv.parent.mkdir(parents=True, exist_ok=True)
        failed_df.to_csv(address_csv, index=False, encoding="utf-8-sig")
        print(f"좌표 변환 실패 시설 수: {len(failed_df):,}")
        print(f"좌표 변환 실패 목록 저장: {address_csv}")

    geocoded_df = geocoded_df.dropna(subset=["경도", "위도"]).copy()

    return gpd.GeoDataFrame(
        geocoded_df,
        geometry=gpd.points_from_xy(geocoded_df["경도"], geocoded_df["위도"]),
        crs="EPSG:4326",
    )


def add_social_welfare_facility_counts(
    final_df,
    points_gdf,
    facility_xlsx=SOCIAL_WELFARE_XLSX,
    geocoded_csv=SOCIAL_WELFARE_GEOCODED_CSV,
    radius_m=300,
    output_col=SOCIAL_WELFARE_COLUMN,
    vworld_api_key=None,
    use_geocoded_csv=False,
    sleep_seconds=0.05,
):
    """각 POINT_ID의 300m 반경 안에 있는 노인의료복지시설 개수를 추가합니다.

    기본값은 VWorld Geocoder API를 실시간 호출해 주소를 좌표로 변환합니다.
    이미 좌표가 있는 CSV를 직접 사용할 때만 use_geocoded_csv=True로 실행합니다.
    """
    if use_geocoded_csv:
        geocoded_df = _load_geocoded_facility_csv(geocoded_csv=geocoded_csv)
    else:
        geocoded_df = geocode_elderly_welfare_facilities_vworld(
            facility_xlsx=facility_xlsx,
            vworld_api_key=vworld_api_key,
            sleep_seconds=sleep_seconds,
        )

    facility_points_gdf = _make_facility_points_gdf(geocoded_df).to_crs(points_gdf.crs)

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
