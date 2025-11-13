import api from './api_service';

export const getDashboardOverview = async () => {
  try {
    const response = await api.get('/dashboard/overview');
    return response.data;
  } catch (error) {
    console.error('Error fetching dashboard overview:', error);
    return { success: false, data: {} };
  }
};

export const getEnergyMix = async (days = 30) => {
  try {
    const response = await api.get('/dashboard/energy-mix', {
      params: { days }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching energy mix:', error);
    return { success: false, data: [] };
  }
};

export const getTopPerformers = async (limit = 10) => {
  try {
    const response = await api.get('/dashboard/top-performers', {
      params: { limit }
    });
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
