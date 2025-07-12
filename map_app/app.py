import json
import os
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for

# 災害別の地図生成モジュール
from map_utils.dosya import main as dosya
from map_utils.flood import main as flood
from map_utils.tsunami import main as tsunami

app = Flask(__name__)

def log(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}")

@app.route('/getGeolocate')
def getGeolocate():
    log("🔄 /getGeolocate にアクセスされました。")
    return render_template('geolocate.html')

@app.route('/api/json_geolocate/', methods=['POST'])
def json_geolocate():
    log("🚨 POSTリクエスト受信：/api/json_geolocate/")

    # JSON取得
    try:
        data = request.get_json(force=True)
        log(f"📥 JSONデータ取得成功: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except Exception as e:
        log("❌ JSON取得失敗:")
        traceback.print_exc()
        return jsonify({'error': 'Invalid JSON format'}), 400

    # バリデーション
    if not data:
        log("❗ JSONが空です")
        return jsonify({'error': 'No JSON data received'}), 400

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    category = data.get('category')

    if latitude is None or longitude is None:
        log("❗ 緯度または経度が欠けています")
        return jsonify({'error': 'Missing latitude or longitude'}), 400

    log(f"🛰 緯度: {latitude}, 経度: {longitude}")
    log(f"📌 災害カテゴリ: {category}")

    # JSON保存処理
    try:
        os.makedirs('data', exist_ok=True)
        save_path = os.path.join('data', 'geolocate.json')
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"💾 位置情報を {save_path} に保存しました。")
    except Exception:
        log("❌ JSON保存中にエラー:")
        traceback.print_exc()
        return jsonify({'error': 'Failed to save JSON'}), 500

    # 地図生成
    try:
        if category == 'flood':
            log("🛠 洪水マップ生成開始")
            flood()
            map_file = 'safe_route_with_flood.html'
        elif category == 'tsunami':
            log("🛠 津波マップ生成開始")
            tsunami()
            map_file = 'safe_route_with_tsunami.html'
        elif category == 'dosya':
            log("🛠 土砂災害マップ生成開始")
            dosya()
            map_file = 'safe_route_with_dosya.html'
        else:
            log(f"❌ 無効なカテゴリ指定: {category}")
            return jsonify({'status': 'error', 'message': 'invalid category'}), 400
    except Exception:
        log("❌ 地図生成中に例外:")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'map generation failed'}), 500

    # ファイル存在確認
    map_path = os.path.join(app.static_folder, 'maps', map_file)
    if not os.path.exists(map_path):
        log(f"❌ 生成された地図ファイルが存在しません: {map_path}")
        return jsonify({'status': 'error', 'message': 'map file not found'}), 500
    else:
        log(f"✅ 地図ファイルの存在確認済み: {map_path}")

    # URL生成
    try:
        map_url = url_for('static', filename=f'maps/{map_file}', _external=True)
        log(f"✅ 地図URL生成成功: {map_url}")
    except Exception:
        log("❌ URL生成中にエラー:")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'failed to build map URL'}), 500

    response = {'status': 'ok', 'map': map_url}
    log(f"📤 レスポンスJSON送信: {json.dumps(response, indent=2)}")
    return jsonify(response)

if __name__ == '__main__':
    log("🚀 Flaskアプリを起動中...")
    log("👉 アクセスURL: http://127.0.0.1:5000/getGeolocate")
    app.run(debug=True)
