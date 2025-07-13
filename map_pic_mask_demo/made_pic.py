import geopandas as gpd
import matplotlib.pyplot as plt
import os
import json
from PIL import Image

def generate_hazard_map():
    # --- 0. Setup Paths ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    map_dir = current_dir # Script is now inside the map directory

    shapefile_path = os.path.join(map_dir, '../data/flood/A31-12_17.shp')
    hazard_map_path = os.path.join(map_dir, 'ishikawa_flood_hazard_map.png')
    tsunami_path = os.path.join(map_dir, 'tsunami.png')
    composite_image_path = os.path.join(map_dir, 'composite_hazard_map.png')
    bounds_path = os.path.join(map_dir, 'bounds.json') # Changed to save in the same directory

    # --- 1. Create Flood Hazard Map Image ---
    try:
        gdf = gpd.read_file(shapefile_path, encoding='shift-jis')
        gdf = gdf.to_crs(epsg=4326) # Reproject to WGS84 (EPSG:4326)
    except Exception as e:
        print(f"Error reading shapefile: {e}")
        return # Exit the function if shapefile cannot be read

    minx, miny, maxx, maxy = gdf.total_bounds
    aspect_ratio = (maxx - minx) / (maxy - miny)

    fig_height_inches = 10
    fig_width_inches = fig_height_inches * aspect_ratio

    fig, ax = plt.subplots(1, 1, figsize=(fig_width_inches, fig_height_inches))
    if 'A31_006' in gdf.columns:
        gdf.plot(column='A31_006', cmap='viridis', linewidth=0.8, ax=ax, edgecolor='0.8', legend=False)
    else:
        gdf.plot(ax=ax, linewidth=0.8, edgecolor='0.8')

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    ax.axis('off')
    plt.savefig(hazard_map_path, dpi=1000, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)

    # --- 2. Composite Images ---
    try:
        hazard_map_mask_image = Image.open(hazard_map_path).convert("RGBA")
        tsunami_image = Image.open(tsunami_path).convert("RGBA")

        # Resize tsunami_image to match hazard_map_mask_image dimensions
        tsunami_image = tsunami_image.resize(hazard_map_mask_image.size, Image.LANCZOS)

        # Get the alpha channel of hazard_map_mask_image to use as a mask
        mask = hazard_map_mask_image.getchannel('A')

        # Create a new image for the result
        composite_image = Image.new("RGBA", hazard_map_mask_image.size)

        # Paste the tsunami_image onto the composite_image using the hazard_map_mask's alpha channel
        composite_image.paste(tsunami_image, (0, 0), mask=mask)

        composite_image.save(composite_image_path)
        print(f"Composite image saved to {composite_image_path}")
    except FileNotFoundError as e:
        print(f"Error opening image file: {e}")
        return # Exit the function if image file not found

    # --- 3. Save Bounds to JSON ---
    minx, miny, maxx, maxy = gdf.total_bounds
    bounds_data = {
        "minx": minx,
        "miny": miny,
        "maxx": maxx,
        "maxy": maxy
    }
    with open(bounds_path, 'w') as f:
        json.dump(bounds_data, f)

    print(f"Bounds data saved to {bounds_path}")
