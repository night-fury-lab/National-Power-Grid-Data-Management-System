import React, { useState, useEffect } from 'react';
import { getAllRegions, getAvailableDatesForRegions, getStateEnergyMix } from '../services/plant_service';
import Card from '../components/Card';
import Table from '../components/Table';
import LoadingSpinner from '../components/LoadingSpinner';
import EnergyMixPieChart from '../charts/EnergyMixPieChart';
import '../styles/Regions.css';

const Regions = () => {
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedState, setSelectedState] = useState(null);
  const [energyMixData, setEnergyMixData] = useState([]);
  const [loadingModal, setLoadingModal] = useState(false);

  useEffect(() => {
    fetchAvailableDates();
  }, []);

  useEffect(() => {
    if (selectedDate) {
      fetchRegions();
    }
  }, [selectedDate]);

  const fetchAvailableDates = async () => {
    try {
      const response = await getAvailableDatesForRegions();
      const dates = response.data || [];
      setAvailableDates(dates);
      
      // Set the most recent date as default
      if (dates.length > 0) {
        setSelectedDate(dates[0]);
      }
    } catch (error) {
      console.error('Error fetching available dates:', error);
      setAvailableDates([]);
    }
  };

  const fetchRegions = async () => {
    try {
      setLoading(true);
      const response = await getAllRegions(selectedDate);
      setRegions(response.data || []);
    } catch (error) {
      console.error('Error fetching regions:', error);
      setRegions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = async (row) => {
    setSelectedState(row);
    setShowModal(true);
    setLoadingModal(true);
    
    try {
      const response = await getStateEnergyMix(row.state_code, selectedDate);
      // Transform data to match the pie chart format
      const transformedData = (response.data || []).map(item => ({
        type_name: item.energy_type,
        total_generation_mu: item.generated_mu
      }));
      setEnergyMixData(transformedData);
    } catch (error) {
      console.error('Error fetching energy mix:', error);
      setEnergyMixData([]);
    } finally {
      setLoadingModal(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedState(null);
    setEnergyMixData([]);
  };

  const columns = [
    { header: 'State', accessor: 'state_name' },
    { header: 'Region', accessor: 'region' },
    { header: 'Plants', accessor: 'plant_count' },
    { 
      header: 'Generated (MU)', 
      render: (row) => (row.generated_mu || 0).toFixed(2) 
    },
    { 
      header: 'Demand (MU)', 
      render: (row) => (row.demand_mu || 0).toFixed(2) 
    },
    { 
      header: 'Status', 
      render: (row) => (
        <span className={`status-badge ${(row.energy_status || 'Unknown').toLowerCase()}`}>
          {row.energy_status || 'Unknown'}
        </span>
      )
    }
  ];

  if (loading) return <LoadingSpinner />;

  return (
    <div className="regions-page">
      <div className="page-header">
        <h1>🗺️ Regional Overview</h1>
        <div className="date-selector">
          <label htmlFor="region-date-picker">View data for date: </label>
          <select
            id="region-date-picker"
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
      <Card>
        <Table columns={columns} data={regions} onRowClick={handleRowClick} />
      </Card>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Energy Mix Distribution ({selectedState?.state_name})</h2>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <div className="modal-body">
              {loadingModal ? (
                <LoadingSpinner />
              ) : (
                <>
                  <p className="modal-date">
                    {selectedDate && new Date(selectedDate).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </p>
                  <EnergyMixPieChart data={energyMixData} />
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Regions;
