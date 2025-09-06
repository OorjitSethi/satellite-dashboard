from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from scipy.integrate import solve_ivp
from sgp4.api import Satrec, jday
import requests
import time
import os
import threading
from datetime import datetime, timedelta

# --- Initialize Flask App and CORS ---
app = Flask(__name__)
# This allows the React app (running on a different port) to make requests to this backend
CORS(app)

# ------------------------------------------------------------------
# 0.  Global Satellite Database (Pre-loaded for fast search)
# ------------------------------------------------------------------

# Global satellite database
SATELLITE_DB = []
DB_LAST_UPDATED = None
DB_UPDATE_INTERVAL = timedelta(hours=6)  # Update every 6 hours
DB_LOADING = False  # Flag to prevent multiple simultaneous loads
DB_SOURCE = 'remote'  # 'file' or 'remote'
# SGP4 is accurate close to the TLE epoch. If elements are older than this threshold,
# anchor propagation to the TLE epoch instead of "now" to avoid nonsensical tracks.
STALE_TLE_THRESHOLD_HOURS = 72  # 3 days

# Optional local TLE catalog file (3-line TLE sets: name, L1, L2)
TLE_FILE_PATH = os.environ.get(
    'TLE_FILE',
    os.path.join(os.path.dirname(__file__), 'data', 'tle_catalog.txt')
)

def parse_tle_file(file_path):
    """Parse a local TLE catalog file and return a list of satellites.
    Expects 3-line entries: name line, line1 (starts with '1 '), line2 (starts with '2 ').
    Safely skips malformed entries.
    """
    sats = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_lines = [ln.rstrip('\n').strip() for ln in f if ln.strip()]
        i = 0
        skipped = 0
        while i < len(raw_lines):
            name = raw_lines[i]
            line1 = raw_lines[i+1] if i + 1 < len(raw_lines) else ''
            line2 = raw_lines[i+2] if i + 2 < len(raw_lines) else ''
            if line1.startswith('1 ') and line2.startswith('2 '):
                # NORAD catalog number is columns 3-7 (1-based); Python slice [2:7]
                norad_id = line1[2:7].strip()
                sats.append({
                    'norad_id': norad_id or '',
                    'name': name,
                    'tle_line1': line1,
                    'tle_line2': line2,
                })
                i += 3
            else:
                # Try to resync by advancing one line
                skipped += 1
                i += 1
        print(f"[DB] Parsed {len(sats)} TLEs from file; skipped {skipped} lines while syncing")
    except FileNotFoundError:
        print(f"[DB] TLE file not found: {file_path}")
    except Exception as e:
        print(f"[DB] Error parsing TLE file '{file_path}': {e}")
    return sats

def load_satellite_database():
    """Load all satellite data into memory for fast searching"""
    global SATELLITE_DB, DB_LAST_UPDATED, DB_LOADING, DB_SOURCE
    
    if DB_LOADING:
        print("[DB] Database load already in progress, skipping...")
        return
    
    DB_LOADING = True
    print(f"[DB] Starting database load at {datetime.now()}")
    print(f"[DB] Current database size: {len(SATELLITE_DB)} satellites")
    
    try:
        # 1) Prefer local file if present
        if os.path.isfile(TLE_FILE_PATH):
            print(f"[DB] Loading satellites from local TLE file: {TLE_FILE_PATH}")
            file_sats = parse_tle_file(TLE_FILE_PATH)
            if file_sats:
                SATELLITE_DB = file_sats
                DB_LAST_UPDATED = datetime.now()
                DB_SOURCE = 'file'
                print(f"[DB] ✓ Loaded {len(SATELLITE_DB)} satellites from local file")
                # Show sample
                for i, sat in enumerate(SATELLITE_DB[:5]):
                    print(f"[DB]   {i+1}. {sat['name']} (ID: {sat['norad_id']})")
                return
            else:
                print("[DB] Local TLE file present but no entries parsed; falling back to remote fetch")

        # 2) Remote fetch fallback (CelesTrak groups)
        print("[DB] Fetching satellite data from CelesTrak...")
        
        # Fetch from multiple groups to get a comprehensive list
        groups = ['active', 'stations', 'weather', 'noaa', 'goes', 'resource', 'sarsat', 'dmc', 'tdrss', 'argos', 'planet', 'spire']
        all_satellites = []
        
        for i, group in enumerate(groups):
            try:
                print(f"[DB] Loading {group} satellites... ({i+1}/{len(groups)})")
                url = "https://celestrak.org/NORAD/elements/gp.php"
                params = {'GROUP': group, 'FORMAT': 'json'}
                
                print(f"[DB] Making request to: {url}?GROUP={group}&FORMAT=json")
                response = requests.get(url, params=params, timeout=30)
                print(f"[DB] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    satellites = response.json()
                    if isinstance(satellites, list):
                        all_satellites.extend(satellites)
                        print(f"[DB]   ✓ Loaded {len(satellites)} satellites from {group}")
                    else:
                        print(f"[DB]   ✗ Unexpected response format for {group}: {type(satellites)}")
                else:
                    print(f"[DB]   ✗ Failed to load {group}: HTTP {response.status_code}")
                
                print(f"[DB] Waiting 0.5s before next request...")
                time.sleep(0.5)  # Be nice to CelesTrak
                
            except Exception as e:
                print(f"[DB]   ✗ Exception loading group {group}: {e}")
                continue
        
        print(f"[DB] Total satellites fetched: {len(all_satellites)}")
        print("[DB] Removing duplicates based on NORAD_CAT_ID...")
        
        # Remove duplicates based on NORAD_CAT_ID
        seen_ids = set()
        unique_satellites = []
        duplicate_count = 0
        
        for sat in all_satellites:
            sat_id = sat.get('NORAD_CAT_ID')
            if sat_id and sat_id not in seen_ids:
                seen_ids.add(sat_id)
                unique_satellites.append({
                    'norad_id': str(sat_id),
                    'name': sat.get('OBJECT_NAME', '').strip(),
                    'tle_line1': sat.get('TLE_LINE1', ''),
                    'tle_line2': sat.get('TLE_LINE2', '')
                })
            else:
                duplicate_count += 1
        
        print(f"[DB] Removed {duplicate_count} duplicates")
        print(f"[DB] Final unique satellites: {len(unique_satellites)}")

        SATELLITE_DB = unique_satellites
        DB_LAST_UPDATED = datetime.now()
        DB_SOURCE = 'remote'

        print(f"[DB] ✓ Database successfully loaded at {DB_LAST_UPDATED}")
        print(f"[DB] Database contains {len(SATELLITE_DB)} unique satellites")

        # Print some sample satellites for verification
        if SATELLITE_DB:
            print("[DB] Sample satellites:")
            for i, sat in enumerate(SATELLITE_DB[:5]):
                print(f"[DB]   {i+1}. {sat['name']} (ID: {sat['norad_id']})")
        
    except Exception as e:
        print(f"[DB] ✗ Failed to load satellite database: {e}")
        import traceback
        print(f"[DB] Full traceback: {traceback.format_exc()}")
        
        # Keep existing database if update fails
        if not SATELLITE_DB:
            print("[DB] No existing database, loading fallback satellites...")
            # If no database exists, load a minimal set of popular satellites
            SATELLITE_DB = [
                {'norad_id': '25544', 'name': 'ISS (ZARYA)', 'tle_line1': '', 'tle_line2': ''},
                {'norad_id': '20580', 'name': 'HST', 'tle_line1': '', 'tle_line2': ''},
                {'norad_id': '28654', 'name': 'NOAA 18', 'tle_line1': '', 'tle_line2': ''},
                {'norad_id': '33591', 'name': 'NOAA 19', 'tle_line1': '', 'tle_line2': ''},
            ]
            print(f"[DB] Using fallback database with {len(SATELLITE_DB)} satellites")
        else:
            print(f"[DB] Keeping existing database with {len(SATELLITE_DB)} satellites")
    finally:
        DB_LOADING = False
        print("[DB] Database loading flag cleared")

def update_database_if_needed():
    """Update database if it's older than the update interval"""
    global DB_LAST_UPDATED
    
    print(f"[DB] Checking if database update is needed...")
    print(f"[DB] Last updated: {DB_LAST_UPDATED}")
    print(f"[DB] Current time: {datetime.now()}")
    
    if not DB_LAST_UPDATED:
        print("[DB] No last update time, update needed")
        needs_update = True
    else:
        time_since_update = datetime.now() - DB_LAST_UPDATED
        print(f"[DB] Time since last update: {time_since_update}")
        needs_update = time_since_update > DB_UPDATE_INTERVAL
    
    # If database source is a local file, don't auto-update from remote
    if needs_update and DB_SOURCE != 'file':
        print("[DB] Database update needed, running in background...")
        # Run in background thread to avoid blocking
        thread = threading.Thread(target=load_satellite_database)
        thread.daemon = True
        thread.start()
    else:
        print("[DB] Database is up to date")

def search_satellites_local(query, limit=20):
    """Search satellites in the local database"""
    # Allow single-character queries; return empty only if truly empty/None
    if not query:
        return []
    
    print(f"[SEARCH] Searching for: '{query}' in {len(SATELLITE_DB)} satellites")
    query_lower = query.lower()
    results = []
    
    # Add popular satellite aliases for better matching
    aliases = {
        'iss': ['ZARYA', 'ISS'],
        'international': ['ZARYA', 'ISS'],
        'hubble': ['HST'],
        'space': ['ZARYA', 'HST'],
        'station': ['ZARYA', 'ISS']
    }
    
    # Check aliases first
    alias_matches = 0
    for alias, names in aliases.items():
        if alias in query_lower:
            for sat in SATELLITE_DB:
                for name in names:
                    if name.lower() in sat['name'].lower() and sat not in results:
                        results.append(sat)
                        alias_matches += 1
    
    print(f"[SEARCH] Found {alias_matches} alias matches")
    
    # Exact matches
    exact_matches = 0
    for sat in SATELLITE_DB:
        if sat['name'].lower() == query_lower and sat not in results:
            results.append(sat)
            exact_matches += 1
    
    print(f"[SEARCH] Found {exact_matches} exact matches")
    
    # Starts with matches
    starts_with_matches = 0
    for sat in SATELLITE_DB:
        if sat['name'].lower().startswith(query_lower) and sat not in results:
            results.append(sat)
            starts_with_matches += 1
    
    print(f"[SEARCH] Found {starts_with_matches} starts-with matches")
    
    # Word boundary matches
    word_matches = 0
    for sat in SATELLITE_DB:
        words = sat['name'].lower().split()
        if any(word.startswith(query_lower) for word in words) and sat not in results:
            results.append(sat)
            word_matches += 1
    
    print(f"[SEARCH] Found {word_matches} word-boundary matches")
    
    # Contains matches
    contains_matches = 0
    for sat in SATELLITE_DB:
        if query_lower in sat['name'].lower() and sat not in results:
            results.append(sat)
            contains_matches += 1
    
    print(f"[SEARCH] Found {contains_matches} contains matches")
    print(f"[SEARCH] Total matches before limit: {len(results)}")
    
    limited_results = results[:limit]
    print(f"[SEARCH] Returning {len(limited_results)} results")
    
    return limited_results

# ------------------------------------------------------------------
# 1.  Physical and geometric constants (Copied from your script)
# ------------------------------------------------------------------
EARTH_MU = 398600.4418
EARTH_ROTATION_RATE = 7.2921150e-5

# WGS84 ellipsoid constants (km)
WGS84_A = 6378.137
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)

# ------------------------------------------------------------------
# 2.  Dynamics and propagation (Copied from your script)
# ------------------------------------------------------------------
def calculate_acceleration(_, state):
    r = state[0:3]
    r_norm = np.linalg.norm(r)
    a_gravity = -EARTH_MU * r / r_norm**3
    return np.concatenate([state[3:6], a_gravity])

def propagate_orbit(initial_position, initial_velocity, duration, step_size=60):
    initial_state = np.concatenate([initial_position, initial_velocity])
    t_eval = np.arange(0, duration + step_size, step_size)
    sol = solve_ivp(
        calculate_acceleration,
        t_span=(0, duration),
        y0=initial_state,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-8,
        atol=1e-8
    )
    return sol.t, sol.y[0:3].T

def propagate_orbit_sgp4_from_now(sat: Satrec, duration_seconds: float, step_size: int = 300, base_time=None):
    """Propagate using SGP4 starting at base_time (UTC) for the given duration.
    If base_time is None, uses current UTC time.
    Returns (t_seconds_array, positions_km Nx3).
    """
    if duration_seconds <= 0:
        return np.array([0.0]), np.zeros((1, 3))

    # Build time grid from t=0 (now) to t=duration
    times = np.arange(0, duration_seconds + step_size, step_size, dtype=float)
    positions = []

    now = base_time or datetime.utcnow()
    for t in times:
        dt = now + timedelta(seconds=float(t))
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond * 1e-6)
        err, r_eci, _v_eci = sat.sgp4(jd, fr)
        if err != 0:
            raise ValueError(f"SGP4 error {err} at +{t:.0f}s from now (check TLE freshness)")
        positions.append(r_eci)

    return times, np.array(positions)

# ------------------------------------------------------------------
# 3.  Utility conversions (Copied from your script)
# ------------------------------------------------------------------
def gmst_from_datetime(dt: datetime) -> float:
    """Compute Greenwich Mean Sidereal Time (radians) for a UTC datetime.
    Based on IAU 1982/2000 conventions; sufficient for visualization.
    """
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond * 1e-6)
    JD = jd + fr
    T = (JD - 2451545.0) / 36525.0
    # GMST in seconds (Vallado 2006)
    gmst_sec = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * T + 0.093104 * T**2 - 6.2e-6 * T**3
    gmst_rad = (gmst_sec % 86400.0) * (2.0 * np.pi / 86400.0)
    return gmst_rad

def teme_to_ecef(r_teme: np.ndarray, dt: datetime) -> np.ndarray:
    """Approximate TEME -> ECEF by rotation about Z using GMST (ignores nutation/polar motion)."""
    theta = gmst_from_datetime(dt)
    c, s = np.cos(theta), np.sin(theta)
    x, y, z = r_teme
    x_e = c * x + s * y
    y_e = -s * x + c * y
    return np.array([x_e, y_e, z])

def ecef_to_geodetic(r_ecef: np.ndarray):
    """Convert ECEF (km) to geodetic lat (deg), lon (deg). Altitude not returned."""
    x, y, z = r_ecef
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - WGS84_E2))
    # Iterate once or twice for improved accuracy
    for _ in range(2):
        sin_lat = np.sin(lat)
        N = WGS84_A / np.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        lat = np.arctan2(z + WGS84_E2 * N * sin_lat, p)
    lat_deg = np.degrees(lat)
    lon_deg = ((np.degrees(lon) + 180.0) % 360.0) - 180.0
    return lat_deg, lon_deg

def teme_positions_to_geodetic(positions: np.ndarray, datetimes):
    """Convert a sequence of TEME positions (km) at given datetimes to geodetic lat/lon arrays."""
    lats, lons = [], []
    for r_teme, dt in zip(positions, datetimes):
        r_ecef = teme_to_ecef(r_teme, dt)
        lat, lon = ecef_to_geodetic(r_ecef)
        lats.append(lat)
        lons.append(lon)
    return np.array(lats), np.array(lons)

def parse_iso_utc(value: str):
    """Parse ISO8601 UTC string like '2025-09-02T09:59:38Z' (optionally with fractional seconds).
    Returns naive datetime (interpreted as UTC) or None on failure.
    """
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    if s.endswith('Z'):
        s = s[:-1]
    try:
        # datetime.fromisoformat supports 'YYYY-MM-DDTHH:MM:SS[.ffffff]'
        return datetime.fromisoformat(s)
    except Exception:
        return None

def parse_tle_epoch_dt(line1: str):
    """Parse epoch from TLE line 1 as a naive UTC datetime.
    Per TLE format: epoch year (2-digit) at cols 19-20, epoch day (with fraction) at cols 21-32 (1-based).
    """
    try:
        year_2 = int(line1[18:20])
        doy = float(line1[20:32])
        year = 2000 + year_2 if year_2 < 57 else 1900 + year_2
        jan1 = datetime(year, 1, 1)
        return jan1 + timedelta(days=doy - 1.0)
    except Exception:
        return None

def tle_age_hours_from_line1(line1: str, now: datetime | None = None) -> float | None:
    """Return TLE age in hours from its line1 epoch to 'now' (UTC). None if epoch can't be parsed."""
    epoch = parse_tle_epoch_dt(line1)
    if epoch is None:
        return None
    now = now or datetime.utcnow()
    return (now - epoch).total_seconds() / 3600.0

def calculate_azimuth(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlon = lon2 - lon1
    y = np.sin(dlon) * np.cos(lat2)
    x = (np.cos(lat1) * np.sin(lat2) -
         np.sin(lat1) * np.cos(lat2) * np.cos(dlon))
    az = np.degrees(np.arctan2(y, x)) % 360
    return az

# ------------------------------------------------------------------
# 4.  API Endpoint for Propagation
# ------------------------------------------------------------------
@app.route('/api/propagate', methods=['POST'])
def propagate_tle():
    """
    API endpoint to receive TLE and duration, propagate orbit, and return track data.
    """
    data = request.get_json()
    if not data or 'line1' not in data or 'line2' not in data:
        return jsonify({'error': 'Invalid TLE data provided.'}), 400

    line1 = data['line1'].strip()
    line2 = data['line2'].strip()
    
    # MODIFIED: Get duration from the request, default to 24 hours if not provided.
    # We get it in hours from the frontend.
    duration_hours = data.get('duration', 24)

    # Basic validation for the duration to prevent server overload
    try:
        duration_hours = float(duration_hours)
        if not 0 < duration_hours <= 168: # Limit to 1 hour to 1 week (168 hours)
             raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Duration must be a number between 1 and 168 hours.'}), 400

    try:
        # Real-time propagation using SGP4; pin start to TLE epoch if stale
        sat = Satrec.twoline2rv(line1, line2)
        duration_seconds = float(duration_hours) * 3600.0
        step_size = 300  # 5-minute steps
        # Allow client to pin start time for verification/testing
        client_start = parse_iso_utc(data.get('start_utc')) if isinstance(data, dict) else None
        tle_epoch = parse_tle_epoch_dt(line1)
        tle_age_hr = None
        if tle_epoch is not None:
            tle_age_hr = (datetime.utcnow() - tle_epoch).total_seconds() / 3600.0
        # If TLE is stale and client didn't request a specific start, anchor around the TLE epoch
        if client_start is None and tle_age_hr is not None and tle_age_hr > STALE_TLE_THRESHOLD_HOURS:
            start_dt = tle_epoch
        else:
            start_dt = client_start or datetime.utcnow()
        t, pos = propagate_orbit_sgp4_from_now(sat, duration_seconds, step_size, base_time=start_dt)
        dts = [start_dt + timedelta(seconds=float(ts)) for ts in t]
        lat, lon = teme_positions_to_geodetic(pos, dts)

        az = np.array([
            calculate_azimuth(lat[i], lon[i], lat[i+1], lon[i+1])
            for i in range(len(lat) - 1)
        ] + [0])

        response_data = {
            'times_hr': (t / 3600).tolist(),
            'latitudes': lat.tolist(),
            'longitudes': lon.tolist(),
            'azimuths': az.tolist(),
            'duration_hr': duration_seconds / 3600,  # Send the actual used duration back
            'start_utc_iso': start_dt.replace(microsecond=0).isoformat() + 'Z',
            'end_utc_iso': (start_dt + timedelta(seconds=duration_seconds)).replace(microsecond=0).isoformat() + 'Z',
            'start_lat': float(lat[0]),
            'start_lon': float(lon[0]),
            'tle_epoch_iso': tle_epoch.replace(microsecond=0).isoformat() + 'Z' if tle_epoch else None,
            'tle_age_hours': round(tle_age_hr, 3) if tle_age_hr is not None else None,
            'anchored_to_tle_epoch': bool(client_start is None and tle_age_hr is not None and tle_age_hr > STALE_TLE_THRESHOLD_HOURS),
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------------------------------------------------------
# 3.5  TLE Fetching using Local Database and CelesTrak
# ------------------------------------------------------------------

def get_tle_by_name(satellite_name):
    """Get TLE data for a satellite by name using local database first"""
    try:
        print(f"Fetching TLE for satellite: '{satellite_name}'")
        
        # First, try to find in local database
        satellite_name_lower = satellite_name.lower()
        
        # Check for exact match first
        for sat in SATELLITE_DB:
            if sat['name'].lower() == satellite_name_lower:
                if sat['tle_line1'] and sat['tle_line2']:
                    # If TLE is stale, try to refresh from CelesTrak by catalog number
                    try:
                        epoch = parse_tle_epoch_dt(sat['tle_line1'])
                    except Exception:
                        epoch = None
                    if epoch is not None:
                        age_hours = (datetime.utcnow() - epoch).total_seconds() / 3600.0
                    else:
                        age_hours = 1e9
                    if age_hours > 48 and sat.get('norad_id'):
                        try:
                            response = requests.get(
                                "https://celestrak.org/NORAD/elements/gp.php",
                                params={'CATNR': sat['norad_id'], 'FORMAT': 'tle'},
                                timeout=10
                            )
                            if response.status_code == 200 and response.text.strip():
                                lines = response.text.strip().split('\n')
                                if len(lines) >= 3:
                                    sat['tle_line1'] = lines[1].strip()
                                    sat['tle_line2'] = lines[2].strip()
                                    return {
                                        'name': lines[0].strip(),
                                        'line1': sat['tle_line1'],
                                        'line2': sat['tle_line2']
                                    }
                        except Exception as e:
                            print(f"TLE refresh failed for {sat.get('norad_id')}: {e}")
                    # Return existing (possibly fresh) TLE
                    return {
                        'name': sat['name'],
                        'line1': sat['tle_line1'],
                        'line2': sat['tle_line2']
                    }
                # If we have the satellite but no TLE data, fetch it
                try:
                    print(f"Fetching TLE for known satellite ID: {sat['norad_id']}")
                    response = requests.get(
                        "https://celestrak.org/NORAD/elements/gp.php",
                        params={'CATNR': sat['norad_id'], 'FORMAT': 'tle'},
                        timeout=10
                    )
                    if response.status_code == 200 and response.text.strip():
                        lines = response.text.strip().split('\n')
                        if len(lines) >= 3:
                            # Update our cache
                            sat['tle_line1'] = lines[1]
                            sat['tle_line2'] = lines[2]
                            return {
                                'name': lines[0].strip(),
                                'line1': lines[1].strip(),
                                'line2': lines[2].strip()
                            }
                except Exception as e:
                    print(f"Error fetching TLE by catalog number: {e}")
        
        # Try partial match in local database
        best_match = None
        for sat in SATELLITE_DB:
            name_lower = sat['name'].lower()
            if satellite_name_lower in name_lower:
                if not best_match or name_lower.startswith(satellite_name_lower):
                    best_match = sat
        
        if best_match:
            try:
                print(f"Found partial match: {best_match['name']}, fetching TLE...")
                response = requests.get(
                    "https://celestrak.org/NORAD/elements/gp.php",
                    params={'CATNR': best_match['norad_id'], 'FORMAT': 'tle'},
                    timeout=10
                )
                if response.status_code == 200 and response.text.strip():
                    lines = response.text.strip().split('\n')
                    if len(lines) >= 3:
                        # Update our cache
                        best_match['tle_line1'] = lines[1]
                        best_match['tle_line2'] = lines[2]
                        return {
                            'name': lines[0].strip(),
                            'line1': lines[1].strip(),
                            'line2': lines[2].strip()
                        }
            except Exception as e:
                print(f"Error fetching TLE for best match: {e}")
        
        # Common satellite name mappings
        common_names = {
            'iss': 'ZARYA',
            'international space station': 'ZARYA',
            'hubble': 'HST',
            'hubble space telescope': 'HST'
        }
        
        mapped_name = common_names.get(satellite_name_lower)
        if mapped_name:
            try:
                print(f"Trying mapped name: {mapped_name}")
                response = requests.get(
                    "https://celestrak.org/NORAD/elements/gp.php",
                    params={'NAME': mapped_name, 'FORMAT': 'tle'},
                    timeout=10
                )
                if response.status_code == 200 and response.text.strip():
                    lines = response.text.strip().split('\n')
                    if len(lines) >= 3:
                        return {
                            'name': lines[0].strip(),
                            'line1': lines[1].strip(),
                            'line2': lines[2].strip()
                        }
            except Exception as e:
                print(f"Error fetching with mapped name: {e}")
        
        # Last resort: try direct name search with CelesTrak
        try:
            print(f"Trying direct name search with CelesTrak...")
            response = requests.get(
                "https://celestrak.org/NORAD/elements/gp.php",
                params={'NAME': satellite_name, 'FORMAT': 'tle'},
                timeout=10
            )
            if response.status_code == 200 and response.text.strip():
                lines = response.text.strip().split('\n')
                if len(lines) >= 3:
                    return {
                        'name': lines[0].strip(),
                        'line1': lines[1].strip(),
                        'line2': lines[2].strip()
                    }
        except Exception as e:
            print(f"Error in direct name search: {e}")
        
    except Exception as e:
        print(f"Error in get_tle_by_name: {e}")
    
    print(f"Could not find TLE data for: '{satellite_name}'")
    return None

# ------------------------------------------------------------------

@app.route('/api/search-satellites', methods=['GET'])
def search_satellites_endpoint():
    """API endpoint to search for satellites by name using local database.
    Supports:
      - q: search query (min 1 char)
      - all: if truthy and q empty, return a default list
      - limit: max number of items to return (default 20)
    """
    raw_query = request.args.get('q', '')
    query = raw_query.strip()
    all_flag = request.args.get('all', '').lower() in ('1', 'true', 'yes')
    try:
        limit = int(request.args.get('limit', 20))
    except Exception:
        limit = 20
    limit = max(1, min(limit, 200))  # clamp between 1 and 200

    print(f"[API] Search request received: q='{query}', all={all_flag}, limit={limit}")

    # Update database if needed (runs in background)
    update_database_if_needed()

    # If no query provided
    if not query:
        if all_flag:
            # Return default list sorted by name
            try:
                sorted_db = sorted(SATELLITE_DB, key=lambda s: s.get('name', ''))
                results = sorted_db[:limit]
                print(f"[API] Returning {len(results)} 'all' results")
                return jsonify({'satellites': results})
            except Exception as e:
                print(f"[API] Error building 'all' list: {e}")
                return jsonify({'satellites': []})
        else:
            print("[API] Empty query and 'all' not set; returning empty list")
            return jsonify({'satellites': []})

    try:
        # Search local database for fast results (allow 1+ char)
        results = search_satellites_local(query, limit=limit)
        print(f"[API] Returning {len(results)} results")
        return jsonify({'satellites': results})
    except Exception as e:
        print(f"[API] Error in search endpoint: {e}")
        import traceback
        print(f"[API] Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-tle', methods=['POST'])
def get_tle_endpoint():
    """API endpoint to get TLE data for a satellite by name"""
    data = request.get_json()
    if not data or 'satellite_name' not in data:
        return jsonify({'error': 'Satellite name is required.'}), 400
    
    satellite_name = data['satellite_name'].strip()
    
    try:
        tle_data = get_tle_by_name(satellite_name)
        if tle_data:
            return jsonify(tle_data)
        else:
            return jsonify({'error': f'Satellite "{satellite_name}" not found.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/propagate-by-name', methods=['POST'])
def propagate_by_name():
    """API endpoint to propagate orbit by satellite name"""
    data = request.get_json()
    if not data or 'satellite_name' not in data:
        return jsonify({'error': 'Satellite name is required.'}), 400
    
    satellite_name = data['satellite_name'].strip()
    duration_hours = data.get('duration', 24)
    
    # Validate duration
    try:
        duration_hours = float(duration_hours)
        if not 0 < duration_hours <= 168:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Duration must be a number between 1 and 168 hours.'}), 400
    
    try:
        # Get TLE data
        tle_data = get_tle_by_name(satellite_name)
        if not tle_data:
            return jsonify({'error': f'Satellite "{satellite_name}" not found.'}), 404

        # Real-time propagation using SGP4; pin start to TLE epoch if stale
        line1 = tle_data['line1']
        line2 = tle_data['line2']
        sat = Satrec.twoline2rv(line1, line2)
        duration_seconds = float(duration_hours) * 3600.0
        step_size = 300
        # Allow client to pin start time for verification/testing
        client_start = parse_iso_utc(data.get('start_utc')) if isinstance(data, dict) else None
        tle_epoch = parse_tle_epoch_dt(line1)
        tle_age_hr = None
        if tle_epoch is not None:
            tle_age_hr = (datetime.utcnow() - tle_epoch).total_seconds() / 3600.0
        if client_start is None and tle_age_hr is not None and tle_age_hr > STALE_TLE_THRESHOLD_HOURS:
            start_dt = tle_epoch
        else:
            start_dt = client_start or datetime.utcnow()
        t, pos = propagate_orbit_sgp4_from_now(sat, duration_seconds, step_size, base_time=start_dt)
        dts = [start_dt + timedelta(seconds=float(ts)) for ts in t]
        lat, lon = teme_positions_to_geodetic(pos, dts)

        az = np.array([
            calculate_azimuth(lat[i], lon[i], lat[i+1], lon[i+1])
            for i in range(len(lat) - 1)
        ] + [0])

        response_data = {
            'satellite_name': tle_data['name'],
            'times_hr': (t / 3600).tolist(),
            'latitudes': lat.tolist(),
            'longitudes': lon.tolist(),
            'azimuths': az.tolist(),
            'duration_hr': duration_seconds / 3600,
            'start_utc_iso': start_dt.replace(microsecond=0).isoformat() + 'Z',
            'end_utc_iso': (start_dt + timedelta(seconds=duration_seconds)).replace(microsecond=0).isoformat() + 'Z',
            'start_lat': float(lat[0]),
            'start_lon': float(lon[0]),
            'tle_epoch_iso': tle_epoch.replace(microsecond=0).isoformat() + 'Z' if tle_epoch else None,
            'tle_age_hours': round(tle_age_hr, 3) if tle_age_hr is not None else None,
            'anchored_to_tle_epoch': bool(client_start is None and tle_age_hr is not None and tle_age_hr > STALE_TLE_THRESHOLD_HOURS),
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def ensure_database_loaded():
    """Ensure the database is loaded before handling requests"""
    global SATELLITE_DB, DB_LOADING
    
    if not SATELLITE_DB and not DB_LOADING:
        print("[DB] Database not loaded, loading now...")
        load_satellite_database()
    elif DB_LOADING:
        print("[DB] Database loading in progress...")
        # Wait a bit for loading to complete
        import time
        time.sleep(1)

@app.before_request
def before_request():
    """Ensure database is loaded before handling any request"""
    ensure_database_loaded()

if __name__ == '__main__':
    print("[MAIN] Starting Flask app...")
    # Run the app in debug mode, which helps with development  
    app.run(debug=True, port=5000)