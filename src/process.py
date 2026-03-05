import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from pathlib import Path
import logging
import json
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_indices(green, red, nir):
    """Calculates NDVI, GNDVI, and NDWI indices."""
    np.seterr(divide='ignore', invalid='ignore')
    
    # NDVI (Vegetation Health)
    ndvi = (nir - red) / (nir + red)
    
    # GNDVI (Chlorophyll Content)
    gndvi = (nir - green) / (nir + green)
    
    # NDWI (Water Content)
    ndwi = (green - nir) / (green + nir)
    
    return ndvi, gndvi, ndwi

def worker_risk_analysis(bands_paths, out_path):
    """Performs multi-spectral classification and risk assessment."""
    try:
        with rasterio.open(bands_paths["B03"]) as src_g, \
             rasterio.open(bands_paths["B04"]) as src_r, \
             rasterio.open(bands_paths["B08"]) as src_n:
            
            green = src_g.read(1).astype('float32')
            red = src_r.read(1).astype('float32')
            nir = src_n.read(1).astype('float32')

        ndvi, gndvi, ndwi = calculate_indices(green, red, nir)

        # --- CLASSIFICATION LOGIC ---
        # 1. Water (Blue)
        water_mask = (ndwi > 0.0)
        
        # 2. Urban/Barren (Gray)
        urban_mask = (ndvi < 0.30) & (~water_mask)
        
        # 3. Forest Analysis
        veg_mask = (~water_mask) & (~urban_mask)
        # Healthy Threshold: High Biomass (NDVI) AND High Chlorophyll (GNDVI)
        is_healthy = (ndvi >= 0.5) & (gndvi >= 0.40)
        
        classification = np.zeros_like(ndvi)
        classification[water_mask] = 1 
        classification[urban_mask] = 2 
        classification[veg_mask] = 4       # Default to Risk (Red)
        classification[veg_mask & is_healthy] = 3 # Upgrade to Healthy (Green)

        # --- METRICS CALCULATION ---
        count_healthy = np.sum(classification == 3)
        count_risk = np.sum(classification == 4)
        total_veg = count_healthy + count_risk
        
        stress_pct = float((count_risk / total_veg) * 100) if total_veg > 0 else 0.0
        veg_coverage = float(total_veg / ndvi.size * 100)
        
        # Determine Verdict
        if stress_pct > 20: status = "NON-COMPLIANT"
        elif stress_pct > 10: status = "HIGH RISK"
        else: status = "COMPLIANT"

        # Export Stats
        stats = {
            "stress_pct": round(stress_pct, 2),
            "status": status,
            "vegetation_cover_pct": round(veg_coverage, 2)
        }
        with open(out_path / "stats.json", "w") as f:
            json.dump(stats, f)
            
        # --- SCIENTIFIC VISUALIZATION (WITH LEGEND) ---
        colors_hex = ['#000000', '#2196f3', '#9e9e9e', '#4caf50', '#f44336']
        cmap = ListedColormap(colors_hex)
        bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        norm = BoundaryNorm(bounds, cmap.N)
        
        fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
        im = ax.imshow(classification, cmap=cmap, norm=norm, interpolation='nearest')
        ax.axis('off')
        
        # RESTORED LEGEND LOGIC
        legend_elements = [
            Patch(facecolor='#2196f3', edgecolor='black', label='Water (NDWI > 0)'),
            Patch(facecolor='#9e9e9e', edgecolor='black', label='Urban/Barren (NDVI < 0.3)'),
            Patch(facecolor='#4caf50', edgecolor='black', label='Healthy Biomass'),
            Patch(facecolor='#f44336', edgecolor='black', label='Degradation/Stress')
        ]
        
        # Place legend inside the plot to prevent cutoff
        ax.legend(handles=legend_elements, loc='upper right', title="Spectral Classification", fontsize=9, framealpha=0.9)
        
        plt.savefig(out_path / "HighRes_Analysis.png", bbox_inches='tight', pad_inches=0.1)
        plt.close()

        return "Risk Analysis Complete"
    except Exception as e:
        return f"Analysis Error: {e}"

def worker_generate_true_color(bands_paths, out_path):
    """Generates RGB composite for visual verification."""
    try:
        with rasterio.open(bands_paths["B04"]) as r, \
             rasterio.open(bands_paths["B03"]) as g, \
             rasterio.open(bands_paths["B02"]) as b:
            
            rgb = np.dstack((
                np.clip(r.read(1) / 2500.0, 0, 1),
                np.clip(g.read(1) / 2500.0, 0, 1),
                np.clip(b.read(1) / 2500.0, 0, 1)
            ))
            plt.imsave(out_path / "HighRes_Optical.png", rgb)
            return "Optical Generated"
    except Exception as e:
        return f"RGB Error: {e}"

class WaterStressAnalyzer:
    def __init__(self):
        self.raw_path = Path("data/raw")
        self.out_path = Path("data/processed")
        self.out_path.mkdir(parents=True, exist_ok=True)

    def run_parallel_pipeline(self):
        logger.info("Starting Processing Pipeline...")
        bands = {
            "B02": self.raw_path / "mosaic_B02.tif",
            "B03": self.raw_path / "mosaic_B03.tif",
            "B04": self.raw_path / "mosaic_B04.tif",
            "B08": self.raw_path / "mosaic_B08.tif"
        }
        # Use ThreadPool to avoid Windows Multiprocessing issues
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker_generate_true_color, bands, self.out_path)
            f2 = executor.submit(worker_risk_analysis, bands, self.out_path)
            logger.info(f"Pipeline Result: {f1.result()} | {f2.result()}")

if __name__ == "__main__":
    analyzer = WaterStressAnalyzer()
    analyzer.run_parallel_pipeline()