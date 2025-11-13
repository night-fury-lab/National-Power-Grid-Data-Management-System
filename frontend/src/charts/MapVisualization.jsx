import React from 'react';
import '../styles/MapVisualization.css';

const MapVisualization = ({ data }) => {
  // Placeholder for future map implementation
  // Can use libraries like react-simple-maps or leaflet
  
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className="map-placeholder">
        <h3>Map Visualization</h3>
        <p>No data available for map visualization</p>
      </div>
    );
  }
  
  return (
    <div className="map-placeholder">
      <h3>Map Visualization</h3>
      <p>Coming Soon: Interactive India Map with State-wise Energy Data</p>
      <div className="map-data-list">
        {data.map((item, index) => (
          <div key={index} className="map-data-item">
            <span className="state-name">{item.state_name || 'Unknown'}</span>
            <span className="state-value">{(item.generated_mu || 0).toFixed(2)} MU</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MapVisualization;
