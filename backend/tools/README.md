TLE Catalog Builder

This utility fetches TLEs from CelesTrak groups and writes a single 3-line-per-satellite file that the backend can load.

- Default output: ../data/tle_catalog.txt (used automatically by the backend if present)
- Uses the same API (CelesTrak gp.php) as the app.

Usage (from this folder):

  python3 build_tle_catalog.py

Options:
- Choose a custom path:

  python3 build_tle_catalog.py --output /absolute/path/tle_catalog.txt

- Choose groups (defaults included):

  python3 build_tle_catalog.py --groups active stations weather

- Respect env var:

  TLE_FILE=/absolute/path/tle_catalog.txt python3 build_tle_catalog.py

Notes:
- The script de-duplicates by NORAD_CAT_ID and keeps the first seen entry.
- A short delay between group requests is used to be polite to CelesTrak.
