import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import EnergyMixPieChart from '../charts/EnergyMixPieChart';
import LoadingSpinner from '../components/LoadingSpinner';
import { getDashboardOverview, getEnergyMix, getTopPerformers } from '../services/api_service';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [energyMix, setEnergyMix] = useState([]);
  const [topPerformers, setTopPerformers] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [minDate, setMinDate] = useState('2025-08-01');
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setError(null);
      setLoading(true);
      const overviewData = await getDashboardOverview();
      // Determine selected date from overview response (preferred) or keep current selectedDate
      if (overviewData.success) {
        setOverview(overviewData.data);
        // overviewData.data may contain selected_date and date_filter_placeholder
        const ovDate = overviewData.data.selected_date || overviewData.data.date_filter_placeholder;
        const ovMin = overviewData.data.date_filter_placeholder || minDate;
        setMinDate(ovMin);
        // If no selectedDate chosen yet, use overview's selected date
        if (!selectedDate) setSelectedDate(ovDate);
      }

      // Use the chosen or overview date for other calls
      const dateToUse = selectedDate || (overviewData.success ? (overviewData.data.selected_date || overviewData.data.date_filter_placeholder) : null);

      const mixData = await getEnergyMix(dateToUse);
      const performersData = await getTopPerformers(dateToUse);

      if (mixData.success) {
        setEnergyMix(mixData.data);
      }
      if (performersData.success) {
        setTopPerformers(performersData.data);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError('Unable to load dashboard data. Please check the backend or try again.');
    } finally {
      setLoading(false);
    }
  };

  // When user changes the date, fetch data for that date
  const onDateChange = async (e) => {
    const newDate = e.target.value;
    setSelectedDate(newDate);
    setLoading(true);
    try {
      setError(null);
      const mixData = await getEnergyMix(newDate);
      const performersData = await getTopPerformers(newDate);
      if (mixData.success) setEnergyMix(mixData.data);
      if (performersData.success) setTopPerformers(performersData.data);
      // Also refresh overview for the selected date (pass date so KPIs update)
      const overviewData = await getDashboardOverview(newDate);
      if (overviewData.success) setOverview(overviewData.data);
    } catch (err) {
      console.error('Error fetching data for selected date:', err);
      setError('Unable to load data for selected date. Please try another date or check the backend.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ marginBottom: 12, color: '#b91c1c', fontWeight: 600 }}>{error}</div>
        <button onClick={fetchDashboardData} style={{ padding: '8px 12px', borderRadius: 6, background: '#2563eb', color: 'white', border: 'none' }}>Retry</button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>🔋 Energy Monitoring Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ color: '#475569', fontWeight: 600 }}>Date:</label>
          <input
            type="date"
            value={selectedDate || ''}
            onChange={onDateChange}
            min={minDate}
            style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid #e2e8f0' }}
          />
        </div>
      </div>
      
      {/* KPI Cards */}
      <div className="kpi-grid">
        <Card>
          <h3>Total Plants</h3>
          <p className="kpi-value">{overview?.total_plants || 0}</p>
        </Card>
        <Card>
          <h3>Today's Generation</h3>
          <p className="kpi-value">{((overview?.todays_generation_mu ?? 0)).toFixed(2)} MU</p>
        </Card>
        <Card>
          <h3>System Efficiency</h3>
          <p className="kpi-value">{((overview?.avg_efficiency ?? 0)).toFixed(2)}%</p>
        </Card>
        <Card>
          <h3>Total Capacity</h3>
          <p className="kpi-value">{((overview?.total_capacity_mw ?? 0)).toFixed(0)} MW</p>
        </Card>
      </div>

      {/* Energy Mix Chart */}
      <div className="chart-section">
        <Card>
          <h2>Energy Mix Distribution {selectedDate ? `(${selectedDate})` : '(selected date)'}</h2>
          {energyMix && energyMix.length > 0 ? (
            <EnergyMixPieChart data={energyMix} />
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
              No energy generation data available for the selected period
            </div>
          )}
        </Card>
      </div>

      {/* Top Performers Table */}
      {topPerformers.length > 0 && (
        <div className="table-section">
          <Card>
            <h2>Top Performing Plants {selectedDate ? `(${selectedDate})` : ''}</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Plant Name</th>
                  <th>State</th>
                  <th>Type</th>
                  <th>Efficiency (%)</th>
                  <th>Generation (MU)</th>
                </tr>
              </thead>
              <tbody>
                {topPerformers.map((plant, index) => (
                  <tr key={plant.plant_id}>
                    <td>{index + 1}</td>
                    <td>{plant.plant_name}</td>
                    <td>{plant.state_name}</td>
                    <td>{plant.energy_type}</td>
                <td>{((plant.avg_efficiency ?? plant.efficiency) || 0).toFixed(2)}</td>
                <td>{((plant.total_generation_mu ?? plant.todays_generation_mu) || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
