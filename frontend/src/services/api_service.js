import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Fail fast if backend doesn't respond
  timeout: 15000,
});

// Dashboard endpoints
export const getDashboardOverview = async (date = null) => {
  try {
    const params = date ? { date } : {};
    const response = await api.get('/dashboard/overview', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching dashboard overview:', error);
    return { success: false, data: {} };
  }
};

export const getEnergyMix = async (date = null) => {
  try {
    const params = date ? { date } : {};
    const response = await api.get('/dashboard/energy-mix', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching energy mix:', error);
    return { success: false, data: [] };
  }
};

export const getTopPerformers = async (date = null, limit = 10) => {
  try {
    const params = {};
    if (date) params.date = date;
    // keep limit for backward compatibility; backend may ignore it
    if (limit) params.limit = limit;
    const response = await api.get('/dashboard/top-performers', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching top performers:', error);
    return { success: false, data: [] };
  }
};

export const getWeeklyTrend = async () => {
  try {
    const response = await api.get('/dashboard/weekly-trend');
    return response.data;
  } catch (error) {
    console.error('Error fetching weekly trend:', error);
    return { success: false, data: [] };
  }
};

// Plants endpoints
export const getAllPlants = async (params = {}) => {
  try {
    // Remove empty search strings
    const cleanParams = { ...params };
    if (cleanParams.search === '' || !cleanParams.search) {
      delete cleanParams.search;
    }
    const response = await api.get('/plants', { params: cleanParams });
    return response.data;
  } catch (error) {
    console.error('Error fetching plants:', error);
    return { success: false, data: [], pagination: {} };
  }
};

export const getPlantDetails = async (plantId) => {
  try {
    const response = await api.get(`/plants/${plantId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching plant details:', error);
    return { success: false, data: null };
  }
};

// Analytics endpoints
export const getRegionalPerformance = async () => {
  try {
    const response = await api.get('/analytics/regional-performance');
    return response.data;
  } catch (error) {
    console.error('Error fetching regional performance:', error);
    return { success: false, data: [] };
  }
};

export const getEfficiencyComparison = async () => {
  try {
    const response = await api.get('/analytics/efficiency-comparison');
    return response.data;
  } catch (error) {
    console.error('Error fetching efficiency comparison:', error);
    return { success: false, data: [] };
  }
};

export const getRenewableMix = async () => {
  try {
    const response = await api.get('/analytics/renewable-mix');
    return response.data;
  } catch (error) {
    console.error('Error fetching renewable mix:', error);
    return { success: false, data: [] };
  }
};

// Regions endpoints
export const getAllRegions = async () => {
  try {
    const response = await api.get('/regions');
    return response.data;
  } catch (error) {
    console.error('Error fetching regions:', error);
    return { success: false, data: [] };
  }
};

// Alerts endpoints
export const getAllAlerts = async () => {
  try {
    const response = await api.get('/alerts');
    return response.data;
  } catch (error) {
    console.error('Error fetching alerts:', error);
    return { success: false, data: [] };
  }
};

export const getCoalCriticalAlerts = async () => {
  try {
    const response = await api.get('/alerts/coal-critical');
    return response.data;
  } catch (error) {
    console.error('Error fetching coal alerts:', error);
    return { success: false, data: [] };
  }
};

export default api;
