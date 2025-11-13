import api from './api_service';

export const getRegionalPerformance = async (opts = {}) => {
  // opts: { report_date: 'YYYY-MM-DD', state_code: 'KA' }
  try {
    const response = await api.get('/analytics/regional-performance', { params: opts });
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

export const getStates = async () => {
  try {
    const response = await api.get('/analytics/states');
    return response.data;
  } catch (error) {
    console.error('Error fetching states list:', error);
    return { success: false, data: [] };
  }
};

export const getMonthlyTrends = async () => {
  try {
    const response = await api.get('/analytics/monthly-trends');
    return response.data;
  } catch (error) {
    console.error('Error fetching monthly trends:', error);
    return { success: false, data: [] };
  }
};
