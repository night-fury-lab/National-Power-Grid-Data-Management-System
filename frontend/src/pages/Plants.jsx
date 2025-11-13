import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getAllPlants, getFilterStates, getFilterSectors, getFilterTypes } from '../services/plant_service';
import Card from '../components/Card';
import Table from '../components/Table';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/Plants.css';

const Plants = () => {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Initialize search and page from the URL to avoid a double-fetch on mount
  const paramsInit = new URLSearchParams(location.search);
  const initialSearch = paramsInit.get('search') || '';
  const initialPage = parseInt(paramsInit.get('page') || '1', 10) || 1;
  const initialState = paramsInit.get('state') || '';
  const initialSector = paramsInit.get('sector') || '';
  const initialType = paramsInit.get('type') || '';
  
  const [search, setSearch] = useState(initialSearch);
  const [searchInput, setSearchInput] = useState(initialSearch); // Local state for input (not debounced)
  const [page, setPage] = useState(initialPage);
  const [pagination, setPagination] = useState({});
  const [selectedState, setSelectedState] = useState(initialState);
  const [selectedSector, setSelectedSector] = useState(initialSector);
  const [selectedType, setSelectedType] = useState(initialType);
  
  // Filter options
  const [states, setStates] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [types, setTypes] = useState([]);
  

  // Note: search/page are initialized from location.search above to avoid
  // fetching the default page first and then immediately fetching the correct
  // page. The sync effect below keeps state updated if the URL changes later.

  // Fetch filter options on mount
  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        const [statesRes, sectorsRes, typesRes] = await Promise.all([
          getFilterStates(),
          getFilterSectors(),
          getFilterTypes()
        ]);
        setStates(statesRes.data || []);
        setSectors(sectorsRes.data || []);
        setTypes(typesRes.data || []);
      } catch (error) {
        console.error('Error fetching filter options:', error);
      }
    };
    fetchFilterOptions();
  }, []);

  // Sync with URL changes from external navigation (e.g., navbar search)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const searchParam = params.get('search') || '';
    const pageParam = parseInt(params.get('page') || '1', 10) || 1;
    // If URL changed externally, update local state
    if (searchParam !== searchInput || pageParam !== page) {
      setSearch(searchParam);
      setSearchInput(searchParam);
      setPage(pageParam);
    }
  }, [location.search]);

  const fetchPlants = React.useCallback(async (overrideSearch = null) => {
    try {
      setLoading(true);
      const searchParam = (overrideSearch !== null ? overrideSearch : search).trim();
      const response = await getAllPlants({ 
        page, 
        per_page: 20, 
        ...(searchParam ? { search: searchParam } : {}),
        ...(selectedState ? { state: selectedState } : {}),
        ...(selectedSector ? { sector: selectedSector } : {}),
        ...(selectedType ? { type: selectedType } : {})
      });
      
      if (response && response.success !== false) {
        setPlants(response.data || []);
        setPagination(response.pagination || {});
      } else {
        console.error('API returned error:', response?.error);
        setPlants([]);
        setPagination({});
      }
    } catch (error) {
      console.error('Error fetching plants:', error);
      setPlants([]);
      setPagination({});
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedState, selectedSector, selectedType]);

  // Debounce search input changes - update search state and URL after user stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== search) {
        setSearch(searchInput);
        setPage(1);
        
        // Update URL without causing navigation/re-render
        const params = new URLSearchParams();
        if (searchInput.trim()) {
          params.set('search', searchInput.trim());
        }
        const newSearch = params.toString();
        const newUrl = newSearch ? `/plants?${newSearch}` : '/plants';
        window.history.replaceState({}, '', newUrl);
      }
    }, 500); // Wait 500ms after user stops typing

    return () => clearTimeout(timer);
  }, [searchInput, search]);

  // Fetch plants when search or page changes
  useEffect(() => {
    fetchPlants();
  }, [fetchPlants]);

  const columns = [
    { header: 'Plant ID', accessor: 'Plant_ID' },
    { header: 'Plant Name', accessor: 'Plant_Name' },
    { header: 'State', accessor: 'State_Code' },
    { header: 'Sector', accessor: 'Sector_ID' },
    { header: 'Type', accessor: 'Type_ID' }
  ];

  const handleRowClick = (plant) => {
    // Pass current search and page in navigation state so details page can return back
    navigate(`/plants/${plant.Plant_ID}`, { state: { search, page } });
  };

  const handleSearchChange = (e) => {
    // Only update local input state - don't trigger search or URL update yet
    setSearchInput(e.target.value);
  };

  const handleSearchKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const trimmedSearch = searchInput.trim();
      // Force immediate search on Enter - update both states
      setSearch(trimmedSearch);
      setPage(1);
      
      // Update URL immediately on Enter (include page=1)
      const params = new URLSearchParams();
      if (trimmedSearch) params.set('search', trimmedSearch);
      params.set('page', '1');
      const newSearch = params.toString();
      const newUrl = newSearch ? `/plants?${newSearch}` : '/plants';
      window.history.replaceState({}, '', newUrl);
      
      // Trigger immediate fetch with the new search value
      fetchPlants(trimmedSearch);
    }
  };

  const changePage = (newPage) => {
    setPage(newPage);

    // Update URL to include both search and page
    const params = new URLSearchParams();
    if (search && search.trim()) params.set('search', search.trim());
    if (newPage && newPage > 1) params.set('page', String(newPage));
    if (selectedState) params.set('state', selectedState);
    if (selectedSector) params.set('sector', selectedSector);
    if (selectedType) params.set('type', selectedType);
    const newSearch = params.toString();
    const newUrl = newSearch ? `/plants?${newSearch}` : '/plants';
    window.history.replaceState({}, '', newUrl);
  };

  const handleFilterChange = (filterType, value) => {
    // Reset page to 1 when filters change
    setPage(1);
    
    if (filterType === 'state') setSelectedState(value);
    if (filterType === 'sector') setSelectedSector(value);
    if (filterType === 'type') setSelectedType(value);
    
    // Update URL
    const params = new URLSearchParams();
    if (search && search.trim()) params.set('search', search.trim());
    params.set('page', '1');
    if (filterType === 'state') {
      if (value) params.set('state', value);
    } else if (selectedState) {
      params.set('state', selectedState);
    }
    if (filterType === 'sector') {
      if (value) params.set('sector', value);
    } else if (selectedSector) {
      params.set('sector', selectedSector);
    }
    if (filterType === 'type') {
      if (value) params.set('type', value);
    } else if (selectedType) {
      params.set('type', selectedType);
    }
    const newSearch = params.toString();
    const newUrl = newSearch ? `/plants?${newSearch}` : '/plants';
    window.history.replaceState({}, '', newUrl);
  };

  const clearFilters = () => {
    setSelectedState('');
    setSelectedSector('');
    setSelectedType('');
    setSearch('');
    setSearchInput('');
    setPage(1);
    window.history.replaceState({}, '', '/plants');
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="plants-page">
      <div className="page-header">
        <h1>⚡ Power Plants</h1>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search plants..."
            value={searchInput}
            onChange={handleSearchChange}
            onKeyPress={handleSearchKeyPress}
            className="search-input"
          />
        </div>
      </div>

      <div className="filters-container">
        <div className="filter-group">
          <label htmlFor="state-filter">State:</label>
          <select
            id="state-filter"
            value={selectedState}
            onChange={(e) => handleFilterChange('state', e.target.value)}
            className="filter-select"
          >
            <option value="">All States</option>
            {states.map(state => (
              <option key={state.code} value={state.code}>
                {state.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="sector-filter">Sector:</label>
          <select
            id="sector-filter"
            value={selectedSector}
            onChange={(e) => handleFilterChange('sector', e.target.value)}
            className="filter-select"
          >
            <option value="">All Sectors</option>
            {sectors.map(sector => (
              <option key={sector.id} value={sector.id}>
                {sector.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="type-filter">Energy Type:</label>
          <select
            id="type-filter"
            value={selectedType}
            onChange={(e) => handleFilterChange('type', e.target.value)}
            className="filter-select"
          >
            <option value="">All Types</option>
            {types.map(type => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
        </div>

        {(selectedState || selectedSector || selectedType || search) && (
          <button onClick={clearFilters} className="clear-filters-btn">
            Clear Filters
          </button>
        )}
      </div>

      <Card>
        <Table columns={columns} data={plants} onRowClick={handleRowClick} />
        
        <div className="pagination">
          <button 
            disabled={page === 1} 
            onClick={() => changePage(page - 1)}
          >
            Previous
          </button>
          <span>Page {page} of {pagination.pages || 1}</span>
          <button 
            disabled={page === pagination.pages} 
            onClick={() => changePage(page + 1)}
          >
            Next
          </button>
        </div>
      </Card>
    </div>
  );
};

export default Plants;
