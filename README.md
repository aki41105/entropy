# hackson 2025(7/12 - 7/13)

## 作成物
今回のハッカソンでは、児童向けハザードマップを作成した。

## ディレクトリ構造
```
.
├── map_app                         # flask app 
│   ├── cache
│   ├── data                        # データ保存場所
│   │   ├── dosha                   # 土砂災害データ
│   │   ├── flood                   # 洪水データ
│   │   └── tsunami                 # 津波データ
│   ├── map_utils                   # マップ作成に使うutil
│   ├── static                      # 静的ファイル
│   └── templates                   # 作成されたHTMLの保存先
├── map_pic_mask_demo               # 画像のマスキングデモ
```

## 使用方法
```bash
cd map_app
pip install -r requirements.txt
python app.py
```