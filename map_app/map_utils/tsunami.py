def main():
    import geopandas as gpd
    from geopy.distance import geodesic
    import osmnx as ox
    import networkx as nx
    import folium
    from shapely.geometry import Point
    import pandas as pd
    from folium.features import CustomIcon
    import json


    radius_km = 2.0  # 半径を5.0kmに設定 (必要に応じて変更)

    # ダウンロード・解凍済みの S H P ファイルを指定(洪水浸水想定区域データ)
    tsunami_gdf = gpd.read_file("data/tsunami/A40-17_17.shp")  # 津波浸水想定データ



    # ダウンロード・解凍済みの S H P ファイルを指定(津波浸水想定データ)
    tsunami_gdf = gpd.read_file("data/tsunami/A40-17_17.shp")  # 津波浸水想定データ
    # WGS84 緯度経度 (EPSG:4326) に変換
    hazard_gdf = tsunami_gdf.to_crs(epsg=4326)

    # 避難所データの読み込み（UTF-8-SIG で正しく読み込む）
    file_path = "data/shelter.csv"  # 適宜ファイルパスを変更
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    # JSONファイルから現在地を読み込む
    with open("data/geolocate.json", "r", encoding="utf-8") as f:
        geo_data = json.load(f)
        current_location = [geo_data["latitude"], geo_data["longitude"]]

    print("✅ 現在地をgeojsonから取得しました：", current_location)

    # 現在地が危険区域内にあるかどうかの判定
    current_point = Point(current_location[1], current_location[0]) # Point(経度, 緯度)
    is_in_hazard_zone = hazard_gdf.contains(current_point).any()

    # 地図の初期化
    fmap = folium.Map(location=current_location, zoom_start=14)

    # カスタムアイコンの設定
    icon_start = CustomIcon(
    icon_image = 'map_utils/start.png'
    ,icon_size = (55, 65)
    ,icon_anchor = (30, 30)
    ,popup_anchor = (3, 3)
    )
    icon_goal = CustomIcon(
    icon_image = 'map_utils/goal.png'
    ,icon_size = (55, 65)
    ,icon_anchor = (30, 30)
    ,popup_anchor = (3, 3)
    )

    # foliumに渡すためにGeoJSON形式に変換
    geojson_data = hazard_gdf.to_json()

    # 津波浸水想定区域ポリゴンを地図に追加 (常に表示)
    folium.GeoJson(
        data=geojson_data,
        name="津波浸水想定区域",
        style_function=lambda feature: {
            'fillColor': '#66ccff',
            'color': '#0099cc',
            'weight': 1,
            'fillOpacity': 0.4,
        }
    ).add_to(fmap)


    # 現在地マーカーを地図に追加（危険区域内か外かでポップアップ内容を変更するため、ここではアイコンのみ設定）
    folium.Marker(location=current_location, icon=icon_start).add_to(fmap)


    # 現在地が危険区域内かどうかに応じて処理を分岐
    if is_in_hazard_zone:
        print("現在地は危険区域内にいます。避難経路を探索します。")
        # 現在地のポップアップを更新
        for marker in fmap._children.values():
            if isinstance(marker, folium.Marker) and marker.location == current_location:
                marker.popup = folium.Popup("現在地: 危険区域内")
                break

        # 緯度・経度が存在する避難所をフィルタリング
        initial_valid_shelters = df.dropna(subset=["緯度", "経度"])

        # === ここから半径`radius_km`以内の避難所に絞り込む処理を追加 ===
        print(f"半径{radius_km}km以内の避難所を絞り込み中...")
        
        # 現在地からの距離を計算
        initial_valid_shelters["距離(km)"] = initial_valid_shelters.apply(
            lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
        )
        
        # 半径`radius_km`以内の避難所のみを抽出
        valid_shelters = initial_valid_shelters[initial_valid_shelters["距離(km)"] <= radius_km].copy()
        
        if valid_shelters.empty:
            print(f"⚠️ 半径 {radius_km}km 以内に有効な避難所が見つかりませんでした。")
            # この場合、経路探索は行わない
            print("\n--- 最適な避難経路が見つかりませんでした。 ---")
            folium.Marker(location=current_location, popup="現在地: 危険区域内（経路なし）", icon=icon_start).add_to(fmap)
            fmap.save("../templates/safe_route_with_tsunami.html") # HTMLファイル名をtsunami版に
            print("✅ 地図を保存しました：safe_route_with_tsunami.html")
            return # ここで処理を終了

        print(f"✅ 半径 {radius_km}km 以内に {len(valid_shelters)} 箇所の避難所が見つかりました。")
        # === 半径`radius_km`以内の避難所に絞り込む処理ここまで ===


        # 避難所を「危険区域外の避難所」と「危険区域内の避難所」に分類
        safe_shelters = []
        hazard_shelters = []
        for idx, row in valid_shelters.iterrows():
            shelter_point = Point(row["経度"], row["緯度"])
            if not hazard_gdf.contains(shelter_point).any():
                safe_shelters.append(row)
            else:
                hazard_shelters.append(row)
        
        safe_shelters_df = pd.DataFrame(safe_shelters)
        hazard_shelters_df = pd.DataFrame(hazard_shelters)

        # 全ての避難所をマップに表示
        for idx, row in valid_shelters.iterrows():
            # 避難所が危険区域内の場合は赤色、危険区域外の場合は緑色で表示
            shelter_point = Point(row["経度"], row["緯度"])
            marker_color = "red" if hazard_gdf.contains(shelter_point).any() else "green"
            folium.Marker(
                location=(row["緯度"], row["経度"]),
                popup=f"避難所: {row.get('名称', '名称不明')}",
                icon=folium.Icon(color=marker_color, icon="home")
            ).add_to(fmap)

        # 道路グラフ取得（一度だけ）
        G = ox.graph_from_point(current_location, dist=radius_km * 1000 + 500, network_type='walk')
        nodes = [(n, Point(d['x'], d['y'])) for n, d in G.nodes(data=True)]
        node_gdf = gpd.GeoDataFrame(nodes, columns=["node", "geometry"], crs="EPSG:4326")

        # ノードと津波浸水想定ポリゴンの空間結合（交差するノードを特定）
        hazard_nodes_in_graph = gpd.sjoin(node_gdf, hazard_gdf, how='inner', predicate='intersects')
        hazard_node_ids = set(hazard_nodes_in_graph["node"])

        # 1. 危険区域ノードを完全に削除したグラフ (厳密な安全経路用)
        # 始点ノードは削除しないようにする
        G_safe_strict = G.copy()
        orig_node = ox.distance.nearest_nodes(G, X=current_location[1], Y=current_location[0])
        nodes_to_remove_from_strict = hazard_node_ids - {orig_node}
        G_safe_strict.remove_nodes_from(nodes_to_remove_from_strict)
        
        # 2. 危険区域内のエッジにペナルティを加えたグラフ (迂回を考慮した経路用)
        G_weighted = G.copy()
        for u, v, k, data in G_weighted.edges(keys=True, data=True):
            if 'length' not in data:
                data['length'] = ox.distance.great_circle_vec(
                    G_weighted.nodes[u]['y'], G_weighted.nodes[u]['x'],
                    G_weighted.nodes[v]['y'], G_weighted.nodes[v]['x']
                )
        penalty_factor = 10000000 # より大きなペナルティ値
        for u, v, k, data in G_weighted.edges(keys=True, data=True):
            if u in hazard_node_ids or v in hazard_node_ids:
                data['length'] += penalty_factor

        best_route = None
        best_shelter_location = None
        min_route_length = float('inf')
        route_color = "red" # 安全経路
        route_tooltip = "安全避難経路"

        # **フェーズ1: 危険区域外の避難所への、危険区域を通らない経路を探索（メインの最適経路として）**
        print("\n--- フェーズ1: 危険区域外の避難所への、厳密に安全な最適経路を探索中 ---")
        if orig_node in G_safe_strict and not safe_shelters_df.empty:
            for idx, shelter in safe_shelters_df.iterrows():
                dest_node = ox.distance.nearest_nodes(G, X=shelter["経度"], Y=shelter["緯度"])
                if dest_node in G_safe_strict:
                    try:
                        current_route = nx.shortest_path(G_safe_strict, orig_node, dest_node, weight='length')
                        current_route_length = sum(ox.utils_graph.get_route_edge_attributes(G_safe_strict, current_route, 'length'))

                        if current_route_length < min_route_length:
                            min_route_length = current_route_length
                            best_route = current_route
                            best_shelter_location = (shelter["緯度"], shelter["経度"])
                            print(f"  ✅ フェーズ1: 最適な安全経路発見: {shelter.get('名称', '名称不明')}, 長さ: {current_route_length:.2f}m")
                    except nx.NetworkXNoPath:
                        print(f"  ⚠️ フェーズ1: 避難所 {shelter.get('名称', '名称不明')} への厳密に安全な経路は見つかりませんでした。")
                else:
                    print(f"  ⚠️ フェーズ1: 避難所ノード {shelter.get('名称', '名称不明')} は厳密な安全グラフ G_safe_strict に存在しません。")
        else:
            if orig_node not in G_safe_strict:
                print("  ⚠️ フェーズ1: 始点ノードが危険区域内にいるため、厳密な安全経路は探索できません。")
            if safe_shelters_df.empty:
                print("  ⚠️ フェーズ1: 危険区域外に避難所が見つかりませんでした。")

        # **フェーズ2: フェーズ1で見つからなかった場合、避難所の選択ロジックを分岐**
        if best_route is None:
            if not safe_shelters_df.empty:
                # 危険区域外の避難所がある場合 -> 危険区域外の避難所へのペナルティ付き最短経路を探索
                print("\n--- フェーズ2a: 危険区域を通らない経路が見つからなかったため、危険区域外の避難所へのペナルティ付き最短経路を探索します。 ---")
                
                # フェーズ1で既に距離計算済みの場合もあるが、念のため再計算または存在確認
                if "距離(km)" not in safe_shelters_df.columns:
                     safe_shelters_df["距離(km)"] = safe_shelters_df.apply(
                        lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
                    )
                nearest_shelter_df = safe_shelters_df.loc[safe_shelters_df["距離(km)"].idxmin()]
                nearest_location = (nearest_shelter_df["緯度"], nearest_shelter_df["経度"])

                orig_node_weighted = ox.distance.nearest_nodes(G_weighted, X=current_location[1], Y=current_location[0])
                dest_node_weighted = ox.distance.nearest_nodes(G_weighted, X=nearest_location[1], Y=nearest_location[0])

                if orig_node_weighted in G_weighted and dest_node_weighted in G_weighted:
                    try:
                        best_route = nx.astar_path(G_weighted, orig_node_weighted, dest_node_weighted, weight='length')
                        best_shelter_location = nearest_location
                        route_color = "red"
                        route_tooltip = "最短（一部危険区域通過）避難経路"
                        print(f"  ✅ フェーズ2a: ペナルティ付き最短経路を危険区域外の避難所 {nearest_shelter_df.get('名称', '名称不明')} へ表示します。")
                    except nx.NetworkXNoPath:
                        print("  ⚠️ フェーズ2a: ペナルティ付きのグラフでも、危険区域外の避難所への経路が見つかりませんでした。")
                else:
                    print("  ⚠️ フェーズ2a: 始点または終点ノードがペナルティ付きグラフに存在しません。")

            else: # 危険区域外の避難所が一つもない場合
                # 危険区域内の避難所を含めた全避難所の中から最短距離の避難所を選択
                print("\n--- フェーズ2b: 危険区域外に避難所がないため、危険区域内の最短避難所へのペナルティ付き最短経路を探索します。 ---")
                
                # valid_shelters (半径`radius_km`以内の全避難所) を使用
                if not valid_shelters.empty:
                    # 距離がまだ計算されていない場合、計算する
                    if "距離(km)" not in valid_shelters.columns:
                        valid_shelters["距離(km)"] = valid_shelters.apply(
                            lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
                        )
                    nearest_shelter_df = valid_shelters.loc[valid_shelters["距離(km)"].idxmin()]
                    nearest_location = (nearest_shelter_df["緯度"], nearest_shelter_df["経度"])

                    orig_node_weighted = ox.distance.nearest_nodes(G_weighted, X=current_location[1], Y=current_location[0])
                    dest_node_weighted = ox.distance.nearest_nodes(G_weighted, X=nearest_location[1], Y=nearest_location[0])

                    if orig_node_weighted in G_weighted and dest_node_weighted in G_weighted:
                        try:
                            best_route = nx.astar_path(G_weighted, orig_node_weighted, dest_node_weighted, weight='length')
                            best_shelter_location = nearest_location
                            route_color = "red"
                            route_tooltip = "最短（一部危険区域通過）避難経路"
                            print(f"  ✅ フェーズ2b: ペナルティ付き最短経路を危険区域内の避難所 {nearest_shelter_df.get('名称', '名称不明')} へ表示します。")
                        except nx.NetworkXNoPath:
                            print("  ⚠️ フェーズ2b: ペナルティ付きのグラフでも、危険区域内の避難所への経路が見つかりませんでした。")
                    else:
                        print("  ⚠️ フェーズ2b: 始点または終点ノードがペナルティ付きグラフに存在しません。")
                else:
                    print("  ⚠️ フェーズ2b: 半径内に有効な避難所が一つもありませんでした。")


        # 最終的に見つかったメインの経路と避難所を地図に描画
        if best_route:
            route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in best_route]
            folium.PolyLine(route_coords, color=route_color, weight=5, opacity=0.7, tooltip=route_tooltip).add_to(fmap)
            
            final_shelter_info = valid_shelters.loc[(valid_shelters['緯度']==best_shelter_location[0]) & (valid_shelters['経度']==best_shelter_location[1])].iloc[0]
            folium.Marker(location=best_shelter_location, popup=f"メイン避難所: {final_shelter_info.get('名称', '名称不明')}", icon=icon_goal).add_to(fmap)
        else:
            print("\n--- 最適な避難経路が見つかりませんでした。 ---")
            folium.Marker(location=current_location, popup="現在地: 危険区域内（経路なし）", icon=icon_start).add_to(fmap)

        # **追加要件: 最短経路以外の安全な避難所へのルートも表示**
        # ただし、メインの経路の避難所と同じ場所への経路は除外
        print("\n--- 追加: 他の危険区域外避難所への安全経路を探索中 ---")
        print(f"現在の始点ノード (orig_node): {orig_node}")
        print(f"orig_node は G_safe_strict に存在しますか？: {orig_node in G_safe_strict}")
        print(f"危険区域外の避難所は存在しますか？: {not safe_shelters_df.empty}")

        if orig_node in G_safe_strict and not safe_shelters_df.empty: # 現在地が厳密な安全グラフにいる場合のみ、このフェーズを実行
            found_additional_safe_route = False
            for idx, shelter in safe_shelters_df.iterrows():
                shelter_loc = (shelter["緯度"], shelter["経度"])
                
                # メインの避難所への経路と重ならないようにする
                if best_shelter_location and shelter_loc == best_shelter_location:
                    print(f"  スキップ: メイン経路の避難所 {shelter.get('名称', '名称不明')} への経路は既に描画済みです。")
                    continue

                dest_node = ox.distance.nearest_nodes(G, X=shelter["経度"], Y=shelter["緯度"])
                print(f"  避難所: {shelter.get('名称', '名称不明')} (緯度: {shelter['緯度']:.6f}, 経度: {shelter['経度']:.6f})")
                print(f"  避難所ノード (dest_node): {dest_node}")
                print(f"  dest_node は G_safe_strict に存在しますか？: {dest_node in G_safe_strict}")

                if dest_node in G_safe_strict:
                    try:
                        other_safe_route = nx.shortest_path(G_safe_strict, orig_node, dest_node, weight='length')
                        other_route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in other_safe_route]
                        
                        # 別の安全経路として、青色で描画
                        folium.PolyLine(other_route_coords, color="blue", weight=3, opacity=0.5, tooltip=f"安全避難経路: {shelter.get('名称', '名称不明')}").add_to(fmap)
                        print(f"  ✅ 追加経路: 安全な避難所 {shelter.get('名称', '名称不明')} への経路を表示しました。")
                        found_additional_safe_route = True
                    except nx.NetworkXNoPath:
                        print(f"  ⚠️ 経路なし: 避難所 {shelter.get('名称', '名称不明')} への厳密に安全な経路は見つかりませんでした。")
                else:
                    print(f"  ⚠️ 避難所ノード {shelter.get('名称', '名称不明')} は厳密な安全グラフ G_safe_strict に存在しません。")
            
            if not found_additional_safe_route:
                print("--- 追加: 他の安全な避難所への経路は見つかりませんでした。 ---")

        else:
            if orig_node not in G_safe_strict:
                print("--- 追加: 始点ノードが厳密な安全グラフにないため、他の安全経路は探索しません。 ---")
            if safe_shelters_df.empty:
                print("--- 追加: 危険区域外に避難所が見つかりませんでした。 ---")


    else: # 現在地が危険区域外の場合
        print("現在地は危険区域外です。安全です。")
        # 現在地のポップアップを更新
        for marker in fmap._children.values():
            if isinstance(marker, folium.Marker) and marker.location == current_location:
                marker.popup = folium.Popup("現在地: 安全です")
                break

        # 全避難所をマップに表示 (危険区域外でも避難所の場所は知りたい可能性があるため)
        initial_valid_shelters = df.dropna(subset=["緯度", "経度"])

        # === ここから半径`radius_km`以内の避難所に絞り込む処理を追加 ===
        print(f"半径{radius_km}km以内の避難所を絞り込み中...")
        
        # 現在地からの距離を計算
        initial_valid_shelters["距離(km)"] = initial_valid_shelters.apply(
            lambda row: geodesic(current_location, (row["緯度"], row["経度"])).km, axis=1
        )
        
        # 半径`radius_km`以内の避難所のみを抽出
        valid_shelters = initial_valid_shelters[initial_valid_shelters["距離(km)"] <= radius_km].copy()
        
        if valid_shelters.empty:
            print(f"⚠️ 半径 {radius_km}km 以内に有効な避難所が見つかりませんでした。")
            # 危険区域外なので、経路探索は不要。避難所なしの表示で終了
            folium.Marker(location=current_location, popup="現在地: 安全です（避難所なし）", icon=icon_start).add_to(fmap)
            fmap.save("../templates/safe_route_with_tsunami.html") # HTMLファイル名をtsunami版に
            print("✅ 地図を保存しました：safe_route_with_tsunami.html")
            return # ここで処理を終了

        print(f"✅ 半径 {radius_km}km 以内に {len(valid_shelters)} 箇所の避難所が見つかりました。")
        # === 半径`radius_km`以内の避難所に絞り込む処理ここまで ===

        for idx, row in valid_shelters.iterrows():
            # 避難所が危険区域内の場合は赤色、危険区域外の場合は緑色で表示
            shelter_point = Point(row["経度"], row["緯度"])
            marker_color = "red" if hazard_gdf.contains(shelter_point).any() else "green"
            folium.Marker(
                location=(row["緯度"], row["経度"]),
                popup=f"避難所: {row.get('施設・場所名')}",
                icon=folium.Icon(color=marker_color, icon="home")
            ).add_to(fmap)

    

    import os

    # 保存先の絶対パスを指定（static/maps/ に保存）
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'maps'))
    os.makedirs(output_dir, exist_ok=True)

    absolute_path = os.path.join(output_dir, "safe_route_with_tsunami.html")

    # 保存
    fmap.save(absolute_path)
    print(f"✅ 地図を保存しました：{absolute_path}")

if __name__ == "__main__":

    main()

