import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const TrendLineChart = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        No data available for chart
      </div>
    );
  }

  const chartData = data.map(item => {
    try {
      return {
        date: item.date ? new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Unknown',
        generation: parseFloat(item.total_generation_mu || 0),
        efficiency: parseFloat(item.avg_efficiency || 0),
        capacity: parseFloat(item.total_capacity_mw || 0) / 1000 // Convert to GW for better scale
      };
    } catch (error) {
      return {
        date: 'Invalid',
        generation: 0,
        efficiency: 0,
        capacity: 0
      };
    }
  });

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'white',
          padding: '12px',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <p style={{ fontWeight: '600', marginBottom: '8px' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, fontSize: '0.875rem' }}>
              {entry.name}: {(entry.value || 0).toFixed(2)} {entry.unit || ''}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart
        data={chartData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          stroke="#64748b"
          style={{ fontSize: '0.875rem' }}
        />
        <YAxis
          yAxisId="left"
          stroke="#64748b"
          style={{ fontSize: '0.875rem' }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          stroke="#64748b"
          style={{ fontSize: '0.875rem' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ paddingTop: '20px' }}
          iconType="line"
        />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="generation"
          stroke="#3b82f6"
          strokeWidth={3}
          name="Generation (MU)"
          dot={{ fill: '#3b82f6', r: 4 }}
          activeDot={{ r: 6 }}
          animationDuration={1000}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="efficiency"
          stroke="#10b981"
          strokeWidth={3}
          name="Efficiency (%)"
          dot={{ fill: '#10b981', r: 4 }}
          activeDot={{ r: 6 }}
          animationDuration={1000}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default TrendLineChart;
