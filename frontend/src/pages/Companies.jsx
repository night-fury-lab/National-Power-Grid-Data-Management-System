import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/Companies.css';
import { createCompany, getCompanies, deleteCompany } from '../services/companies_service';

const Companies = () => {
  const [form, setForm] = useState({
    id: '',
    company_name: '',
    company_description: '',
    company_email: '',
    demand_date: '',
    demand_MU: '',
    state_code: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCompanies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchCompanies = async () => {
    setListLoading(true);
    const res = await getCompanies();
    if (res && res.success) {
      setCompanies(Array.isArray(res.data) ? res.data : res.data?.companies || []);
    } else {
      console.error('Failed to load companies', res);
    }
    setListLoading(false);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    // normalize date if user types DD-MM-YYYY -> convert to YYYY-MM-DD
    if (name === 'demand_date' && value) {
      const ddmmyyyy = value.match(/^(\d{2})-(\d{2})-(\d{4})$/);
      if (ddmmyyyy) {
        const [, dd, mm, yyyy] = ddmmyyyy;
        setForm((s) => ({ ...s, [name]: `${yyyy}-${mm}-${dd}` }));
        return;
      }
    }

    setForm((s) => ({ ...s, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // required fields: id, company_name, demand_date, demand_MU, state_code
    if (!form.id || isNaN(Number(form.id))) {
      setError('A numeric id is required');
      return;
    }
    if (!form.company_name) {
      setError('Company name is required');
      return;
    }
    if (!form.demand_date) {
      setError('Demand date is required');
      return;
    }
    if (form.demand_MU === '' || isNaN(Number(form.demand_MU))) {
      setError('demand_MU (number) is required');
      return;
    }
    if (!form.state_code) {
      setError('State code is required');
      return;
    }

    // basic email validation
    if (form.company_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.company_email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      // build payload matching Node schema
      const payload = {
        id: Number(form.id),
        company_name: form.company_name,
        company_description: form.company_description || '',
        company_email: form.company_email || '',
        demand_date: form.demand_date,
        demand_MU: Number(form.demand_MU),
        state_code: form.state_code,
      };
      const res = await createCompany(payload);
      if (res && res.success) {
        setSuccess('Company saved successfully');
        setForm({ id: '', company_name: '', company_description: '', company_email: '', demand_date: '', demand_MU: '', state_code: '' });
        // refresh list
        fetchCompanies();
      } else {
        setError(res?.message || res?.error || 'Failed to save company');
      }
    } catch (err) {
      console.error(err);
      setError('Server error while saving company');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="companies-page">
      <div className="page-header">
        <h1>🏢 Energy Companies</h1>
        <p className="page-subtitle">Manage corporate energy demand registrations</p>
      </div>

      <div className="companies-container">
        <Card>
          <div className="card-header">
            <h2>Register New Company</h2>
            <p>Enter company details and energy demand requirements</p>
          </div>

          <form className="company-form" onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="id">Company ID <span className="required">*</span></label>
                <input 
                  id="id"
                  name="id" 
                  type="number" 
                  value={form.id} 
                  onChange={handleChange} 
                  placeholder="Enter unique ID"
                  required 
                />
              </div>

              <div className="form-group">
                <label htmlFor="company_name">Company Name <span className="required">*</span></label>
                <input 
                  id="company_name"
                  name="company_name" 
                  value={form.company_name} 
                  onChange={handleChange}
                  placeholder="Enter company name"
                  required 
                />
              </div>

              <div className="form-group full-width">
                <label htmlFor="company_description">Description</label>
                <textarea 
                  id="company_description"
                  name="company_description" 
                  value={form.company_description} 
                  onChange={handleChange}
                  placeholder="Brief description of the company"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label htmlFor="company_email">Email Address</label>
                <input 
                  id="company_email"
                  name="company_email" 
                  type="email" 
                  value={form.company_email} 
                  onChange={handleChange}
                  placeholder="company@example.com"
                />
              </div>

              <div className="form-group">
                <label htmlFor="state_code">State Code <span className="required">*</span></label>
                <input 
                  id="state_code"
                  name="state_code" 
                  value={form.state_code} 
                  onChange={handleChange}
                  placeholder="e.g., MH, GJ, DL"
                  required 
                />
              </div>

              <div className="form-group">
                <label htmlFor="demand_date">Demand Date <span className="required">*</span></label>
                <input 
                  id="demand_date"
                  name="demand_date" 
                  type="date" 
                  value={form.demand_date} 
                  onChange={handleChange} 
                  required 
                />
              </div>

              <div className="form-group">
                <label htmlFor="demand_MU">Energy Demand (MU) <span className="required">*</span></label>
                <input 
                  id="demand_MU"
                  name="demand_MU" 
                  type="number" 
                  step="0.01" 
                  value={form.demand_MU} 
                  onChange={handleChange}
                  placeholder="0.00"
                  required 
                />
              </div>
            </div>

            {error && (
              <div className="alert alert-error">
                <span className="alert-icon">⚠️</span>
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="alert alert-success">
                <span className="alert-icon">✅</span>
                <span>{success}</span>
              </div>
            )}

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? '⏳ Saving...' : '💾 Save Company'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
                ← Back
              </button>
            </div>
          </form>
        </Card>

        <Card>
          <div className="card-header">
            <h2>Registered Companies</h2>
            <p>Total: {companies.length} companies</p>
          </div>

          {listLoading ? (
            <LoadingSpinner />
          ) : companies.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <p>No companies registered yet</p>
              <p className="empty-subtitle">Fill out the form above to register a new company</p>
            </div>
          ) : (
            <div className="companies-table-container">
              <table className="companies-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Company Name</th>
                    <th>Email</th>
                    <th>State</th>
                    <th>Demand Date</th>
                    <th>Demand (MU)</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((c) => (
                    <tr key={c._id || c.id}>
                      <td className="id-cell">{c.id ?? c._id}</td>
                      <td className="name-cell">
                        <div className="company-name">{c.company_name}</div>
                        {c.company_description && (
                          <div className="company-desc">{c.company_description}</div>
                        )}
                      </td>
                      <td className="email-cell">{c.company_email || '—'}</td>
                      <td className="state-cell">
                        <span className="state-badge">{c.state_code}</span>
                      </td>
                      <td className="date-cell">
                        {new Date(c.demand_date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </td>
                      <td className="demand-cell">{Number(c.demand_MU).toFixed(2)}</td>
                      <td className="actions-cell">
                        <button
                          className="btn-delete"
                          onClick={async () => {
                            if (!window.confirm(`Delete ${c.company_name}?`)) return;
                            const idToDelete = c.id;
                            if (idToDelete == null) {
                              alert('Cannot delete: company has no numeric id');
                              return;
                            }
                            const resp = await deleteCompany(idToDelete);
                            if (resp && resp.success) {
                              fetchCompanies();
                            } else {
                              alert(resp?.message || 'Failed to delete');
                            }
                          }}
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Companies;
