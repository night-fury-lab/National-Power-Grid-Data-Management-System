import React from 'react';
import '../styles/LoadingSpinner.css';

const LoadingSpinner = () => {
  return (
    <div className="loading-container">
      <div className="spinner"></div>
      <p>Loading data...</p>
    </div>
  );
};

export default LoadingSpinner;
