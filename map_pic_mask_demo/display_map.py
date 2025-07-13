import folium
from folium.raster_layers import ImageOverlay
import os
import json
from made_pic import generate_hazard_map

# --- 0. Setup Paths ---
current_dir = os.path.dirname(os.path.abspath(__file__))
map_dir = current_dir # Script is now inside the map directory

composite_image_path = os.path.join(map_dir, 'composite_hazard_map.png')
bounds_path = os.path.join(map_dir, 'bounds.json')
map_output_path = os.path.join(map_dir, 'composite_folium_map.html')

# --- Generate Hazard Map ---
generate_hazard_map()

# --- 1. Load Bounds from JSON ---
try:
    with open(bounds_path, 'r') as f:
        bounds_data = json.load(f)
except FileNotFoundError:
    print(f"Error: bounds.json not found. Please run test.py first.")
    exit()

minx = bounds_data['minx']
miny = bounds_data['miny']
maxx = bounds_data['maxx']
maxy = bounds_data['maxy']

# --- 2. Create Folium Map ---
map_center = [(miny + maxy) / 2, (minx + maxx) / 2]
m = folium.Map(location=map_center, zoom_start=9)

img_overlay = ImageOverlay(
    image=composite_image_path,
    bounds=[[miny, minx], [maxy, maxx]],
    opacity=0.7,
    name='Composite Hazard Map'
)

img_overlay.add_to(m)
folium.LayerControl().add_to(m)
m.save(map_output_path)

print(f"Folium map saved to {map_output_path}")
