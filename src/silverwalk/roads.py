import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString

from silverwalk.config import (
    BUFFER_50M,
    INCLUDED_ROAD_CLASSES,
    ROAD_SHP,
    TARGET_REGION_NAME,
    TARGET_SIG_CD_PREFIX,
)

###################################################
# roads.py: 도로 shapefile을 읽고, 대상 지역 도로를 필터링하고, 도로 라인 위에 포인트를 생성하는 함수들을 정의합니다.
# 다른 모듈에서 이 함수들을 import하여 사용합니다.
###################################################

def load_road_segments(road_shp=ROAD_SHP, encoding="cp949"):
    """도로명주소 도로구간 shapefile을 읽습니다."""
    if not road_shp.exists():
        raise FileNotFoundError(f"도로명주소 도로구간 shapefile을 찾을 수 없습니다: {road_shp}")
    roads = gpd.read_file(road_shp, encoding=encoding)
    return roads, road_shp


def filter_target_roads(
    roads,
    sig_cd_prefix=TARGET_SIG_CD_PREFIX,
    included_road_classes=INCLUDED_ROAD_CLASSES,
    target_region_name=TARGET_REGION_NAME,
):
    """대상 지역 도로 중 분석 대상 도로 클래스만 필터링합니다."""
    target_all_roads = roads.loc[roads["SIG_CD"].astype(str).str.startswith(sig_cd_prefix)].copy()
    target_all_roads["ROA_CLS_SE"] = target_all_roads["ROA_CLS_SE"].astype(str)

    target_roads = target_all_roads.loc[
        target_all_roads["ROA_CLS_SE"].isin(included_road_classes)
    ].copy()

    if target_roads.empty:
        classes = ", ".join(sorted(included_road_classes))
        raise ValueError(
            f"{target_region_name} SIG_CD prefix={sig_cd_prefix}에서 "
            f"도로 클래스 {classes}에 해당하는 도로구간이 없습니다."
        )

    return target_all_roads, target_roads


def make_road_summary(target_all_roads, target_roads, target_region_name=TARGET_REGION_NAME):
    """노트북 표시용 도로 요약 테이블을 생성합니다."""
    return pd.DataFrame(
        {
            "항목": [
                "시각화 대상 도로구간 수",
                f"전체 {target_region_name} 도로구간 수",
                "총 연장(km)",
                "평균 도로폭(m)",
                "좌표계",
            ],
            "값": [
                f"{len(target_roads):,}",
                f"{len(target_all_roads):,}",
                f"{target_roads['ROAD_LT'].sum() / 1000:,.1f}",
                f"{target_roads['ROAD_BT'].mean():,.1f}",
                str(target_roads.crs),
            ],
        }
    )


def create_points_along_line(geom, distance=25):
    """LineString 또는 MultiLineString 위에 일정 간격의 포인트를 생성합니다."""
    points = []

    if geom is None or geom.is_empty:
        return points

    if isinstance(geom, LineString):
        lines = [geom]
    elif isinstance(geom, MultiLineString):
        lines = list(geom.geoms)
    else:
        return points

    for line in lines:
        distances = list(range(0, int(line.length) + 1, distance))
        if not distances or distances[-1] < line.length:
            distances.append(line.length)

        points.extend(line.interpolate(d) for d in distances)

    return points


def create_road_points(target_roads, distance=25):
    """대상 지역 도로 라인 위에 POINT_ID가 있는 포인트 GeoDataFrame을 생성합니다."""
    point_rows = []

    for road_idx, row in target_roads.reset_index(drop=True).iterrows():
        road_points = create_points_along_line(row.geometry, distance=distance)
        for point_seq, point in enumerate(road_points):
            point_rows.append(
                {
                    "POINT_ID": len(point_rows),
                    "ROAD_IDX": road_idx,
                    "POINT_SEQ": point_seq,
                    "RN": row["RN"],
                    "RN_CD": row["RN_CD"],
                    "ROAD_LT": row["ROAD_LT"],
                    "ROAD_BT": row["ROAD_BT"],
                    "ROA_CLS_SE": row["ROA_CLS_SE"],
                    "geometry": point,
                }
            )

    return gpd.GeoDataFrame(point_rows, geometry="geometry", crs=target_roads.crs)


def create_point_buffers(points_gdf, buffer_distance_m=BUFFER_50M):
    """각 도로 포인트 주변 버퍼 GeoDataFrame을 생성합니다."""
    point_buffers_gdf = points_gdf.copy()
    point_buffers_gdf["geometry"] = point_buffers_gdf.geometry.buffer(buffer_distance_m)
    return point_buffers_gdf
