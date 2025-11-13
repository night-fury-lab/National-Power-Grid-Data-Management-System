import React, { useState, useEffect } from 'react';
import { getAllAlerts, getCoalCriticalAlerts } from '../services/plant_service';
import Card from '../components/Card';
import AlertBanner from '../components/AlertBanner';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/Alerts.css';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [coalAlerts, setCoalAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const [allAlerts, coal] = await Promise.all([
        getAllAlerts(),
        getCoalCriticalAlerts()
      ]);

      setAlerts(allAlerts.data || []);
      setCoalAlerts(coal.data || []);
    } catch (error) {
      console.error('Error fetching alerts:', error);
      setAlerts([]);
      setCoalAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="alerts-page">
      <h1>🚨 System Alerts</h1>

      <div className="alerts-summary">
        <Card>
          <h3>Total Alerts</h3>
          <p className="alert-count">{alerts.length}</p>
        </Card>
        <Card>
          <h3>Critical</h3>
          <p className="alert-count critical">
            {alerts.filter(a => a.severity === 'CRITICAL').length}
          </p>
        </Card>
        <Card>
          <h3>Warning</h3>
          <p className="alert-count warning">
            {alerts.filter(a => a.severity === 'WARNING').length}
          </p>
        </Card>
      </div>

      <Card>
        <h2>All Alerts</h2>
        <div className="alerts-list">
          {alerts.map((alert, index) => (
            <AlertBanner
              key={index}
              type={alert.severity?.toLowerCase() || 'warning'}
              message={`${alert.alert_type || 'Alert'}: ${alert.plant_name || 'Unknown'} (${alert.state_name || 'Unknown'}) - Value: ${(alert.value || 0).toFixed(2)}`}
            />
          ))}
        </div>
      </Card>

      <Card>
        <h2>Critical Coal Stock</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Plant Name</th>
              <th>State</th>
              <th>Coal Stock (Days)</th>
              <th>Capacity (MW)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {coalAlerts.map((alert, index) => (
              <tr key={index}>
                <td>{alert.plant_name || 'Unknown'}</td>
                <td>{alert.state_name || 'Unknown'}</td>
                <td>{(alert.coal_stock_days || 0).toFixed(1)}</td>
                <td>{(alert.operational_capacity_mw || 0).toFixed(0)}</td>
                <td>
                  <span className={`status-badge ${(alert.stock_status || 'ADEQUATE').toLowerCase()}`}>
                    {alert.stock_status || 'ADEQUATE'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

export default Alerts;
