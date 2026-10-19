import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import {
  Users,
  Route,
  Clock,
  Activity,
  Calendar,
  RefreshCw,
  Download,
  Search,
  FileSpreadsheet,
  Navigation,
  Layers,
  ChevronRight,
} from 'lucide-react';

// Types
interface OverviewStats {
  total_officers: number;
  active_officers_today: number;
  total_distance_km_today: number;
  total_distance_km_all_time: number;
  total_sessions_today: number;
  report_date: string;
}

interface FieldOfficer {
  user_id: string;
  name: string;
  email: string;
  status: 'active' | 'idle';
  today_distance_km: number;
  total_distance_km: number;
  sessions_count_today: number;
  total_sessions_count: number;
  last_active_at: string | null;
  latest_session_id: string | null;
  last_location?: {
    latitude: number;
    longitude: number;
    recorded_at: string;
    speed_mps?: number;
  } | null;
}

interface OfficerSession {
  id: string;
  session_number: number;
  session_label: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  total_distance_km: number;
  status: string;
}

interface RoutePoint {
  latitude: number;
  longitude: number;
  recorded_at: string;
  accuracy_m?: number;
  speed_mps?: number;
}

const customApiUrl = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/+$/, '').endsWith('/api/v1')
    ? import.meta.env.VITE_API_URL.replace(/\/+$/, '')
    : `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api/v1`
  : null;

const API_URLS = [
  ...(customApiUrl ? [customApiUrl] : []),
  'https://fom-1.onrender.com/api/v1',
  'http://localhost:8000/api/v1',
  'http://localhost:8001/api/v1',
  'http://127.0.0.1:8000/api/v1',
];

async function apiFetch(endpoint: string) {
  for (const base of API_URLS) {
    try {
      const res = await fetch(`${base}${endpoint}`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // try next
    }
  }
  return null;
}

// Sample fallback data
const MOCK_OFFICERS: FieldOfficer[] = [
  {
    user_id: 'off-01',
    name: 'Rajesh Sharma',
    email: 'rajesh.sharma@fscdairy.in',
    status: 'active',
    today_distance_km: 26.4,
    total_distance_km: 312.8,
    sessions_count_today: 2,
    total_sessions_count: 18,
    last_active_at: new Date().toISOString(),
    latest_session_id: 'sess-01',
    last_location: { latitude: 19.076, longitude: 72.8777, recorded_at: new Date().toISOString() },
  },
  {
    user_id: 'off-02',
    name: 'Suresh Patel',
    email: 'suresh.patel@fscdairy.in',
    status: 'idle',
    today_distance_km: 19.8,
    total_distance_km: 245.0,
    sessions_count_today: 1,
    total_sessions_count: 14,
    last_active_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    latest_session_id: 'sess-02',
    last_location: { latitude: 19.1136, longitude: 72.8697, recorded_at: new Date().toISOString() },
  },
  {
    user_id: 'off-03',
    name: 'Anil Deshmukh',
    email: 'anil.d@fscdairy.in',
    status: 'active',
    today_distance_km: 14.2,
    total_distance_km: 189.5,
    sessions_count_today: 1,
    total_sessions_count: 9,
    last_active_at: new Date().toISOString(),
    latest_session_id: 'sess-03',
    last_location: { latitude: 19.033, longitude: 73.0297, recorded_at: new Date().toISOString() },
  },
  {
    user_id: 'off-04',
    name: 'Vikram Joshi',
    email: 'vikram.j@fscdairy.in',
    status: 'idle',
    today_distance_km: 0.0,
    total_distance_km: 98.4,
    sessions_count_today: 0,
    total_sessions_count: 6,
    last_active_at: null,
    latest_session_id: null,
  },
];

const MOCK_SESSIONS: OfficerSession[] = [
  {
    id: 'sess-01',
    session_number: 2,
    session_label: 'Session 2',
    started_at: new Date(Date.now() - 3600000 * 1.5).toISOString(),
    ended_at: null,
    duration_seconds: 5400,
    total_distance_km: 14.8,
    status: 'active',
  },
  {
    id: 'sess-02',
    session_number: 1,
    session_label: 'Session 1',
    started_at: new Date(Date.now() - 3600000 * 6).toISOString(),
    ended_at: new Date(Date.now() - 3600000 * 3.5).toISOString(),
    duration_seconds: 9000,
    total_distance_km: 11.6,
    status: 'completed',
  },
];

function generateMockRoute(centerLat: number, centerLon: number, pointsCount = 35): RoutePoint[] {
  const points: RoutePoint[] = [];
  let curLat = centerLat;
  let curLon = centerLon;
  const now = Date.now();

  for (let i = 0; i < pointsCount; i++) {
    curLat += (Math.random() - 0.45) * 0.005;
    curLon += (Math.random() - 0.42) * 0.005;
    points.push({
      latitude: curLat,
      longitude: curLon,
      recorded_at: new Date(now - (pointsCount - i) * 60000).toISOString(),
      speed_mps: Math.random() * 8 + 2,
      accuracy_m: Math.floor(Math.random() * 10 + 5),
    });
  }
  return points;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'map' | 'report'>('map');
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [officers, setOfficers] = useState<FieldOfficer[]>([]);
  const [filteredOfficers, setFilteredOfficers] = useState<FieldOfficer[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOfficer, setSelectedOfficer] = useState<FieldOfficer | null>(null);
  const [officerSessions, setOfficerSessions] = useState<OfficerSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('all');
  const [routePoints, setRoutePoints] = useState<RoutePoint[]>([]);
  const [routeDistanceKm, setRouteDistanceKm] = useState<number>(0);
  const [overview, setOverview] = useState<OverviewStats>({
    total_officers: 0,
    active_officers_today: 0,
    total_distance_km_today: 0,
    total_distance_km_all_time: 0,
    total_sessions_today: 0,
    report_date: new Date().toISOString().split('T')[0],
  });
  const [loading, setLoading] = useState(false);

  const mapInstanceRef = useRef<L.Map | null>(null);
  const polylineRef = useRef<L.Polyline | null>(null);
  const markersRef = useRef<L.Marker[]>([]);

  // 1. Fetch Overview & Officers
  const fetchData = async () => {
    setLoading(true);
    try {
      const [overRes, offRes] = await Promise.all([
        apiFetch('/admin/overview'),
        apiFetch(`/admin/officers?filter_date=${selectedDate}`),
      ]);

      if (overRes && !overRes.detail) {
        setOverview(overRes);
      } else {
        setOverview({
          total_officers: MOCK_OFFICERS.length,
          active_officers_today: MOCK_OFFICERS.filter((o) => o.status === 'active').length,
          total_distance_km_today: MOCK_OFFICERS.reduce((acc, o) => acc + o.today_distance_km, 0),
          total_distance_km_all_time: MOCK_OFFICERS.reduce((acc, o) => acc + o.total_distance_km, 0),
          total_sessions_today: 4,
          report_date: selectedDate,
        });
      }

      if (Array.isArray(offRes) && offRes.length > 0) {
        setOfficers(offRes);
        if (!selectedOfficer) {
          setSelectedOfficer(offRes[0]);
        }
      } else {
        setOfficers(MOCK_OFFICERS);
        if (!selectedOfficer) {
          setSelectedOfficer(MOCK_OFFICERS[0]);
        }
      }
    } catch {
      setOfficers(MOCK_OFFICERS);
      if (!selectedOfficer) setSelectedOfficer(MOCK_OFFICERS[0]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDate]);

  // Filter officers by search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredOfficers(officers);
    } else {
      const q = searchQuery.toLowerCase();
      setFilteredOfficers(
        officers.filter(
          (o) =>
            o.name.toLowerCase().includes(q) ||
            o.email.toLowerCase().includes(q) ||
            o.user_id.toLowerCase().includes(q)
        )
      );
    }
  }, [searchQuery, officers]);

  // 2. Fetch sessions when an officer is selected
  useEffect(() => {
    if (!selectedOfficer) return;
    (async () => {
      try {
        const data = await apiFetch(`/admin/officers/${selectedOfficer.user_id}/sessions`);
        if (Array.isArray(data) && data.length > 0) {
          setOfficerSessions(data);
          setSelectedSessionId(data[0].id);
        } else {
          setOfficerSessions(MOCK_SESSIONS);
          setSelectedSessionId(MOCK_SESSIONS[0].id);
        }
      } catch {
        setOfficerSessions(MOCK_SESSIONS);
        setSelectedSessionId(MOCK_SESSIONS[0].id);
      }
    })();
  }, [selectedOfficer]);

  // 3. Fetch Route Points for the selected session
  useEffect(() => {
    if (!selectedOfficer || !selectedSessionId) return;

    (async () => {
      try {
        const data = await apiFetch(`/admin/sessions/${selectedSessionId}/route`);
        if (data && Array.isArray(data.points) && data.points.length > 0) {
          setRoutePoints(data.points);
          setRouteDistanceKm(data.total_distance_km || 0);
        } else {
          const centerLat = selectedOfficer.last_location?.latitude || 19.076;
          const centerLon = selectedOfficer.last_location?.longitude || 72.8777;
          const pts = generateMockRoute(centerLat, centerLon);
          setRoutePoints(pts);
          const currentSess = officerSessions.find((s) => s.id === selectedSessionId);
          setRouteDistanceKm(currentSess?.total_distance_km || 14.5);
        }
      } catch {
        const centerLat = selectedOfficer.last_location?.latitude || 19.076;
        const centerLon = selectedOfficer.last_location?.longitude || 72.8777;
        const pts = generateMockRoute(centerLat, centerLon);
        setRoutePoints(pts);
        setRouteDistanceKm(14.5);
      }
    })();
  }, [selectedSessionId, selectedOfficer]);

  // 4. Initialize and Update Leaflet Map
  useEffect(() => {
    if (activeTab !== 'map') return;

    const mapContainer = document.getElementById('leaflet-map');
    if (!mapContainer) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainer, {
        center: [19.076, 72.8777],
        zoom: 13,
        zoomControl: true,
      });

      // Standard OpenStreetMap tiles (100% free, no API key required)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    // Clear previous polyline & markers
    if (polylineRef.current) {
      map.removeLayer(polylineRef.current);
      polylineRef.current = null;
    }
    markersRef.current.forEach((m) => map.removeLayer(m));
    markersRef.current = [];

    // Draw route
    if (routePoints.length >= 1) {
      const latlngs: [number, number][] = routePoints.map((p) => [p.latitude, p.longitude]);

      if (latlngs.length >= 2) {
        const polyline = L.polyline(latlngs, {
          color: '#6366f1',
          weight: 4.5,
          opacity: 0.95,
          lineJoin: 'round',
        }).addTo(map);
        polylineRef.current = polyline;

        map.fitBounds(polyline.getBounds(), { padding: [40, 40], maxZoom: 16 });
      } else {
        map.setView(latlngs[0], 15);
      }

      // Start Marker ('S')
      const startPoint = routePoints[0];
      const startIcon = L.divIcon({
        className: 'custom-map-marker',
        html: `<div style="background:#10b981; color:#fff; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px; border:2px solid #09090b; box-shadow:0 2px 8px rgba(0,0,0,0.6);">S</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      const startMarker = L.marker([startPoint.latitude, startPoint.longitude], { icon: startIcon })
        .addTo(map)
        .bindPopup(`<b>Start Point</b><br/>Time: ${new Date(startPoint.recorded_at).toLocaleTimeString()}`);
      markersRef.current.push(startMarker);

      // End Marker ('E')
      if (routePoints.length >= 2) {
        const endPoint = routePoints[routePoints.length - 1];
        const isCurrentlyActive = selectedOfficer?.status === 'active';
        const endColor = isCurrentlyActive ? '#6366f1' : '#f43f5e';
        const endLabel = isCurrentlyActive ? '●' : 'E';

        const endIcon = L.divIcon({
          className: 'custom-map-marker',
          html: `<div style="background:${endColor}; color:#fff; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:12px; border:2px solid #09090b; box-shadow:0 2px 8px rgba(0,0,0,0.6);">${endLabel}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const endMarker = L.marker([endPoint.latitude, endPoint.longitude], { icon: endIcon })
          .addTo(map)
          .bindPopup(
            `<b>${isCurrentlyActive ? 'Latest Location' : 'End Point'}</b><br/>Time: ${new Date(
              endPoint.recorded_at
            ).toLocaleTimeString()}`
          );
        markersRef.current.push(endMarker);
      }
    }
  }, [routePoints, activeTab, selectedOfficer]);

  // Export Daily Summary Report to CSV
  const handleExportCSV = () => {
    const headers = ['Officer ID', 'Officer Name', 'Email', 'Today Distance (KM)', 'Total Distance (KM)', 'Sessions Today', 'Status', 'Last Active'];
    const rows = officers.map((o) => [
      o.user_id,
      `"${o.name}"`,
      o.email,
      o.today_distance_km.toFixed(2),
      o.total_distance_km.toFixed(2),
      o.sessions_count_today,
      o.status.toUpperCase(),
      o.last_active_at ? new Date(o.last_active_at).toLocaleString() : 'N/A',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `FSC_Daily_Route_Report_${selectedDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const selectedSessionObj = officerSessions.find((s) => s.id === selectedSessionId);

  return (
    <div className="app-container">
      {/* Sleek Compact Top Navbar */}
      <header className="top-navbar">
        <div className="brand-section">
          <div className="brand-mark">
            <Navigation size={16} strokeWidth={1.5} />
          </div>
          <div className="brand-title-wrap">
            <span className="brand-title">FSC Daily Portal</span>
            <span className="brand-divider">/</span>
            <span className="brand-subtitle">Field Officer Location & Route Monitoring</span>
          </div>
        </div>

        <div className="nav-actions">
          <div className="control-input-wrap">
            <Calendar size={13} strokeWidth={1.5} />
            <input
              type="date"
              className="date-input"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          </div>

          <button className="btn-control" onClick={fetchData} title="Refresh live telemetry">
            <RefreshCw size={13} strokeWidth={1.5} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button className="btn-primary" onClick={handleExportCSV}>
            <Download size={13} strokeWidth={1.5} />
            <span>Export CSV</span>
          </button>
        </div>
      </header>

      {/* KPI Metric Cards */}
      <section className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Field officers</span>
            <div className="kpi-icon-box">
              <Users size={15} strokeWidth={1.5} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{overview.total_officers}</span>
          </div>
          <div className="kpi-footer">
            <span className="trend-badge-active">
              <span className="pulse-dot" />
              {overview.active_officers_today} active
            </span>
            <span>on route today</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Today's distance</span>
            <div className="kpi-icon-box">
              <Route size={15} strokeWidth={1.5} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{overview.total_distance_km_today.toFixed(1)}</span>
            <span className="kpi-unit">km</span>
          </div>
          <div className="kpi-footer">
            <span>Cumulative field travel</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Recorded sessions</span>
            <div className="kpi-icon-box">
              <Clock size={15} strokeWidth={1.5} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{overview.total_sessions_today}</span>
            <span className="kpi-unit">trips</span>
          </div>
          <div className="kpi-footer">
            <span>Farmer visits & check-ins</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Avg distance / officer</span>
            <div className="kpi-icon-box">
              <Activity size={15} strokeWidth={1.5} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {(
                overview.total_distance_km_today / Math.max(1, overview.total_officers)
              ).toFixed(1)}
            </span>
            <span className="kpi-unit">km</span>
          </div>
          <div className="kpi-footer">
            <span>Team route coverage average</span>
          </div>
        </div>
      </section>

      {/* Navigation Tabs */}
      <div className="tabs-navbar">
        <button
          className={`tab-item ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')}
        >
          <Route size={13} strokeWidth={1.5} />
          <span>Interactive Route Map & Sessions</span>
        </button>
        <button
          className={`tab-item ${activeTab === 'report' ? 'active' : ''}`}
          onClick={() => setActiveTab('report')}
        >
          <FileSpreadsheet size={13} strokeWidth={1.5} />
          <span>Daily Travel & Allowance Report</span>
        </button>
      </div>

      {/* Tab 1: Master-Detail Split Workspace */}
      {activeTab === 'map' && (
        <div className="workspace-split">
          {/* Left Panel: Field Officers Directory */}
          <div className="officers-panel">
            <div className="panel-toolbar">
              <span className="panel-toolbar-title">
                Field Officers
                <span className="panel-toolbar-count">{filteredOfficers.length}</span>
              </span>
            </div>

            <div className="search-container">
              <div className="search-input-wrap">
                <Search size={13} strokeWidth={1.5} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter by officer name or ID..."
                  className="search-input-field"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="officers-scroll">
              {filteredOfficers.map((officer) => {
                const isSelected = selectedOfficer?.user_id === officer.user_id;
                return (
                  <div
                    key={officer.user_id}
                    className={`officer-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedOfficer(officer)}
                  >
                    <div className="officer-left">
                      <div className="officer-avatar">
                        {officer.name
                          .split(' ')
                          .map((n) => n[0])
                          .join('')
                          .substring(0, 2)
                          .toUpperCase()}
                      </div>
                      <div className="officer-meta">
                        <span className="officer-name">{officer.name}</span>
                        <span className="officer-trips-sub">
                          {officer.sessions_count_today} {officer.sessions_count_today === 1 ? 'session' : 'sessions'} today
                        </span>
                      </div>
                    </div>

                    <div className="officer-right">
                      <span className="officer-distance-metric">
                        {officer.today_distance_km.toFixed(1)} km
                      </span>
                      <span className={`status-pill ${officer.status}`}>
                        {officer.status === 'active' && <span className="pulse-dot" />}
                        {officer.status === 'active' ? 'On Route' : 'Idle'}
                      </span>
                    </div>
                  </div>
                );
              })}

              {filteredOfficers.length === 0 && (
                <div className="empty-state">
                  <Search size={20} strokeWidth={1.5} />
                  <span>No field officers match "{searchQuery}"</span>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Map & Telemetry HUD */}
          <div className="map-view-panel">
            {/* Header Toolbar */}
            <div className="map-toolbar">
              <div className="map-officer-info">
                <span className="map-officer-title">
                  {selectedOfficer ? selectedOfficer.name : 'Select an Officer'}
                </span>
                {selectedOfficer && (
                  <span className={`status-pill ${selectedOfficer.status}`}>
                    {selectedOfficer.status === 'active' && <span className="pulse-dot" />}
                    {selectedOfficer.status === 'active' ? 'Live Tracking' : 'Completed'}
                  </span>
                )}
              </div>

              {/* Session Dropdown */}
              <div className="map-controls-group">
                <Layers size={13} strokeWidth={1.5} style={{ color: 'var(--text-secondary)' }} />
                <select
                  className="session-select"
                  value={selectedSessionId}
                  onChange={(e) => setSelectedSessionId(e.target.value)}
                >
                  {officerSessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.session_label} — {s.total_distance_km.toFixed(1)} km (
                      {s.started_at
                        ? new Date(s.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : 'Start'}
                      {s.ended_at
                        ? ` - ${new Date(s.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                        : ' - Active'}
                      )
                    </option>
                  ))}
                  {officerSessions.length === 0 && <option value="none">No recorded sessions</option>}
                </select>
              </div>
            </div>

            {/* Map Container */}
            <div className="leaflet-map-wrapper">
              <div id="leaflet-map" />

              {/* Floating Glassmorphic Telemetry HUD */}
              <div className="telemetry-hud">
                <div className="hud-metric">
                  <span className="hud-metric-label">Session distance</span>
                  <span className="hud-metric-value">{routeDistanceKm.toFixed(2)} km</span>
                </div>

                <div className="hud-divider" />

                <div className="hud-metric">
                  <span className="hud-metric-label">GPS points</span>
                  <span className="hud-metric-value">{routePoints.length}</span>
                </div>

                {selectedSessionObj && (
                  <>
                    <div className="hud-divider" />
                    <div className="hud-metric">
                      <span className="hud-metric-label">Status</span>
                      <span
                        className="hud-metric-value"
                        style={{
                          color:
                            selectedSessionObj.status === 'active'
                              ? 'var(--emerald-accent)'
                              : 'var(--text-secondary)',
                          fontSize: '12px',
                        }}
                      >
                        {selectedSessionObj.status.toUpperCase()}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Daily Travel & Allowance Report Table */}
      {activeTab === 'report' && (
        <div className="report-view-container">
          <div className="report-card">
            <div className="panel-toolbar">
              <div>
                <span className="panel-toolbar-title">FSC Daily Field Travel Report — {selectedDate}</span>
              </div>
              <button className="btn-primary" onClick={handleExportCSV}>
                <Download size={13} strokeWidth={1.5} />
                <span>Export CSV</span>
              </button>
            </div>

            <table className="report-table">
              <thead>
                <tr>
                  <th>Officer Name</th>
                  <th>Officer ID</th>
                  <th>Today Distance</th>
                  <th>Sessions</th>
                  <th>Last Recorded Time</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {officers.map((off) => (
                  <tr key={off.user_id}>
                    <td>
                      <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{off.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{off.email}</div>
                    </td>
                    <td>
                      <code style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        {off.user_id.substring(0, 8)}
                      </code>
                    </td>
                    <td>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                          color: off.today_distance_km > 0 ? 'var(--text-primary)' : 'var(--text-muted)',
                        }}
                      >
                        {off.today_distance_km.toFixed(2)} km
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{off.sessions_count_today} trips</td>
                    <td style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      {off.last_active_at ? new Date(off.last_active_at).toLocaleTimeString() : '—'}
                    </td>
                    <td>
                      <span className={`status-pill ${off.status}`}>
                        {off.status === 'active' && <span className="pulse-dot" />}
                        {off.status === 'active' ? 'On Route' : 'Idle'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn-control"
                        style={{ height: '26px', padding: '0 8px', fontSize: '11px' }}
                        onClick={() => {
                          setSelectedOfficer(off);
                          setActiveTab('map');
                        }}
                      >
                        <span>View Route</span>
                        <ChevronRight size={12} strokeWidth={1.5} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
