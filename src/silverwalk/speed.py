import geopandas as gpd
import pandas as pd

###################################################
# 제한속도 컬럼 추가 함수
###################################################

def add_speed_limit(final_df, points_gdf, nodelink_shp):
    """ITS 표준노드링크 최근접 링크의 MAX_SPD를 제한속도 컬럼으로 추가합니다."""
    # 전국 링크 전체를 최근접 결합하면 무거우므로, 먼저 진주시 포인트 범위 주변 bbox로 링크를 잘라 읽습니다.
    link_sample_crs = gpd.read_file(nodelink_shp, rows=1, encoding="cp949").crs
    point_bounds_links_crs = gpd.GeoSeries(
        [points_gdf.union_all().envelope],
        crs=points_gdf.crs,
    ).to_crs(link_sample_crs).total_bounds

    minx, miny, maxx, maxy = point_bounds_links_crs
    bbox_buffer_m = 1000
    link_bbox = (
        minx - bbox_buffer_m,
        miny - bbox_buffer_m,
        maxx + bbox_buffer_m,
        maxy + bbox_buffer_m,
    )

    links_gdf = gpd.read_file(
        nodelink_shp,
        bbox=link_bbox,
        columns=["LINK_ID", "ROAD_NAME", "MAX_SPD", "geometry"],
        encoding="cp949",
    )
    links_gdf = links_gdf.dropna(subset=["MAX_SPD", "geometry"]).copy()
    links_gdf["MAX_SPD"] = pd.to_numeric(links_gdf["MAX_SPD"], errors="coerce")
    links_gdf = links_gdf.dropna(subset=["MAX_SPD"])
    links_gdf = links_gdf.to_crs(points_gdf.crs)

    if links_gdf.empty:
        raise ValueError("진주시 범위 주변에서 ITS 표준노드링크를 찾지 못했습니다.")

    point_speed_df = gpd.sjoin_nearest(
        points_gdf[["POINT_ID", "geometry"]],
        links_gdf[["LINK_ID", "ROAD_NAME", "MAX_SPD", "geometry"]],
        how="left",
        distance_col="link_distance_m",
    )
    point_speed_df = pd.DataFrame(point_speed_df.drop(columns="geometry"))

    # sjoin_nearest는 동거리 최근접 링크가 여러 개이면 POINT_ID가 중복될 수 있습니다.
    # 최종 학습/분석 데이터는 포인트당 1행이어야 하므로 거리, LINK_ID 기준으로 하나만 남깁니다.
    point_speed_df = (
        point_speed_df.sort_values(["POINT_ID", "link_distance_m", "LINK_ID"])
        .drop_duplicates(subset=["POINT_ID"], keep="first")
    )
    point_speed_df = point_speed_df.rename(columns={"MAX_SPD": "제한속도"})
    point_speed_df["제한속도"] = point_speed_df["제한속도"].round().astype("Int64")

    print(f"제한속도 결합 대상 링크 수: {len(links_gdf):,}")

    return final_df.merge(point_speed_df[["POINT_ID", "제한속도"]], on="POINT_ID", how="left")

