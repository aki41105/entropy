import geopandas as gpd
from geopy.distance import geodesic
import osmnx as ox
import networkx as nx
import folium
from shapely.geometry import Point
import pandas as pd
<<<<<<< HEAD
import os
=======
import json
>>>>>>> 9a9032e1f9fd7d3924cb46a5b158dd4130af7cd7

# SHPファイルの読み込み（適宜パスを調整）
landslide_gdf = gpd.read_file("dosha/A33-18_17Polygon.shp")  # 土砂災害想定区域データ
hazard_gdf = landslide_gdf.to_crs(epsg=4326)

# 避難所CSVの読み込み
df = pd.read_csv("170003_evacuation_space.csv", encoding="utf-8-sig")

<<<<<<< HEAD
# 現在地
current_location = [36.599901, 136.677889]

# 距離を計算し避難所を絞り込む
valid_shelters = df.dropna(subset=["緯度", "経度"]).copy()
=======
# JSONファイルから現在地を読み込む
with open("map_app/data/geolocate.json", "r", encoding="utf-8") as f:
    geo_data = json.load(f)
    current_location = [geo_data["latitude"], geo_data["longitude"]]

# 災害種別の指定
valid_shelters = df[
    (df["災害種別_崖崩れ、土石流及び地滑り"] == 1) & df["緯度"].notna() & df["経度"].notna()
].copy()

# 現在地からの距離計算
>>>>>>> 9a9032e1f9fd7d3924cb46a5b158dd4130af7cd7
valid_shelters["距離(km)"] = valid_shelters.apply(
    lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
)

<<<<<<< HEAD
=======
# 安全な避難所だけに限定（危険区域と重なっていないもの）
>>>>>>> 9a9032e1f9fd7d3924cb46a5b158dd4130af7cd7
shelter_points = gpd.GeoDataFrame(
    valid_shelters,
    geometry=gpd.points_from_xy(valid_shelters["経度"], valid_shelters["緯度"]),
    crs="EPSG:4326"
)
safe_shelters = gpd.sjoin(shelter_points, hazard_gdf, how="left", predicate="intersects")
safe_shelters = safe_shelters[safe_shelters["index_right"].isna()]
nearest = safe_shelters.loc[safe_shelters["距離(km)"].idxmin()]
nearest_location = (nearest["緯度"], nearest["経度"])

# 道路グラフ取得と危険領域ノードの除去
G = ox.graph_from_point(current_location, dist=2000, network_type='walk')
nodes = [(n, Point(d['x'], d['y'])) for n, d in G.nodes(data=True)]
node_gdf = gpd.GeoDataFrame(nodes, columns=["node", "geometry"], crs="EPSG:4326")
hazard_nodes = gpd.sjoin(node_gdf, hazard_gdf, how='inner', predicate='intersects')
hazard_node_ids = set(hazard_nodes["node"])
G_safe = G.copy()
G_safe.remove_nodes_from(hazard_node_ids)

# 経路探索
orig_node = ox.distance.nearest_nodes(G_safe, X=current_location[1], Y=current_location[0])
dest_node = ox.distance.nearest_nodes(G_safe, X=nearest_location[1], Y=nearest_location[0])
safe_route = nx.astar_path(G_safe, orig_node, dest_node, weight='length')
route_coords = [(G_safe.nodes[n]['y'], G_safe.nodes[n]['x']) for n in safe_route]

# 地図描画
fmap = folium.Map(location=current_location, zoom_start=14)
folium.Marker(location=current_location, popup="現在地", icon=folium.Icon(color="green")).add_to(fmap)
folium.Marker(location=nearest_location, popup="避難所", icon=folium.Icon(color="red")).add_to(fmap)
folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(fmap)

<<<<<<< HEAD
=======
# foliumに渡すためにGeoJSON形式に変換
geojson_data = hazard_gdf.to_json()

# 危険区域ポリゴンを地図に追加
>>>>>>> 9a9032e1f9fd7d3924cb46a5b158dd4130af7cd7
folium.GeoJson(
    data=hazard_gdf.to_json(),
    name="土砂災害想定区域",
    style_function=lambda feature: {
        'fillColor': '#cc9966',
        'color': '#cc3300',
        'weight': 1,
        'fillOpacity': 0.4,
    }
).add_to(fmap)

# ✅ 地図を Flask の static/maps に保存
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'maps'))
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "safe_route_with_dosya.html")
fmap.save(output_path)

print(f"✅ 地図を保存しました：{output_path}")
