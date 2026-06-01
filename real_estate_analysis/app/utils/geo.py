import numpy as np
import pandas as pd

try:
    from pyproj import Transformer
    _transformer = Transformer.from_crs("EPSG:3794", "EPSG:4326", always_xy=True)
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


def d96_to_wgs84(easting: float, northing: float) -> tuple:
    """Convert D96/TM (EPSG:3794) coordinates to WGS84 (lon, lat)."""
    if not PYPROJ_AVAILABLE:
        # Rough linear approximation for Slovenia as fallback
        lon = (easting - 374000) / 111320 + 14.5
        lat = (northing - 5000000) / 111000 + 45.0
        return lon, lat
    lon, lat = _transformer.transform(easting, northing)
    return lon, lat


def convert_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Add lon/lat columns to dataframe from E_CENTROID/N_CENTROID."""
    mask = df["E_CENTROID"].notna() & df["N_CENTROID"].notna()
    result = df.copy()
    result["lon"] = np.nan
    result["lat"] = np.nan

    if mask.any():
        east = pd.to_numeric(df.loc[mask, "E_CENTROID"], errors="coerce")
        north = pd.to_numeric(df.loc[mask, "N_CENTROID"], errors="coerce")
        valid = east.notna() & north.notna()

        if valid.any():
            lons, lats = d96_to_wgs84(
                east[valid].values,
                north[valid].values,
            )
            result.loc[mask[mask].index[valid], "lon"] = lons
            result.loc[mask[mask].index[valid], "lat"] = lats

    return result


def hexbin_aggregate(
    df: pd.DataFrame,
    hex_size_m: float = 150,
    min_count: int = 3,
) -> pd.DataFrame:
    """
    Aggregate points into approximate hexagonal bins using a grid approach.
    Returns dataframe with hex_lon, hex_lat, median_cena_m2, count columns.
    """
    if df.empty or "lon" not in df.columns:
        return pd.DataFrame()

    valid = df.dropna(subset=["lon", "lat", "CENA_M2"])
    if valid.empty:
        return pd.DataFrame()

    # Approximate degrees per meter at Slovenian latitudes (~46°N)
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * np.cos(np.radians(46.0)))

    cell_lat = hex_size_m * deg_per_m_lat
    cell_lon = hex_size_m * deg_per_m_lon * 1.1547  # hexagonal offset factor

    valid = valid.copy()
    valid["hex_col"] = np.floor(valid["lon"] / cell_lon).astype(int)
    valid["hex_row"] = np.floor(valid["lat"] / cell_lat).astype(int)
    # Offset every other column for hexagonal appearance
    valid["hex_row"] = valid["hex_row"] + (valid["hex_col"] % 2) * 0.5
    valid["hex_row"] = np.floor(valid["hex_row"]).astype(int)

    agg = (
        valid.groupby(["hex_col", "hex_row"])
        .agg(
            median_cena_m2=("CENA_M2", "median"),
            count=("CENA_M2", "count"),
        )
        .reset_index()
    )

    # Exact grid cell centers (not mean of data points) so hexagons tile without overlap.
    # Even columns: center_lat = (row + 0.5) * cell_lat
    # Odd  columns: center_lat = row * cell_lat  (because of the 0.5 floor-offset above)
    agg["hex_lon"] = (agg["hex_col"] + 0.5) * cell_lon
    agg["hex_lat"] = (agg["hex_row"] + (1 - agg["hex_col"] % 2) * 0.5) * cell_lat

    return agg[agg["count"] >= min_count]
