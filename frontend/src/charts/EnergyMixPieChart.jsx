import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const COLORS = {
  'THERMAL': '#ef4444',
  'HYDRO': '#3b82f6',
  'WIND': '#10b981',
  'SOLAR': '#f59e0b',
  'NUCLEAR': '#8b5cf6',
  'BIOMASS': '#84cc16',
  'THER (CGT)': '#f97316'
};

const EnergyMixPieChart = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        No data available for chart
      </div>
    );
  }

  const chartData = data
    .filter(item => item && (item.total_generation_mu || 0) > 0)
    .map(item => ({
      name: item.type_name || 'Unknown',
      value: parseFloat(item.total_generation_mu || 0),
      efficiency: parseFloat(item.avg_efficiency || 0)
    }));

  if (chartData.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        No energy generation data available
      </div>
    );
  }

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * Math.PI / 180);
    const y = cy + radius * Math.sin(-midAngle * Math.PI / 180);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontWeight="600"
      >
        {`${(percent * 100).toFixed(1)}%`}
      </text>
    );
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'white',
          padding: '12px',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <p style={{ fontWeight: '600', marginBottom: '4px' }}>
            {payload[0].name}
          </p>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Generation: {(payload[0].value || 0).toFixed(2)} MU
          </p>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Avg Efficiency: {(payload[0].payload?.efficiency || 0).toFixed(2)}%
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={350}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={renderCustomLabel}
          outerRadius={120}
          fill="#8884d8"
          dataKey="value"
          animationBegin={0}
          animationDuration={800}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          verticalAlign="bottom"
          height={36}
          iconType="circle"
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default EnergyMixPieChart;
