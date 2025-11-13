import React from 'react';
import { FaExclamationTriangle, FaCheckCircle, FaInfoCircle } from 'react-icons/fa';
import '../styles/AlertBanner.css';

const AlertBanner = ({ type = 'info', message, onClose }) => {
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <FaCheckCircle />;
      case 'error':
      case 'critical':
        return <FaExclamationTriangle />;
      default:
        return <FaInfoCircle />;
    }
  };

  return (
    <div className={`alert-banner alert-${type}`}>
      <div className="alert-icon">{getIcon()}</div>
      <div className="alert-message">{message}</div>
      {onClose && (
        <button className="alert-close" onClick={onClose}>
          ×
        </button>
      )}
    </div>
  );
};

export default AlertBanner;
