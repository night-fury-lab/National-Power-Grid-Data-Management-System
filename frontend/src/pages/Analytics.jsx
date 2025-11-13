import React, { useState, useEffect } from 'react';
import { getRegionalPerformance, getRenewableMix } from '../services/analyticsService';
import Card from '../components/Card';
import BarChart from '../charts/BarChart';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/Analytics.css';

const Analytics = () => {
  const [regionalData, setRegionalData] = useState([]);
  const [renewableData, setRenewableData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);

      const [regional, renewable] = await Promise.all([
        getRegionalPerformance(),
        getRenewableMix()
      ]);

      setRegionalData(regional.data || []);
      setRenewableData(renewable.data || []);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setRegionalData([]);
      setRenewableData([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="analytics-page">
      <h1>📊 Analytics & Insights</h1>

      <Card>
        <h2>Regional Performance</h2>
        <div className="analytics-grid">{regionalData.map((region, index) => (
            <div key={index} className="region-card">
              <h3>{region.region || 'Unknown'}</h3>
              <p>
                <span className="label">Plants:</span>
                <span className="value">{(region.total_plants || 0).toLocaleString()}</span>
              </p>
              <p>
                <span className="label">Generated:</span>
                <span className="value">{(region.generated_mu || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})} MU</span>
              </p>
              <p>
                <span className="label">Demand:</span>
                <span className="value">{(region.demand_mu || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})} MU</span>
              </p>
              <p>
                <span className="label">Surplus:</span>
                <span className="value">{(region.surplus_mu || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})} MU</span>
              </p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2>Renewable Energy Mix by State</h2>
        <BarChart data={renewableData} />
      </Card>
    </div>
  );
};

export default Analytics;
