import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getPlantDetails } from '../services/plant_service';
import { runDataUpdate } from '../services/admin_service';
import { FaUserCircle, FaSearch, FaSyncAlt } from 'react-icons/fa';
import '../styles/Navbar.css';

const Navbar = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [updating, setUpdating] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Keep the navbar search in sync with the URL when on the plants page.
  // Do NOT clear the input when on other pages so user-typed text is preserved.
  React.useEffect(() => {
    if (location.pathname === '/plants') {
      const params = new URLSearchParams(location.search);
      const searchParam = params.get('search') || '';
      setSearchQuery(searchParam);
    }
    // Intentionally do not clear the searchQuery when on other routes.
  }, [location.pathname, location.search]);

  const handleSearch = async (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) {
      navigate('/plants');
      return;
    }

    // Try exact Plant_ID lookup first; if found go directly to details page.
    try {
      const resp = await getPlantDetails(q);
      if (resp && resp.success && resp.data) {
        // Navigate to plant details and preserve no extra state
        navigate(`/plants/${encodeURIComponent(q)}`);
        return;
      }
    } catch (err) {
      // Ignore errors and fall back to list search
      console.debug('Exact plant lookup failed, falling back to list search', err);
    }

    // Fallback: navigate to plants list filtered by search
    navigate(`/plants?search=${encodeURIComponent(q)}`);
  };

  // Use keyDown for more consistent Enter handling
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      // Prevent the form submitting twice; delegate to handleSearch
      e.preventDefault();
      handleSearch(e);
    }
  };

  const handleDataUpdate = async () => {
    if (updating) return;
    
    const confirmUpdate = window.confirm(
      'This will run the data update pipeline:\n\n' +
      '1. Web scraping\n' +
      '2. Data parsing (3 stages)\n' +
      '3. Database updates\n\n' +
      'This may take several minutes. Continue?'
    );
    
    if (!confirmUpdate) return;
    
    setUpdating(true);
    try {
      const response = await runDataUpdate();
      if (response.success) {
        alert(`✅ Data update completed successfully!\n\n${response.message || ''}`);
        // Optionally refresh the current page
        window.location.reload();
      } else {
        alert(`⚠️ Update completed with issues:\n\n${response.error || response.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Update error:', error);
      alert(`❌ Update failed:\n\n${error.message || 'Server error'}`);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h2>⚡ Energy Monitor</h2>
      </div>
      
      <form className="navbar-search" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search plants..."
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" className="search-btn" aria-label="Search">
          <FaSearch />
        </button>
      </form>
      
      <div className="navbar-actions">
        <button 
          className={`navbar-btn update-btn ${updating ? 'updating' : ''}`}
          onClick={handleDataUpdate}
          disabled={updating}
          title="Run data update pipeline"
        >
          <FaSyncAlt className={updating ? 'spinning' : ''} />
          <span>{updating ? 'Updating...' : 'Update'}</span>
        </button>
        <button className="navbar-btn" aria-label="Profile" onClick={() => navigate('/companies')}>
          <FaUserCircle />
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
