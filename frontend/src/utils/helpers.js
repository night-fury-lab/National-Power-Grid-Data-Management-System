export const formatNumber = (num, decimals = 2) => {
  return Number(num).toFixed(decimals);
};

export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-IN');
};

export const getStatusColor = (status) => {
  const colors = {
    'Active': '#10b981',
    'Under Outage': '#ef4444',
    'Not Commisioned': '#f59e0b'
  };
  return colors[status] || '#64748b';
};

export const calculatePercentage = (value, total) => {
  if (total === 0) return 0;
  return ((value / total) * 100).toFixed(2);
};

export const truncateText = (text, maxLength) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};
