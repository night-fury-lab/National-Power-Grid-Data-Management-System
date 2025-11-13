import api from './api_service';

// Use a dedicated companies API base if provided; prefer Node/Mongo by default for companies
const COMPANIES_API_BASE = process.env.REACT_APP_COMPANIES_URL || process.env.REACT_APP_MONGO_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const createCompany = async (payload) => {
  try {
    const url = `${COMPANIES_API_BASE.replace(/\/$/, '')}/companies`;
    console.log('[companies_service] POST', url, payload);
    // Use axios instance 'api' so default headers/timeouts are applied; passing an absolute URL overrides baseURL
    const response = await api.post(url, payload);
    // Normalize return shape: prefer { success: true, id } if present, else adapt from other servers
    const data = response.data || {};
    console.log('[companies_service] response', data);
    if (data.success || data.id || data.msg === 'Success') {
      return { success: true, data };
    }
    return { success: false, data };
  } catch (error) {
    console.error('Error creating company:', error?.response || error);
    const data = error?.response?.data;
    console.log('[companies_service] error response', data);
    return { success: false, message: data?.message || data?.msg || data?.error || 'Server error', error: data };
  }
};
export const getCompanies = async () => {
  try {
    const url = `${COMPANIES_API_BASE.replace(/\/$/, '')}/companies`;
    const response = await api.get(url);
    const data = response.data || [];
    return { success: true, data };
  } catch (error) {
    console.error('Error fetching companies:', error?.response || error);
    const data = error?.response?.data;
    return { success: false, message: data?.message || 'Server error', error: data };
  }
};

export const deleteCompany = async (id) => {
  try {
    const url = `${COMPANIES_API_BASE.replace(/\/$/, '')}/companies/${id}`;
    const response = await api.delete(url);
    const data = response.data || {};
    return { success: true, data };
  } catch (error) {
    console.error('Error deleting company:', error?.response || error);
    const data = error?.response?.data;
    return { success: false, message: data?.message || 'Server error', error: data };
  }
};

export default { createCompany, getCompanies, deleteCompany };
