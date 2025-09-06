import React, { useState } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import './App.css';
import DurationInput from './DurationInput.js'; // <-- NEW: Import the custom component

function App() {
  // --- STATE MANAGEMENT ---
  const [satelliteName, setSatelliteName] = useState('ISS');
  const [tleLine1, setTleLine1] = useState('1 25544U 98067A   23330.34210087  .00006325  00000+0  12143-3 0  9995');
  const [tleLine2, setTleLine2] = useState('2 25544  51.6413 290.4937 0007278  62.5839  91.2415 15.49493955398239');
  const [duration, setDuration] = useState(24);
  const [inputMode, setInputMode] = useState('name'); // 'name' or 'tle'
  
  // Autocomplete state
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const [searchLoading, setSearchLoading] = useState(false);

  const [plotData, setPlotData] = useState(null);
  const [plotLayout, setPlotLayout] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [meta, setMeta] = useState(null); // start/end metadata
  const [error, setError] = useState('');

  // --- SATELLITE SEARCH HANDLER ---
  const searchSatellites = async (query, { forceAll = false } = {}) => {
    // If no query and not forcing the full list, show nothing
    if (!query && !forceAll) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setSearchLoading(true);
    try {
      let url = 'http://127.0.0.1:5000/api/search-satellites';
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (forceAll && !query) params.set('all', '1');
      params.set('limit', '50');
      url += `?${params.toString()}`;

      const response = await axios.get(url);
      setSuggestions(response.data.satellites || []);
      setShowSuggestions(true);
      setActiveSuggestion(-1);
    } catch (err) {
      console.error('Error searching satellites:', err);
      setSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setSearchLoading(false);
    }
  };

  // Debounced search function - faster since we're using local database
  const debouncedSearch = React.useCallback(
    React.useMemo(() => {
      let timeoutId;
      return (query) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => searchSatellites(query), 100); // Reduced from 300ms to 100ms
      };
    }, []),
    []
  );

  // --- SATELLITE NAME INPUT HANDLERS ---
  const handleSatelliteNameChange = (e) => {
    const value = e.target.value;
    setSatelliteName(value);
    // Allow 1+ char queries; if empty, we keep dropdown hidden unless explicitly requested on focus
    debouncedSearch(value);
  };

  const handleSuggestionClick = (suggestion) => {
    setSatelliteName(suggestion.name);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestion(prev => 
        prev < suggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestion(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeSuggestion >= 0) {
        handleSuggestionClick(suggestions[activeSuggestion]);
      } else if (suggestions.length > 0) {
        // If no active selection, choose the first
        handleSuggestionClick(suggestions[0]);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setActiveSuggestion(-1);
    }
  };

  const handleInputFocus = () => {
    // Show all options when focused and no text typed
    if (!satelliteName) {
      searchSatellites('', { forceAll: true });
    } else {
      // Trigger search for current value
      searchSatellites(satelliteName);
    }
  };

  // --- API CALL HANDLER ---
  const handleGenerateTrack = async () => {
    setIsLoading(true);
    setError('');
  setPlotData(null);
  setMeta(null);

    try {
      let apiUrl, requestData;
      
    if (inputMode === 'name') {
        // Use satellite name endpoint
        apiUrl = 'http://127.0.0.1:5000/api/propagate-by-name';
        requestData = {
          satellite_name: satelliteName,
  duration: duration,
        };
      } else {
        // Use TLE endpoint
        apiUrl = 'http://127.0.0.1:5000/api/propagate';
        requestData = {
          line1: tleLine1,
          line2: tleLine2,
  duration: duration,
        };
      }
      
      const response = await axios.post(apiUrl, requestData);

  const data = response.data;
      
      const hoverText = data.times_hr.map((t, i) => 
        `t = ${t.toFixed(2)} h<br>` +
        `Lat: ${data.latitudes[i].toFixed(2)}°<br>` +
        `Lon: ${data.longitudes[i].toFixed(2)}°<br>` +
        `Az: ${data.azimuths[i].toFixed(2)}°`
      );

      // --- PLOTLY DATA & LAYOUT ---
      const trace = {
        lat: data.latitudes,
        lon: data.longitudes,
        mode: 'lines+markers',
        type: 'scattergeo',
        line: { width: 2, color: 'rgba(255, 255, 255, 0.7)' },
        marker: {
          size: 4,
          color: data.azimuths,
          colorscale: [
            [0, '#537fe7'], [0.25, 'green'],
            [0.5, 'red'], [0.75, 'purple'], [1, '#537fe7']
          ],
          cmin: 0,
          cmax: 360,
          colorbar: {
            title: { text: 'Azimuth (°)', font: { color: '#c0c0c0' } },
            titleside: 'right',
            tickvals: [0, 90, 180, 270, 360],
            ticktext: ['N', 'E', 'S', 'W', 'N'],
            tickfont: { color: '#c0c0c0' }
          },
        },
        text: hoverText,
        hoverinfo: 'text',
      };
      // Start marker (now)
      const startMarker = {
        lat: [data.latitudes[0]],
        lon: [data.longitudes[0]],
        mode: 'markers+text',
        type: 'scattergeo',
        marker: { size: 12, color: '#2ecc71', symbol: 'star' },
  text: [data.anchored_to_tle_epoch ? 'START (TLE epoch)' : 'START'],
        textposition: 'top center',
        hoverinfo: 'skip'
      };
      // End marker (end of duration)
      const lastIdx = data.latitudes.length - 1;
      const endMarker = {
        lat: [data.latitudes[lastIdx]],
        lon: [data.longitudes[lastIdx]],
        mode: 'markers+text',
        type: 'scattergeo',
        marker: { size: 12, color: '#e74c3c', symbol: 'x' },
        text: ['END'],
        textposition: 'bottom center',
        hoverinfo: 'skip'
      };

      // Current position marker (duplicates start for clarity, with distinct styling)
      const nowMarker = {
        lat: [data.latitudes[0]],
        lon: [data.longitudes[0]],
        mode: 'markers',
        type: 'scattergeo',
        marker: { size: 16, color: 'rgba(46,204,113,0.3)', line: { color: '#2ecc71', width: 2 } },
        hoverinfo: 'skip'
      };

      setPlotData([trace, startMarker, endMarker, nowMarker]);
      setPlotLayout({
        title: `${data.satellite_name || (inputMode === 'name' ? satelliteName : 'Satellite')} Ground Track — ${data.duration_hr.toFixed(1)}h Span`,
        // MODIFIED: Explicitly set background colors to fix the "white box"
        paper_bgcolor: '#1a1a2e',
        geo: {
          projection: { type: 'natural earth' },
          bgcolor: '#1a1a2e', // This sets the map background
          showcoastlines: true,
          coastlinecolor: '#405a80',
          showland: true,
          landcolor: 'rgb(20, 40, 60)',
          showocean: true,
          oceancolor: 'rgb(10, 25, 45)',
        },
        font: { color: '#c0c0c0' }
      });

      // Expose metadata for confirmation panel
      setMeta({
  startUtc: data.start_utc_iso,
        endUtc: data.end_utc_iso,
        startLat: data.start_lat,
  startLon: data.start_lon,
  anchoredToTle: !!data.anchored_to_tle_epoch,
  tleEpoch: data.tle_epoch_iso || null,
  tleAgeHours: data.tle_age_hours || null,
      });

    } catch (err) {
      if (err.response) {
        setError(err.response.data.error || 'An unknown server error occurred.');
      } else if (err.request) {
        setError('Could not connect to the backend server. Is it running?');
      } else {
        setError(`Error: ${err.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // --- RENDER ---
  return (
    <div className="App">
      <h1>Satellite Ground Track Dashboard</h1>
      <div className="controls-container">
        
        {/* Input Mode Toggle */}
        <div className="input-mode-toggle">
          <button 
            className={inputMode === 'name' ? 'active' : ''}
            onClick={() => setInputMode('name')}
          >
            Satellite Name
          </button>
          <button 
            className={inputMode === 'tle' ? 'active' : ''}
            onClick={() => setInputMode('tle')}
          >
            TLE Data
          </button>
        </div>

        {/* Conditional Input Fields */}
        {inputMode === 'name' ? (
          <div className="satellite-name-input">
            <label htmlFor="satelliteName">Satellite Name:</label>
            <div className="autocomplete-container">
              <input
                type="text"
                id="satelliteName"
                value={satelliteName}
                onChange={handleSatelliteNameChange}
                onKeyDown={handleKeyDown}
                onFocus={handleInputFocus}
                // Delay closing to allow click on dropdown
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                placeholder="e.g., ISS, Hubble, NOAA..."
              />
              {searchLoading && (
                <div className="search-loading">Searching...</div>
              )}
              {showSuggestions && suggestions.length > 0 && !searchLoading && (
                <div className="suggestions-dropdown">
                  {suggestions.map((suggestion, index) => (
                    <div
                      key={suggestion.norad_id}
                      className={`suggestion-item ${index === activeSuggestion ? 'active' : ''}`}
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      <div className="suggestion-name">{suggestion.name}</div>
                      <div className="suggestion-id">ID: {suggestion.norad_id}</div>
                    </div>
                  ))}
                </div>
              )}
              {showSuggestions && suggestions.length === 0 && !searchLoading && (
                <div className="no-results">No results</div>
              )}
            </div>
          </div>
        ) : (
          <div className="tle-inputs">
            <textarea
              value={tleLine1}
              onChange={(e) => setTleLine1(e.target.value)}
              placeholder="TLE Line 1"
            />
            <textarea
              value={tleLine2}
              onChange={(e) => setTleLine2(e.target.value)}
              placeholder="TLE Line 2"
            />
          </div>
        )}

        <div className="action-row">
          <div className="duration-control">
            <label htmlFor="duration">Duration (hours):</label>
            {/* NEW: Use the custom DurationInput component */}
            <DurationInput 
              value={duration}
              onChange={setDuration}
              min={1}
              max={168}
            />
          </div>
          <button 
            className="generate-button" 
            onClick={handleGenerateTrack} 
            disabled={isLoading}
          >
            {isLoading ? 'Calculating...' : 'Generate Track'}
          </button>
        </div>
        
        {error && <div className="status-message error">{error}</div>}
      </div>
      
      {plotData && (
        <div className="plot-container">
          <Plot
            data={plotData}
            layout={plotLayout}
            useResizeHandler={true}
            style={{ width: '100%', height: '100%' }}
            config={{ responsive: true }}
          />
        </div>
      )}

      {/* Confirmation panel for start/end */}
      {meta && (
        <div className="confirmation-panel">
          <div>
            Start: <strong>{meta.startUtc}</strong>
          </div>
          <div>
            Start position: <strong>{meta.startLat.toFixed(2)}°, {meta.startLon.toFixed(2)}°</strong>
          </div>
          <div>
            End: <strong>{meta.endUtc}</strong>
          </div>
          {meta.anchoredToTle && (
            <div>
              Using TLE epoch due to stale elements. TLE epoch: <strong>{meta.tleEpoch}</strong>{' '}
              {meta.tleAgeHours != null && (
                <span>(age ≈ {Number(meta.tleAgeHours).toFixed(1)} h)</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;