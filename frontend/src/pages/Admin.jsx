import React, { useState } from 'react';
import { generateDailyReport, identifyUnderperforming, calculateRegionalMetrics } from '../services/admin_service';
import Card from '../components/Card';
import Table from '../components/Table';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/Analytics.css';
import '../styles/Admin.css';

const prettify = (s) => {
  if (!s) return '';
  return s
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const normalizeResult = (res) => {
  // Accept many possible shapes from backend or stored-proc responses
  if (!res) return { rows: [], dataDate: null, raw: res };
  if (res.rows && Array.isArray(res.rows)) return { rows: res.rows, dataDate: res.data_date || res.dataDate || res.data_date, raw: res };
  if (Array.isArray(res)) return { rows: res, dataDate: null, raw: res };
  if (res.data && Array.isArray(res.data)) return { rows: res.data, dataDate: res.data_date || null, raw: res };
  // Some stored-proc wrappers return { result: [...] }
  if (res.result && Array.isArray(res.result)) return { rows: res.result, dataDate: res.data_date || null, raw: res };
  // If nothing matches, but res is an object, try to use its values if all are arrays of equal length -> construct rows
  const objVals = Object.values(res).filter(v => Array.isArray(v));
  if (objVals.length > 0 && objVals[0].length > 0) {
    // build rows from first array's length
    const len = objVals[0].length;
    const keys = Object.keys(res).filter(k => Array.isArray(res[k]) && res[k].length === len);
    if (keys.length > 0) {
      const rows = Array.from({ length: len }).map((_, i) => {
        const r = {};
        keys.forEach(k => r[k] = res[k][i]);
        return r;
      });
      return { rows, dataDate: res.data_date || null, raw: res };
    }
  }
  return { rows: [], dataDate: res.data_date || null, raw: res };
};

const downloadCSV = (rows, filename = 'report.csv') => {
  if (!rows || rows.length === 0) {
    const blob = new Blob([""], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    return;
  }
  const keys = Object.keys(rows[0]);
  const header = keys.join(',');
  const lines = rows.map(r => keys.map(k => {
    const v = r[k] === null || r[k] === undefined ? '' : String(r[k]);
    // escape quotes
    if (v.includes(',') || v.includes('"') || v.includes('\n')) return '"' + v.replace(/"/g, '""') + '"';
    return v;
  }).join(','));
  const csv = [header, ...lines].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
};

const ResultPanel = ({ title, result, loading, onDownloadJson, onDownloadCsv }) => {
  const { rows, dataDate, raw } = normalizeResult(result);
  const columns = rows && rows.length > 0 ? Object.keys(rows[0]).map(k => ({ header: prettify(k), accessor: k })) : [];

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>{title}</h3>
        <div className="result-panel-meta">
          {dataDate && <small style={{ color: '#666' }}>Data date: {dataDate}</small>}
          <div className="result-actions">
            <button type="button" onClick={() => onDownloadJson && onDownloadJson()} disabled={!result}>JSON</button>
            <button type="button" onClick={() => onDownloadCsv && onDownloadCsv()} disabled={!rows || rows.length === 0}>CSV</button>
          </div>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div>
          {result && result.success === false ? (
            <div style={{ padding: 12 }}>
              <div style={{ background: '#fff7ed', border: '1px solid #fcd34d', color: '#92400e', padding: 12, borderRadius: 8 }}>
                <strong>Error:</strong> {result.error || 'An error occurred while running the report.'}
              </div>
              {raw && <pre style={{ maxHeight: 240, overflow: 'auto', marginTop: 8 }}>{JSON.stringify(raw, null, 2)}</pre>}
            </div>
          ) : (
            <div>
              {rows && rows.length > 0 ? (
                <Table columns={columns} data={rows} />
              ) : (
                <div style={{ padding: 12 }}>
                  <em>No tabular results to display.</em>
                  {raw && <pre style={{ maxHeight: 240, overflow: 'auto', marginTop: 8 }}>{JSON.stringify(raw, null, 2)}</pre>}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

const Admin = () => {
  const [reportDate, setReportDate] = useState('');
  const [dailyReport, setDailyReport] = useState(null);
  const [threshold, setThreshold] = useState(60);
  const [days, setDays] = useState(30);
  const [underperf, setUnderperf] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [regionalMetrics, setRegionalMetrics] = useState(null);
  const [loading, setLoading] = useState(false);

  const onGenerate = async () => {
    setLoading(true);
    const res = await generateDailyReport(reportDate || undefined);
    setDailyReport(res);
    setLoading(false);
  };

  const onIdentify = async () => {
    setLoading(true);
    const res = await identifyUnderperforming(Number(threshold), Number(days));
    setUnderperf(res);
    setLoading(false);
  };

  const onCalculate = async () => {
    // Client-side validation before calling backend
    if (!startDate || !endDate) {
      setRegionalMetrics({ success: false, error: 'Please select both start and end dates.' });
      return;
    }
    // ensure format roughly YYYY-MM-DD
    const iso = /^\d{4}-\d{2}-\d{2}$/;
    if (!iso.test(startDate) || !iso.test(endDate)) {
      setRegionalMetrics({ success: false, error: 'Dates must be in YYYY-MM-DD format.' });
      return;
    }
    if (startDate > endDate) {
      setRegionalMetrics({ success: false, error: 'Start date must be before or equal to end date.' });
      return;
    }

    setLoading(true);
    const res = await calculateRegionalMetrics(startDate, endDate);
    setRegionalMetrics(res);
    setLoading(false);
  };

  // Update Plant Status feature removed

  const [selectedFeature, setSelectedFeature] = useState('daily');

  return (
    <div className="analytics-page">
      <h1>Admin Tools</h1>

      <div style={{ marginBottom: 12 }}>
        <label style={{ marginRight: 8 }}>Choose feature:</label>
        <select className="admin-select" value={selectedFeature} onChange={(e) => setSelectedFeature(e.target.value)}>
          <option value="daily">Generate Daily Report</option>
          <option value="underperform">Identify Underperforming Plants</option>
          <option value="regional">Calculate Regional Metrics</option>
          
        </select>
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        {selectedFeature === 'daily' && (
          <div style={{ maxWidth: 900 }}>
            <Card>
              <h3>Generate Daily Report</h3>
              <div className="admin-controls">
                <input type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
                <button type="button" onClick={onGenerate} disabled={loading}>Generate</button>
              </div>
            </Card>
            <ResultPanel
              title="Daily Report"
              result={dailyReport}
              loading={loading}
              onDownloadJson={() => {
                const blob = new Blob([JSON.stringify(dailyReport, null, 2)], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `daily_report_${reportDate || 'latest'}.json`;
                link.click();
              }}
              onDownloadCsv={() => downloadCSV(normalizeResult(dailyReport).rows, `daily_report_${reportDate || 'latest'}.csv`)}
            />
          </div>
        )}

        {selectedFeature === 'underperform' && (
          <div style={{ maxWidth: 900 }}>
            <Card>
              <h3>Identify Underperforming Plants</h3>
              <div className="admin-controls">
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  Threshold
                  <input type="number" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  Days
                  <input type="number" value={days} onChange={(e) => setDays(e.target.value)} />
                </label>
                <button type="button" onClick={onIdentify} disabled={loading}>Run</button>
              </div>
            </Card>
            <ResultPanel
              title="Underperforming Plants"
              result={underperf}
              loading={loading}
              onDownloadJson={() => {
                const blob = new Blob([JSON.stringify(underperf, null, 2)], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `underperforming_${Date.now()}.json`;
                link.click();
              }}
              onDownloadCsv={() => downloadCSV(normalizeResult(underperf).rows, `underperforming_${Date.now()}.csv`) }
            />
          </div>
        )}

        {selectedFeature === 'regional' && (
          <div style={{ maxWidth: 900 }}>
            <Card>
              <h3>Calculate Regional Metrics</h3>
              <div className="admin-controls">
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                <button type="button" onClick={onCalculate} disabled={loading}>Calculate</button>
              </div>
            </Card>
            <ResultPanel
              title="Regional Metrics"
              result={regionalMetrics}
              loading={loading}
              onDownloadJson={() => {
                const blob = new Blob([JSON.stringify(regionalMetrics, null, 2)], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `regional_metrics_${Date.now()}.json`;
                link.click();
              }}
              onDownloadCsv={() => downloadCSV(normalizeResult(regionalMetrics).rows, `regional_metrics_${Date.now()}.csv`)}
            />
          </div>
        )}

        
      </div>
    </div>
  );
};

export default Admin;
