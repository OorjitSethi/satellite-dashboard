Local TLE catalog

- Put a text file named `tle_catalog.txt` in this folder, or set environment variable `TLE_FILE` to an absolute path.
- Format: 3-line sets per satellite (no blank lines required, they are ignored):

  NAME OF SATELLITE
  1 25544U 98067A   24238.50967593  .00019045  00000-0  33148-3 0  9991
  2 25544  51.6411  24.8010 0005051 130.6302  38.3036 15.50342234568964

- The loader extracts the NORAD_CAT_ID from columns 3-7 of line1.
- If the file exists and parses, the backend will use only this data and skip remote fetches.
- To refresh from file, restart the backend process.
