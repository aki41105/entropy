import geopandas as gpd
from geopy.distance import geodesic
import osmnx as ox
import networkx as nx
import folium
from shapely.geometry import Point
import pandas as pd
import json

# ダウンロード・解凍済みの S H P ファイルを指定(津波浸水想定区域データ)
tsunami_gdf = gpd.read_file("tsunami/A40-17_17.shp")  # 津波浸水想定データ


# WGS84 緯度経度 (EPSG:4326) に変換
hazard_gdf = tsunami_gdf.to_crs(epsg=4326)

# 避難所データの読み込み（UTF-8-SIG で正しく読み込む）
file_path = "170003_evacuation_space.csv"  # 適宜ファイルパスを変更
df = pd.read_csv(file_path, encoding="utf-8-sig")

# JSONファイルから現在地を読み込む
with open("map_app/data/geolocate.json", "r", encoding="utf-8") as f:
    geo_data = json.load(f)
    current_location = [geo_data["latitude"], geo_data["longitude"]]

# 「災害種別_津波」列を 1 or 0 の整数に変換（それ以外はNaNに）
df["災害種別_津波"] = pd.to_numeric(df["災害種別_津波"], errors="coerce")

# 1または0のみ残す（文字列や"－"は除外）
df = df[df["災害種別_津波"].isin([0, 1])]

# 災害種別の指定
valid_shelters = df[
    (df["災害種別_津波"] == 1) & df["緯度"].notna() & df["経度"].notna()
].copy()

# 現在地からの距離計算
valid_shelters["距離(km)"] = valid_shelters.apply(
    lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
)

# 安全な避難所だけに限定（危険区域と重なっていないもの）
shelter_points = gpd.GeoDataFrame(
    valid_shelters,
    geometry=gpd.points_from_xy(valid_shelters["経度"], valid_shelters["緯度"]),
    crs="EPSG:4326"
)
safe_shelters = gpd.sjoin(shelter_points, hazard_gdf, how="left", predicate="intersects")
safe_shelters = safe_shelters[safe_shelters["index_right"].isna()]  # 洪水域に入ってない

# 安全な避難所だけに限定（危険区域と重なっていないもの）
shelter_points = gpd.GeoDataFrame(
    valid_shelters,
    geometry=gpd.points_from_xy(valid_shelters["経度"], valid_shelters["緯度"]),
    crs="EPSG:4326"
)
safe_shelters = gpd.sjoin(shelter_points, hazard_gdf, how="left", predicate="intersects")
safe_shelters = safe_shelters[safe_shelters["index_right"].isna()]  # 洪水域に入ってない

# 最も近い安全な避難所
nearest = safe_shelters.loc[safe_shelters["距離(km)"].idxmin()]
nearest_location = (nearest["緯度"], nearest["経度"])

# 道路グラフ取得
G = ox.graph_from_point(current_location, dist=2000, network_type='walk')
nodes = [(n, Point(d['x'], d['y'])) for n, d in G.nodes(data=True)]
node_gdf = gpd.GeoDataFrame(nodes, columns=["node", "geometry"], crs="EPSG:4326")

# ノードと危険区域ポリゴンの空間結合（交差するノードを特定）
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
folium.Marker(location=current_location, popup="現在地", icon=folium.Icon(color="green")).add_to(fmap)
folium.Marker(location=nearest_location, popup="避難所", icon=folium.Icon(color="red")).add_to(fmap)
folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(fmap)

# foliumに渡すためにGeoJSON形式に変換
geojson_data = hazard_gdf.to_json()

# 危険区域ポリゴンを地図に追加
folium.GeoJson(
    data=geojson_data,
    name="津波浸水想定区域",
    style_function=lambda feature: {
        'fillColor': '#66ccff',
        'color': '#0099cc',
        'weight': 1.5,
        'fillOpacity': 0.6,
        'dashArray': '5, 5'
    }
).add_to(fmap)

# HTML形式で保存
fmap.save("safe_route_with_tsunami.html")
print("✅ 地図を保存しました：safe_route_with_tsunami.html")