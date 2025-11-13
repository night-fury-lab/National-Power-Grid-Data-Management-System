import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaHome, FaPlug, FaChartBar, FaMap, FaBell } from 'react-icons/fa';
import '../styles/Sidebar.css';

const Sidebar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path ? 'active' : '';

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        <Link to="/" className={`sidebar-item ${isActive('/')}`}>
          <FaHome className="sidebar-icon" />
          <span className="sidebar-label">Dashboard</span>
        </Link>
        
        <Link to="/plants" className={`sidebar-item ${isActive('/plants')}`}>
          <FaPlug className="sidebar-icon" />
          <span className="sidebar-label">Plants</span>
        </Link>
        
        <Link to="/analytics" className={`sidebar-item ${isActive('/analytics')}`}>
          <FaChartBar className="sidebar-icon" />
          <span className="sidebar-label">Analytics</span>
        </Link>
        
        {/* Companies moved to Navbar profile icon - removed from sidebar */}
        
        <Link to="/regions" className={`sidebar-item ${isActive('/regions')}`}>
          <FaMap className="sidebar-icon" />
          <span className="sidebar-label">Regions</span>
        </Link>
        
        <Link to="/alerts" className={`sidebar-item ${isActive('/alerts')}`}>
          <FaBell className="sidebar-icon" />
          <span className="sidebar-label">Alerts</span>
        </Link>
        
        <Link to="/admin" className={`sidebar-item ${isActive('/admin')}`}>
          <FaChartBar className="sidebar-icon" />
          <span className="sidebar-label">Admin</span>
        </Link>
      </nav>
    </aside>
  );
};

export default Sidebar;
