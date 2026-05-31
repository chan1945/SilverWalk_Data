###################################################
# point_id, 위도, 경도 컬럼 추가 함수
# 기본 베이스 데이터
###################################################

def make_base_point_df(points_gdf):
    """POINT_ID별 기본 좌표 컬럼을 생성합니다."""
    point_coords_wgs84 = points_gdf[["POINT_ID", "geometry"]].to_crs(epsg=4326).copy()
    point_coords_wgs84["경도"] = point_coords_wgs84.geometry.x
    point_coords_wgs84["위도"] = point_coords_wgs84.geometry.y

    return point_coords_wgs84[["POINT_ID", "위도", "경도"]]

