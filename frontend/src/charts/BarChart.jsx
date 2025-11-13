import React from 'react';
import { BarChart as RechartsBar, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BarChart = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        No data available for chart
      </div>
    );
  }

  const chartData = data.map(item => ({
    name: item.state_name || 'Unknown',
    renewable: parseFloat(item.renewable_mu || 0),
    nonRenewable: parseFloat(item.non_renewable_mu || 0)
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RechartsBar data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="name" 
          angle={-45} 
          textAnchor="end" 
          height={100}
          style={{ fontSize: '0.75rem' }}
        />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="renewable" fill="#10b981" name="Renewable (MU)" />
        <Bar dataKey="nonRenewable" fill="#ef4444" name="Non-Renewable (MU)" />
      </RechartsBar>
    </ResponsiveContainer>
  );
};

export default BarChart;
