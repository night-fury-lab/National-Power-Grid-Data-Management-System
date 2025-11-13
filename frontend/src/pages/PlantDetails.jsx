import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getPlantDetails, getProductionHistory } from '../services/plant_service';
import Card from '../components/Card';
import TrendLineChart from '../charts/TrendLineChart';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/PlantDetails.css';

const PlantDetails = () => {
  const { plantId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [plant, setPlant] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState('');
  const [availableDates, setAvailableDates] = useState([]);

  useEffect(() => {
    fetchPlantData();
  }, [plantId, selectedDate]);

  const fetchPlantData = async () => {
    try {
      setLoading(true);
      const [plantData, historyData] = await Promise.all([
        getPlantDetails(plantId, selectedDate),
        getProductionHistory(plantId, 30)
      ]);

      if (plantData.success) {
        setPlant(plantData.data || null);
      } else {
        console.error('Error fetching plant details:', plantData.error);
        setPlant(null);
      }
      
      if (historyData.success) {
        const histData = historyData.data || [];
        setHistory(histData);
        // Extract unique dates from history for the date picker
        const dates = histData
          .map(h => h.log_date || h.date)
          .filter(d => d)
          .sort((a, b) => new Date(b) - new Date(a));
        setAvailableDates([...new Set(dates)]);
        
        // Set default selected date to the most recent if not already set
        if (!selectedDate && dates.length > 0) {
          setSelectedDate(dates[0]);
        }
      } else {
        console.error('Error fetching production history:', historyData.error);
        setHistory([]);
      }
    } catch (error) {
      console.error('Error fetching plant data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!plant) return <div>Plant not found</div>;

  return (
    <div className="plant-details-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => {
          // Try to use state passed from Plants page to reconstruct URL
          const prevSearch = location.state?.search || '';
          const prevPage = location.state?.page || 1;
          if (location.state && (prevSearch || prevPage)) {
            const params = new URLSearchParams();
            if (prevSearch) params.set('search', prevSearch);
            if (prevPage && prevPage > 1) params.set('page', String(prevPage));
            const url = params.toString() ? `/plants?${params.toString()}` : '/plants';
            navigate(url);
          } else {
            // fallback to history back
            navigate(-1);
          }
        }}>← Back</button>
        <h1>{plant.plant_name}</h1>
        <div className="date-selector">
          <label htmlFor="date-picker">View data for date: </label>
          <select
            id="date-picker"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-picker-select"
          >
            {availableDates.map(date => (
              <option key={date} value={date}>
                {new Date(date).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'short', 
                  day: 'numeric' 
                })}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="info-grid">
        <Card>
          <h3>Plant Information</h3>
          <div className="info-item">
            <span className="label">Plant ID:</span>
            <span className="value">{plant.plant_id}</span>
          </div>
          <div className="info-item">
            <span className="label">State:</span>
            <span className="value">{plant.state_name}</span>
          </div>
          <div className="info-item">
            <span className="label">Region:</span>
            <span className="value">{plant.region || 'Unknown'}</span>
          </div>
          <div className="info-item">
            <span className="label">Energy Type:</span>
            <span className="value">{plant.energy_type}</span>
          </div>
          <div className="info-item">
            <span className="label">Sector:</span>
            <span className="value">{plant.sector_name}</span>
          </div>
        </Card>

        <Card>
          <h3>Performance Metrics</h3>
          <div className="info-item">
            <span className="label">Average Efficiency:</span>
            <span className="value">{(plant.avg_efficiency || 0).toFixed(2)}%</span>
          </div>
          <div className="info-item">
            <span className="label">Total Generation:</span>
            <span className="value">{(plant.total_generation_mu || 0).toFixed(2)} MU</span>
          </div>
          <div className="info-item">
            <span className="label">Average Capacity:</span>
            <span className="value">{(plant.avg_capacity_mw || 0).toFixed(2)} MW</span>
          </div>
          <div className="info-item">
            <span className="label">Current Status:</span>
            <span className={`status-badge ${plant.current_status?.toLowerCase().replace(/\s+/g, '-')}`}>
              {plant.current_status || 'Unknown'}
            </span>
          </div>
          {plant.current_status === 'Under Outage' && plant.status_remarks && (
            <>
              <div className="info-item">
                <span className="label">Outage Date:</span>
                <span className="value">{plant.outage_date || 'N/A'}</span>
              </div>
              <div className="info-item">
                <span className="label">Remarks:</span>
                <span className="value">{plant.status_remarks}</span>
              </div>
            </>
          )}
        </Card>
      </div>

      <Card>
        <h3>Production History (Last 30 Days)</h3>
        <TrendLineChart data={history.map(h => ({
          date: h.log_date || h.date,
          total_generation_mu: h.todays_actual_mu || h.actual_mu || 0,
          avg_efficiency: h.efficiency_percentage || h.efficiency || 0,
          total_capacity_mw: h.operational_capacity_mw || 0
        }))} />
      </Card>
    </div>
  );
};

export default PlantDetails;
