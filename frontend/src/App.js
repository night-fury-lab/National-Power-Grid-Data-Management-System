import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Plants from './pages/Plants';
import PlantDetails from './pages/PlantDetails';
import Analytics from './pages/Analytics';
import Regions from './pages/Regions';
import Alerts from './pages/Alerts';
import Admin from './pages/Admin';
import Companies from './pages/Companies';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <div className="app-container">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/plants" element={<Plants />} />
              <Route path="/plants/:plantId" element={<PlantDetails />} />
              <Route path="/companies" element={<Companies />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/regions" element={<Regions />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
