export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

export const ENERGY_COLORS = {
  'THERMAL': '#ef4444',
  'HYDRO': '#3b82f6',
  'WIND': '#10b981',
  'SOLAR': '#f59e0b',
  'NUCLEAR': '#8b5cf6',
  'BIOMASS': '#84cc16',
  'THER (CGT)': '#f97316'
};

export const STATUS_COLORS = {
  'Active': '#10b981',
  'Under Outage': '#ef4444',
  'Not Commisioned': '#f59e0b'
};

export const SEVERITY_COLORS = {
  'CRITICAL': '#dc2626',
  'WARNING': '#f59e0b',
  'INFO': '#3b82f6'
};

export const REGIONS = ['Northern', 'Southern', 'Eastern', 'Western', 'North-Eastern'];
