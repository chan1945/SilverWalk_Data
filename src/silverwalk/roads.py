import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString

from silverwalk.config import INCLUDED_ROAD_CLASSES, JINJU_SIG_CD, ROAD_SHP_CANDIDATES

###################################################
# roads.py: 도로 shapefile을 읽고, 진주시 도로를 필터링하고, 도로 라인 위에 포인트를 생성하는 함수들을 정의합니다.
# 다른 모듈에서 이 함수들을 import하여 사용합니다.
###################################################

def resolve_existing_path(candidates, description):
    """후보 경로 중 실제 존재하는 첫 번째 경로를 반환합니다."""
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        raise FileNotFoundError(f"{description} 파일을 찾을 수 없습니다.")
    return path


def load_road_segments(road_shp_candidates=ROAD_SHP_CANDIDATES, encoding="cp949"):
    """도로명주소 도로구간 shapefile을 읽습니다."""
    road_shp = resolve_existing_path(road_shp_candidates, "TL_SPRD_MANAGE_48_202605.shp")
    roads = gpd.read_file(road_shp, encoding=encoding)
    return roads, road_shp


def filter_jinju_roads(
    roads,
    sig_cd=JINJU_SIG_CD,
    included_road_classes=INCLUDED_ROAD_CLASSES,
):
    """진주시 도로 중 분석 대상 도로 클래스만 필터링합니다."""
    jinju_all_roads = roads.loc[roads["SIG_CD"].astype(str).eq(sig_cd)].copy()
    jinju_all_roads["ROA_CLS_SE"] = jinju_all_roads["ROA_CLS_SE"].astype(str)

    jinju_roads = jinju_all_roads.loc[
        jinju_all_roads["ROA_CLS_SE"].isin(included_road_classes)
    ].copy()

    if jinju_roads.empty:
        classes = ", ".join(sorted(included_road_classes))
        raise ValueError(f"SIG_CD={sig_cd}에서 도로 클래스 {classes}에 해당하는 도로구간이 없습니다.")

    return jinju_all_roads, jinju_roads


def make_road_summary(jinju_all_roads, jinju_roads):
    """노트북 표시용 도로 요약 테이블을 생성합니다."""
    return pd.DataFrame(
        {
            "항목": ["시각화 대상 도로구간 수", "전체 진주시 도로구간 수", "총 연장(km)", "평균 도로폭(m)", "좌표계"],
            "값": [
                f"{len(jinju_roads):,}",
                f"{len(jinju_all_roads):,}",
                f"{jinju_roads['ROAD_LT'].sum() / 1000:,.1f}",
                f"{jinju_roads['ROAD_BT'].mean():,.1f}",
                str(jinju_roads.crs),
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


def create_road_points(jinju_roads, distance=25):
    """진주시 도로 라인 위에 POINT_ID가 있는 포인트 GeoDataFrame을 생성합니다."""
    point_rows = []

    for road_idx, row in jinju_roads.reset_index(drop=True).iterrows():
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

    return gpd.GeoDataFrame(point_rows, geometry="geometry", crs=jinju_roads.crs)


def create_point_buffers(points_gdf, buffer_distance_m=50):
    """각 도로 포인트 주변 버퍼 GeoDataFrame을 생성합니다."""
    point_buffers_gdf = points_gdf.copy()
    point_buffers_gdf["geometry"] = point_buffers_gdf.geometry.buffer(buffer_distance_m)
    return point_buffers_gdf

