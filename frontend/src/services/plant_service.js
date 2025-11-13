import api from './api_service';

export const getAllPlants = async (params = {}) => {
  try {
    const response = await api.get('/plants', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching all plants:', error);
    throw error;
  }
};

export const getFilterStates = async () => {
  try {
    const response = await api.get('/plants/filters/states');
    return response.data;
  } catch (error) {
    console.error('Error fetching filter states:', error);
    throw error;
  }
};

export const getFilterSectors = async () => {
  try {
    const response = await api.get('/plants/filters/sectors');
    return response.data;
  } catch (error) {
    console.error('Error fetching filter sectors:', error);
    throw error;
  }
};

export const getFilterTypes = async () => {
  try {
    const response = await api.get('/plants/filters/types');
    return response.data;
  } catch (error) {
    console.error('Error fetching filter types:', error);
    throw error;
  }
};

export const getPlantDetails = async (plantId, date = null) => {
  try {
    const params = date ? { date } : {};
    const response = await api.get(`/plants/${plantId}`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching plant details:', error);
    throw error;
  }
};

export const createPlant = async (data) => {
  try {
    const response = await api.post('/plants', data);
    return response.data;
  } catch (error) {
    console.error('Error creating plant:', error);
    throw error;
  }
};

export const deletePlant = async (plantId) => {
  try {
    const response = await api.delete(`/plants/${plantId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting plant:', error);
    throw error;
  }
};

export const updatePlant = async (plantId, data) => {
  try {
    const response = await api.put(`/plants/${plantId}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating plant:', error);
    throw error;
  }
};

export const getProductionHistory = async (plantId, days = 30) => {
  try {
    const response = await api.get(`/plants/${plantId}/production-history`, {
      params: { days }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching production history:', error);
    throw error;
  }
};

export const getAllRegions = async (date = null) => {
  try {
    const params = date ? { date } : {};
    const response = await api.get('/regions', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching regions:', error);
    throw error;
  }
};

export const getAvailableDatesForRegions = async () => {
  try {
    const response = await api.get('/regions/available-dates');
    return response.data;
  } catch (error) {
    console.error('Error fetching available dates:', error);
    throw error;
  }
};

export const getStateEnergyMix = async (stateCode, date = null) => {
  try {
    const params = date ? { date } : {};
    const response = await api.get(`/regions/${stateCode}/energy-mix`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching state energy mix:', error);
    throw error;
  }
};

export const getAllAlerts = async () => {
  try {
    const response = await api.get('/alerts');
    return response.data;
  } catch (error) {
    console.error('Error fetching alerts:', error);
    throw error;
  }
};

export const getCoalCriticalAlerts = async () => {
  try {
    const response = await api.get('/alerts/coal-critical');
    return response.data;
  } catch (error) {
    console.error('Error fetching coal alerts:', error);
    throw error;
  }
};
