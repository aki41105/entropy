def main():
    import geopandas as gpd
    from geopy.distance import geodesic
    import osmnx as ox
    import networkx as nx
    import folium
    from shapely.geometry import Point
    import pandas as pd
    from folium.features import CustomIcon

    # ダウンロード・解凍済みの S H P ファイルを指定(洪水浸水想定区域データ)
    flood_gdf = gpd.read_file("data/flood/A31-12_17.shp")  #洪水浸水想定区域データ
    # WGS84 緯度経度 (EPSG:4326) に変換

    hazard_gdf = flood_gdf.to_crs(epsg=4326)
    # import ipdb ;ipdb.set_trace()

    # 避難所データの読み込み（UTF-8-SIG で正しく読み込む）
    file_path = "data/shelter.csv"  # 適宜ファイルパスを変更
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    # 現在地の設定
    print("現在地の設定")
    current_location = [36.599901, 136.677889]

    # 緯度・経度が存在する避難所から最も近いものを選定
    valid_shelters = df.dropna(subset=["緯度", "経度"])
    valid_shelters["距離(km)"] = valid_shelters.apply(
        lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
    )
    nearest = valid_shelters.loc[valid_shelters["距離(km)"].idxmin()]
    nearest_location = (nearest["緯度"], nearest["経度"])

    # 道路グラフ取得
    G = ox.graph_from_point(current_location, dist=2000, network_type='walk')
    nodes = [(n, Point(d['x'], d['y'])) for n, d in G.nodes(data=True)]
    node_gdf = gpd.GeoDataFrame(nodes, columns=["node", "geometry"], crs="EPSG:4326")


    # ノードと洪水ポリゴンの空間結合（交差するノードを特定）
    hazard_nodes = gpd.sjoin(node_gdf, hazard_gdf, how='inner', predicate='intersects')

    # 危険なノードIDのリストを作成
    hazard_node_ids = set(hazard_nodes["node"])


    # 安全なグラフを作成
    G_safe = G.copy()
    G_safe.remove_nodes_from(hazard_node_ids)

    # 最寄りノードを取得（再確認）
    orig_node = ox.distance.nearest_nodes(G_safe, X=current_location[1], Y=current_location[0])
    dest_node = ox.distance.nearest_nodes(G_safe, X=nearest_location[1], Y=nearest_location[0])

    # 安全経路を探索（A*アルゴリズム）
    safe_route = nx.astar_path(G_safe, orig_node, dest_node, weight='length')

    # ルート座標を取得
    route_coords = [(G_safe.nodes[n]['y'], G_safe.nodes[n]['x']) for n in safe_route]

    # 地図に描画
    fmap = folium.Map(location=current_location, zoom_start=14)
    icon_start = CustomIcon(
    icon_image = 'map_utils/start.png'
    ,icon_size = (55, 65)
    ,icon_anchor = (30, 30)
    ,popup_anchor = (3, 3)
    )
    icon_goal = CustomIcon(
<<<<<<< HEAD
    icon_image = 'map_utils/goal.png'
    ,icon_size = (20, 30)
=======
    icon_image = './goal.png'
    ,icon_size = (55, 65)
>>>>>>> 9a9032e1f9fd7d3924cb46a5b158dd4130af7cd7
    ,icon_anchor = (30, 30)
    ,popup_anchor = (3, 3)
    )
    folium.Marker(location=current_location, popup="現在地", icon=icon_start).add_to(fmap)
    folium.Marker(location=nearest_location, popup="避難所", icon=icon_goal).add_to(fmap)
    folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(fmap)

    # foliumに渡すためにGeoJSON形式に変換
    geojson_data = hazard_gdf.to_json()

    # 洪水ポリゴンを地図に追加
    folium.GeoJson(
        data=geojson_data,
        name="洪水浸水想定区域（ベクター）",
        style_function=lambda feature: {
            'fillColor': 'blue',
            'color': 'blue',
            'weight': 1,
            'fillOpacity': 0.4,
        }
    ).add_to(fmap)

    import os

    # 保存先の絶対パスを指定（static/maps/ に保存）
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'maps'))
    os.makedirs(output_dir, exist_ok=True)

    absolute_path = os.path.join(output_dir, "safe_route_with_flood.html")

    # 保存
    fmap.save(absolute_path)
    print(f"✅ 地図を保存しました：{absolute_path}")

if __name__ == "__main__":
    main()