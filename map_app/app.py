import json
import os

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/getGeolocate')
def getGeolocate():
    return render_template('geolocate.html')

@app.route('/api/json_geolocate/', methods=['POST'])
def json_geolocate():
    # JSONデータを取得
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400

    latitude = data.get('latitude')
    longitude = data.get('longitude')

    # 必須項目チェック
    if latitude is None or longitude is None:
        return jsonify({'error': 'Missing latitude or longitude'}), 400

    # ここで必要な処理（例：DB保存など）を実施
    print(f"受信した緯度: {latitude}, 経度: {longitude}")
    
    # jsonの保存
    save_dir = 'data'
    fileName = 'geolocate.json'
    file_path = os.path.join(save_dir, fileName)
    
    # JSONとして保存
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # レスポンスを返す
    return jsonify({'status': 'ok', 'received': {'latitude': latitude, 'longitude': longitude}})
    

if __name__ == '__main__':
    app.run(debug=True)