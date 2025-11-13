import api from './api_service';

export const generateDailyReport = async (reportDate) => {
  try {
    const params = reportDate ? { report_date: reportDate } : {};
    // --- CHANGE THIS LINE ---
    // Change from api.post(...) to api.get(...)
    // const response = await api.post('/admin/generate-daily-report', null, { params });
    const response = await api.get('/admin/generate-daily-report', { params });
    // --- END OF CHANGE ---
    return response.data;
  } catch (error) {
    console.error('Error generating daily report:', error);
    // Surface the specific error from the server if it exists
    if (error.response && error.response.data) {
        return error.response.data;
    }
    return { success: false, error: error.message };
  }
};

// ... (The other functions are correct and don't need changes)

export const identifyUnderperforming = async (threshold = 60, days = 30) => {
  try {
    const response = await api.get('/admin/identify-underperforming', { params: { threshold, days } });
    return response.data;
  } catch (error) {
    console.error('Error identifying underperforming plants:', error);
    return { success: false, error: error.message };
  }
};

export const calculateRegionalMetrics = async (startDate, endDate) => {
  try {
    const response = await api.get('/admin/calculate-regional-metrics', { params: { start_date: startDate, end_date: endDate } });
    return response.data;
  } catch (error) {
    console.error('Error calculating regional metrics:', error);
    if (error.response && error.response.data) {
      return error.response.data;
    }
    return { success: false, error: error.message };
  }
};

export const runDataUpdate = async () => {
  try {
    // Set timeout to 2 hours (7200000ms) to allow all scripts to complete
    const response = await api.post('/admin/run-data-update', null, {
      timeout: 7200000  // 2 hours in milliseconds
    });
    return response.data;
  } catch (error) {
    console.error('Error running data update:', error);
    if (error.response && error.response.data) {
      return error.response.data;
    }
    return { success: false, error: error.message };
  }
};

const admin = {
  generateDailyReport,
  identifyUnderperforming,
  calculateRegionalMetrics,
  runDataUpdate
};

export default admin;