# Satellite Ground Track Dashboard

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb?logo=react&logoColor=white)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A full-stack web application for real-time visualization of satellite ground tracks using TLE (Two-Line Element) data. Track satellites in orbit with beautiful azimuth-colored paths, real-time propagation, and interactive maps.

![Satellite Dashboard Preview](https://via.placeholder.com/800x400/1a1a2e/ffffff?text=Satellite+Ground+Track+Visualization)

## Features

- **Smart Satellite Search**: Search satellites by name with autocomplete from CelesTrak database
- 📡 **Direct TLE Input**: Manual TLE entry for custom satellite tracking
- 🌍 **Interactive World Map**: Real-time ground track visualization with Plotly.js
- 🎨 **Azimuth Coloring**: Color-coded tracks showing satellite direction changes
- ⏰ **Real-time Propagation**: SGP4 orbital mechanics for accurate positioning
- 📊 **Orbit Metadata**: Display TLE epoch, age, and propagation timeframes
- 🔄 **Auto-refresh TLEs**: Automatic handling of stale orbital data
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile devices

## Architecture

```
 satellite-dashboard/
├──  backend/                 # Flask API Server
│   ├── app.py                  # Main Flask application
│   ├── requirements.txt        # Python dependencies
│   └── data/
│       └── tle_catalog.txt     # Optional local TLE catalog
├──  frontend/                # React Web Application
│   ├── package.json           # Node.js dependencies
│   ├── public/                # Static assets
│   └── src/                   # React components & logic
│       ├── App.js             # Main application component
│       ├── components/        # Reusable UI components
│       └── utils/             # Helper functions
└──  README.md               # Project documentation
```

##  Quick Start

### Prerequisites

- **Python 3.10+** (recommended 3.11)
- **Node.js 18+** and npm
- **Git** for version control

### Clone the Repository

```bash
git clone https://github.com/OorjitSethi/satellite-dashboard.git
cd satellite-dashboard
```

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask development server
python app.py
```

 **Backend server running at:** http://127.0.0.1:5000

### Frontend Setup

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

 **Frontend application running at:** http://localhost:3000

### Usage

1. **Open your browser** and navigate to http://localhost:3000
2. **Search for satellites** using the search bar (try "ISS", "Hubble", "Starlink")
3. **Select a satellite** from the dropdown results
4. **Click "Track Satellite"** to visualize its ground track
5. **Explore the map** with zoom, pan, and hover interactions

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Optional: Path to local TLE catalog file
TLE_FILE=data/tle_catalog.txt

# Optional: Custom CelesTrak groups to fetch
CELESTRAK_GROUPS=stations,visual,active-geo

# Optional: Flask configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### Local TLE Catalog

For offline usage or custom satellites, create `backend/data/tle_catalog.txt`:

```
ISS (ZARYA)
1 25544U 98067A   24001.50000000  .00002182  00000-0  40768-4 0  9992
2 25544  51.6461 339.7939 0001220  92.8340 267.3124 15.49309239123456
HUBBLE SPACE TELESCOPE
1 20580U 90037B   24001.50000000  .00000294  00000-0  12345-4 0  9993
2 20580  28.4691 123.4567 0002640 123.4567 236.7890 15.09234567234567
```

## API Reference

### Core Endpoints

#### Search Satellites
```http
GET /api/search-satellites?q={query}&limit={limit}
```

**Parameters:**
- `q` (string): Search query (satellite name)
- `limit` (integer): Maximum results to return (default: 20)

**Response:**
```json
[
  {
    "name": "ISS (ZARYA)",
    "norad_id": "25544",
    "line1": "1 25544U 98067A   24001.50000000...",
    "line2": "2 25544  51.6461 339.7939 0001220..."
  }
]
```

#### Get TLE Data
```http
POST /api/get-tle
Content-Type: application/json

{
  "satellite_name": "ISS (ZARYA)"
}
```

#### Propagate Orbit
```http
POST /api/propagate-by-name
Content-Type: application/json

{
  "satellite_name": "ISS (ZARYA)",
  "duration": 90
}
```

**Response:**
```json
{
  "times_hr": [0, 0.1, 0.2, ...],
  "latitudes": [51.2, 48.9, 46.1, ...],
  "longitudes": [-121.3, -118.7, -115.9, ...],
  "azimuths": [45.2, 47.8, 50.1, ...],
  "start_utc_iso": "2024-01-01T12:00:00Z",
  "end_utc_iso": "2024-01-01T13:30:00Z",
  "tle_epoch_iso": "2024-01-01T12:00:00Z",
  "tle_age_hours": 2.5,
  "anchored_to_tle_epoch": true
}
```

##  Troubleshooting

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
|  Long first request | Satellite database fetching from CelesTrak | Wait ~10-30 seconds; subsequent requests are cached |
|  500 error on propagation | Outdated/invalid TLE data | Refresh TLE data via `/api/get-tle` endpoint |
|  Track appears stationary | Very old TLE or geostationary satellite | Increase duration or verify TLE freshness |
|  Frontend can't connect | Backend not running or wrong port | Ensure backend is running on port 5000 |
|  Module import errors | Missing Python dependencies | Run `pip install -r requirements.txt` |

### Performance Tips

-  **First Launch**: Initial satellite database fetch may take 10-30 seconds
-  **Caching**: Subsequent searches are fast due to local caching
-  **TLE Freshness**: Refresh TLEs every 24-48 hours for accuracy
-  **Local Catalog**: Use `TLE_FILE` environment variable for offline mode

##  Roadmap

### 🔄 Current Development
- [ ] Real-time satellite position updates
- [ ] Multiple satellite tracking simultaneously
- [ ] 3D visualization mode

###  Future Features
- [ ] Satellite pass predictions for ground observers
- [ ] Altitude profile visualization
- [ ] Ground track animation with time controls
- [ ] Export functionality (KML, GeoJSON)
- [ ] Docker containerization
- [ ] Database persistence for TLE caching
- [ ] User accounts and favorite satellites
- [ ] Mobile app (React Native)

###  Development Improvements
- [ ] Unit tests (pytest + Jest)
- [ ] Integration tests
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Code coverage reports
- [ ] Performance monitoring
- [ ] Error tracking (Sentry)

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **JavaScript**: Use Prettier, ESLint configuration
- **Commits**: Use conventional commit messages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **[CelesTrak](https://celestrak.com/)** for providing satellite TLE data
- **[SGP4](https://pypi.org/project/sgp4/)** library for orbital mechanics
- **[Plotly.js](https://plotly.com/javascript/)** for interactive visualizations
- **[Flask](https://flask.palletsprojects.com/)** for the backend framework
- **[React](https://reactjs.org/)** for the frontend framework

##  Support

- 📧 **Email**: [Your Email Here]
- 🐛 **Issues**: [GitHub Issues](https://github.com/OorjitSethi/satellite-dashboard/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/OorjitSethi/satellite-dashboard/discussions)

---

⭐ **Star this repository if you found it helpful!**

🚀 **Built with ❤️ by [Oorjit Sethi](https://github.com/OorjitSethi)**
