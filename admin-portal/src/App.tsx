import React, { useState, useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
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
  ChevronDown,
  ChevronUp,
  LogIn,
  UserCheck,
  MapPin,
  CheckCircle,
  AlertCircle,
  Shield,
  Phone,
  User,
} from 'lucide-react';
import { exportAdminVisitPDF } from './utils/pdfExport';
import './index.css';

// ─── Types ────────────────────────────────────────────────────────────────────

interface VisitEntry {
  id: string;
  user_id: string;
  customer_id: string;
  checked_in_at: string;
  checked_out_at?: string | null;
  duration_minutes?: number | null;
  checkin_lat?: number | null;
  checkin_lng?: number | null;
  notes?: string | null;
  sync_status?: string;
  customers?: { name: string; village?: string; taluka?: string; district?: string } | null;
}

interface OfficerTimeline {
  user_id: string;
  name: string;
  email: string;
  total_meetings: number;
  total_minutes: number;
  visits: VisitEntry[];
}

interface UserProfile {
  id: string;
  full_name?: string | null;
  role: 'admin' | 'caller' | 'field_officer';
  caller_id?: string | null;
  caller_name?: string | null;
  email?: string;
}

interface RoutePoint {
  latitude: number;
  longitude: number;
  recorded_at: string;
  accuracy_m?: number;
  speed_mps?: number;
}

// ─── Config ────────────────────────────────────────────────────────────────────

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
];

// ─── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch(endpoint: string, token?: string): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  for (const base of API_URLS) {
    try {
      const res = await fetch(`${base}${endpoint}`, { headers });
      if (res.ok) return await res.json();
    } catch { /* try next */ }
  }
  return null;
}

async function apiPost(endpoint: string, body: object, token?: string): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  for (const base of API_URLS) {
    try {
      const res = await fetch(`${base}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
      if (res.ok) return await res.json();
    } catch { /* try next */ }
  }
  return null;
}

async function apiPut(endpoint: string, body: object, token?: string): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  for (const base of API_URLS) {
    try {
      const res = await fetch(`${base}${endpoint}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(body),
      });
      if (res.ok) return await res.json();
    } catch { /* try next */ }
  }
  return null;
}

// ─── Formatters ──────────────────────────────────────────────────────────────

function fmtTime(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function fmtDur(minutes?: number | null): string {
  if (!minutes || minutes <= 0) return '—';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function todayIST(): string {
  const now = new Date();
  const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
  return ist.toISOString().slice(0, 10);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

// Token login banner
function TokenBanner({ token, onSet }: { token: string; onSet: (t: string) => void }) {
  const [val, setVal] = useState('');
  if (token) return (
    <div style={{ background: '#ECFDF5', borderBottom: '1px solid #BBF7D0', padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#059669' }}>
      <CheckCircle size={14} /> Admin token active — authenticated requests enabled
      <button onClick={() => onSet('')} style={{ marginLeft: 'auto', fontSize: 11, color: '#DC2626', background: 'none', border: 'none', cursor: 'pointer' }}>Clear</button>
    </div>
  );
  return (
    <div style={{ background: '#FEF3C7', borderBottom: '1px solid #FDE68A', padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <AlertCircle size={14} color="#D97706" />
      <span style={{ fontSize: 12, color: '#92400E' }}>Paste your admin JWT to enable authenticated endpoints:</span>
      <input
        value={val}
        onChange={e => setVal(e.target.value)}
        placeholder="eyJhbGci..."
        style={{ flex: 1, minWidth: 200, fontSize: 11, padding: '4px 8px', border: '1px solid #FDE68A', borderRadius: 6, fontFamily: 'monospace' }}
      />
      <button
        onClick={() => { if (val.trim()) onSet(val.trim()); }}
        style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 6, padding: '5px 14px', cursor: 'pointer', fontSize: 12 }}
      >
        Set Token
      </button>
      <span style={{ fontSize: 11, color: '#78350F' }}>
        (Get from mobile app DevTools or Supabase Auth → Users → JWT)
      </span>
    </div>
  );
}

// ─── Tab: Visit Dashboard (replaces old map tab) ─────────────────────────────

function VisitDashboardTab({ token }: { token: string }) {
  const [date, setDate] = useState(todayIST());
  const [timeline, setTimeline] = useState<OfficerTimeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<OfficerTimeline | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    const data = await apiFetch(`/visits/admin/timeline?date=${date}`, token);
    if (Array.isArray(data)) {
      setTimeline(data);
      if (data.length > 0 && !selected) setSelected(data[0]);
    }
    setLoading(false);
  }, [date, token]);

  useEffect(() => { load(); }, [load]);

  const totalVisits = timeline.reduce((a, o) => a + o.total_meetings, 0);
  const totalMinutes = timeline.reduce((a, o) => a + o.total_minutes, 0);
  const activeOfficers = timeline.filter(o => o.visits.some(v => !v.checked_out_at)).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Top stats bar */}
      <div style={{ display: 'flex', gap: 16, padding: '16px 20px', borderBottom: '1px solid #E2E8F0', background: '#FAFAFA', flexWrap: 'wrap' }}>
        {[
          { icon: <Users size={16} color="#2563EB" />, label: 'Officers Active', value: `${activeOfficers} / ${timeline.length}` },
          { icon: <CheckCircle size={16} color="#10B981" />, label: 'Total Visits', value: totalVisits },
          { icon: <Clock size={16} color="#7C3AED" />, label: 'Total Time', value: fmtDur(totalMinutes) },
          { icon: <Activity size={16} color="#F59E0B" />, label: 'In Progress', value: timeline.reduce((a, o) => a + o.visits.filter(v => !v.checked_out_at).length, 0) },
        ].map((s, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 12, padding: '10px 18px', display: 'flex', alignItems: 'center', gap: 10, flex: '1 1 150px' }}>
            <div style={{ background: '#F0F9FF', borderRadius: 8, padding: 6 }}>{s.icon}</div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#111827' }}>{s.value}</div>
              <div style={{ fontSize: 11, color: '#6B7280' }}>{s.label}</div>
            </div>
          </div>
        ))}

        {/* Date picker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
          <Calendar size={14} color="#6B7280" />
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '6px 10px', fontSize: 13 }}
          />
          <button onClick={load} disabled={loading} style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <RefreshCw size={13} /> {loading ? 'Loading…' : 'Refresh'}
          </button>
          <button onClick={() => exportAdminVisitPDF(timeline, date)} disabled={timeline.length === 0} style={{ background: '#10B981', color: '#fff', border: 'none', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <Download size={13} /> Export PDF
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: officer list */}
        <div style={{ width: 280, borderRight: '1px solid #E2E8F0', overflowY: 'auto', background: '#FAFAFA' }}>
          <div style={{ padding: '12px 14px', borderBottom: '1px solid #E2E8F0', fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Field Officers ({timeline.length})
          </div>
          {timeline.length === 0 && !loading && (
            <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
              {token ? 'No visits recorded for this date.' : 'Set admin token to load data.'}
            </div>
          )}
          {timeline.map(officer => {
            const isActive = officer.visits.some(v => !v.checked_out_at);
            const isSelected = selected?.user_id === officer.user_id;
            return (
              <div
                key={officer.user_id}
                onClick={() => setSelected(officer)}
                style={{
                  padding: '12px 14px',
                  cursor: 'pointer',
                  background: isSelected ? '#EFF6FF' : 'transparent',
                  borderLeft: isSelected ? '3px solid #2563EB' : '3px solid transparent',
                  borderBottom: '1px solid #F1F5F9',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#111827' }}>{officer.name || officer.email}</div>
                  <div style={{ background: isActive ? '#ECFDF5' : '#F3F4F6', color: isActive ? '#059669' : '#6B7280', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20 }}>
                    {isActive ? 'ACTIVE' : 'IDLE'}
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{officer.email}</div>
                <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
                  <span style={{ fontSize: 12, color: '#2563EB', fontWeight: 600 }}>{officer.total_meetings} visits</span>
                  <span style={{ fontSize: 12, color: '#6B7280' }}>{fmtDur(officer.total_minutes)}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: visit detail */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {selected ? (
            <div>
              {/* Officer header */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#111827' }}>{selected.name || selected.email}</div>
                <div style={{ fontSize: 13, color: '#6B7280', marginTop: 2 }}>{selected.email}</div>
                <div style={{ display: 'flex', gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
                  <span style={{ background: '#EFF6FF', color: '#2563EB', borderRadius: 8, padding: '4px 12px', fontSize: 13, fontWeight: 700 }}>
                    {selected.total_meetings} completed visits
                  </span>
                  <span style={{ background: '#ECFDF5', color: '#10B981', borderRadius: 8, padding: '4px 12px', fontSize: 13, fontWeight: 700 }}>
                    {fmtDur(selected.total_minutes)} total time
                  </span>
                  <span style={{ background: '#FEF3C7', color: '#D97706', borderRadius: 8, padding: '4px 12px', fontSize: 13, fontWeight: 700 }}>
                    {selected.visits.filter(v => !v.checked_out_at).length} in progress
                  </span>
                </div>
              </div>

              {/* Visit cards */}
              <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                All Visits
              </div>
              {selected.visits.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>No visits for this officer today.</div>
              ) : (
                selected.visits.map((v, i) => {
                  const isComplete = !!v.checked_out_at;
                  return (
                    <div key={v.id} style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 12, padding: 16, marginBottom: 10, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                      {/* Step number */}
                      <div style={{ width: 28, height: 28, borderRadius: 8, background: isComplete ? '#ECFDF5' : '#FEF3C7', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 12, fontWeight: 800, color: isComplete ? '#059669' : '#D97706' }}>
                        {i + 1}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>
                          {v.customers?.name || 'Unknown Customer'}
                        </div>
                        {v.customers && (v.customers.village || v.customers.taluka) && (
                          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>
                            📍 {[v.customers.village, v.customers.taluka, v.customers.district].filter(Boolean).join(', ')}
                          </div>
                        )}
                        <div style={{ display: 'flex', gap: 16, marginTop: 6, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: 12, color: '#374151' }}>
                            <strong>IN:</strong> {fmtTime(v.checked_in_at)}
                          </span>
                          <span style={{ fontSize: 12, color: '#374151' }}>
                            <strong>OUT:</strong> {fmtTime(v.checked_out_at)}
                          </span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#2563EB' }}>
                            ⏱ {fmtDur(v.duration_minutes)}
                          </span>
                          <span style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: 6,
                            background: isComplete ? '#ECFDF5' : '#FEF3C7',
                            color: isComplete ? '#059669' : '#D97706',
                          }}>
                            {isComplete ? 'Completed' : 'In Progress'}
                          </span>
                        </div>
                        {v.notes && (
                          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 6, fontStyle: 'italic' }}>
                            💬 {v.notes}
                          </div>
                        )}
                        {(v.checkin_lat && v.checkin_lng) && (
                          <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 4 }}>
                            🗺 {v.checkin_lat.toFixed(5)}, {v.checkin_lng.toFixed(5)}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#9CA3AF' }}>
              Select a field officer from the list to view their visit details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Tab: GPS Map (legacy sessions) ──────────────────────────────────────────

function GPSMapTab() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    const map = L.map(mapRef.current, { center: [19.076, 72.8777], zoom: 12, zoomControl: true });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors', maxZoom: 19,
    }).addTo(map);
    mapInstanceRef.current = map;
    setTimeout(() => map.invalidateSize(), 200);
  }, []);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #E2E8F0', fontSize: 13, color: '#6B7280' }}>
        GPS route map — select an officer from the Visit Dashboard to see their location pins.
      </div>
      <div ref={mapRef} style={{ flex: 1, minHeight: 400 }} />
    </div>
  );
}

// ─── Tab: Daily Travel Report ─────────────────────────────────────────────────

function ReportTab({ token }: { token: string }) {
  const [date, setDate] = useState(todayIST());
  const [data, setData] = useState<OfficerTimeline[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const res = await apiFetch(`/visits/admin/timeline?date=${date}`, token);
    if (Array.isArray(res)) setData(res);
    setLoading(false);
  };

  useEffect(() => { load(); }, [date, token]);

  const exportCSV = () => {
    const rows = ['Officer,Email,Customer,Check-In,Check-Out,Duration (min),Notes'];
    for (const o of data) {
      for (const v of o.visits) {
        rows.push([
          `"${o.name}"`, `"${o.email}"`,
          `"${v.customers?.name || ''}"`,
          v.checked_in_at, v.checked_out_at || '',
          v.duration_minutes ?? '', `"${v.notes || ''}"`,
        ].join(','));
      }
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `visit-report-${date}.csv`; a.click();
  };

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#111827' }}>Daily Travel & Visit Report</div>
          <div style={{ fontSize: 13, color: '#6B7280', marginTop: 2 }}>Consolidated officer visit report by date</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '6px 10px', fontSize: 13 }} />
          <button onClick={load} disabled={loading} style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={13} /> {loading ? 'Loading…' : 'Load'}
          </button>
          <button onClick={exportCSV} disabled={data.length === 0} style={{ background: '#10B981', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Download size={13} /> Export CSV
          </button>
          <button onClick={() => exportAdminVisitPDF(data, date)} disabled={data.length === 0} style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Download size={13} /> Export PDF
          </button>
        </div>
      </div>

      {data.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#9CA3AF' }}>
          {token ? 'No visit data for this date.' : 'Set admin token above to load data.'}
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
              {['Officer', 'Customer', 'Check-In', 'Check-Out', 'Duration', 'Status', 'Notes'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#374151', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.03em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.flatMap(o =>
              o.visits.map((v, i) => (
                <tr key={v.id} style={{ borderBottom: '1px solid #F1F5F9', background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 600, color: '#111827' }}>{i === 0 ? o.name || o.email : ''}</td>
                  <td style={{ padding: '10px 12px', color: '#374151' }}>{v.customers?.name || '—'}</td>
                  <td style={{ padding: '10px 12px', color: '#374151' }}>{fmtTime(v.checked_in_at)}</td>
                  <td style={{ padding: '10px 12px', color: '#374151' }}>{fmtTime(v.checked_out_at)}</td>
                  <td style={{ padding: '10px 12px', color: '#2563EB', fontWeight: 600 }}>{fmtDur(v.duration_minutes)}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ background: v.checked_out_at ? '#ECFDF5' : '#FEF3C7', color: v.checked_out_at ? '#059669' : '#D97706', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>
                      {v.checked_out_at ? 'Done' : 'In Progress'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#6B7280', fontStyle: 'italic' }}>{v.notes || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── Tab: Team Management ─────────────────────────────────────────────────────

function TeamManagementTab({ token }: { token: string }) {
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const [callers, setCallers] = React.useState<UserProfile[]>([]);
  const [fieldOfficers, setFieldOfficers] = React.useState<UserProfile[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [assignState, setAssignState] = React.useState<Record<string, string>>({});
  const [saving, setSaving] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState('');
  const [roleChanges, setRoleChanges] = React.useState<Record<string, string>>({});

  const load = React.useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    const [usersRes, callersRes, fosRes] = await Promise.all([
      apiFetch('/admin/all-users', token),
      apiFetch('/admin/callers', token),
      apiFetch('/admin/field-officers', token),
    ]);
    if (Array.isArray(usersRes)) setUsers(usersRes);
    if (Array.isArray(callersRes)) setCallers(callersRes);
    if (Array.isArray(fosRes)) setFieldOfficers(fosRes);
    setIsLoading(false);
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const handleAssign = async (officerId: string) => {
    const callerId = assignState[officerId];
    if (!callerId) return;
    setSaving(officerId);
    const res = await apiPost('/admin/profiles/assign', { field_officer_id: officerId, caller_id: callerId }, token);
    if (res?.success) {
      setMessage(`✅ Assignment saved!`);
      await load();
    } else {
      setMessage('❌ Assignment failed. Check token/permissions.');
    }
    setSaving(null);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleRoleChange = async (userId: string) => {
    const role = roleChanges[userId];
    if (!role) return;
    setSaving(userId + '_role');
    const res = await apiPut(`/admin/profiles/${userId}/role`, { role }, token);
    if (res?.success) {
      setMessage(`✅ Role updated to ${role}!`);
      await load();
    } else {
      setMessage('❌ Role update failed. Check token/permissions.');
    }
    setSaving(null);
    setTimeout(() => setMessage(''), 3000);
  };

  if (!token) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 15 }}>
      <Shield size={40} color="#D1D5DB" style={{ marginBottom: 12 }} />
      <div>Set the admin JWT token above to manage team assignments.</div>
    </div>
  );

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#111827' }}>Team Management</div>
          <div style={{ fontSize: 13, color: '#6B7280', marginTop: 2 }}>Assign field officers to callers · Manage roles</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {message && <div style={{ background: message.startsWith('✅') ? '#ECFDF5' : '#FEF2F2', color: message.startsWith('✅') ? '#059669' : '#DC2626', borderRadius: 8, padding: '8px 14px', fontSize: 13 }}>{message}</div>}
          <button onClick={load} disabled={isLoading} style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={13} /> {isLoading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>Loading…</div>
      ) : (
        <>
          {/* Callers section */}
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <Phone size={13} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
              Callers ({callers.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {callers.length === 0 && <div style={{ color: '#9CA3AF', fontSize: 13 }}>No callers found. Change a user's role to "caller" below.</div>}
              {callers.map(c => (
                <div key={c.id} style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 10, padding: '10px 14px', minWidth: 200 }}>
                  <div style={{ fontWeight: 700, color: '#1E40AF', fontSize: 14 }}>{c.full_name || c.email}</div>
                  <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{c.email}</div>
                  <div style={{ fontSize: 12, color: '#2563EB', marginTop: 4, fontWeight: 600 }}>
                    {fieldOfficers.filter(f => f.caller_id === c.id).length} officers assigned
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Field Officers section */}
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <UserCheck size={13} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
              Field Officers ({fieldOfficers.length}) — Assign to Caller
            </div>
            {fieldOfficers.length === 0 && <div style={{ color: '#9CA3AF', fontSize: 13 }}>No field officers found.</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {fieldOfficers.map(fo => (
                <div key={fo.id} style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 12, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <div style={{ fontWeight: 700, color: '#111827', fontSize: 14 }}>{fo.full_name || fo.email}</div>
                    <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{fo.email}</div>
                    {fo.caller_name && (
                      <div style={{ fontSize: 12, color: '#10B981', marginTop: 3, fontWeight: 600 }}>
                        ✓ Assigned to: {fo.caller_name}
                      </div>
                    )}
                    {!fo.caller_id && (
                      <div style={{ fontSize: 12, color: '#F59E0B', marginTop: 3 }}>⚠ Unassigned</div>
                    )}
                  </div>
                  <select
                    value={assignState[fo.id] ?? fo.caller_id ?? ''}
                    onChange={e => setAssignState(s => ({ ...s, [fo.id]: e.target.value }))}
                    style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '6px 10px', fontSize: 13, minWidth: 180 }}
                  >
                    <option value="">— Select Caller —</option>
                    {callers.map(c => (
                      <option key={c.id} value={c.id}>{c.full_name || c.email}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleAssign(fo.id)}
                    disabled={saving === fo.id || !assignState[fo.id]}
                    style={{ background: '#2563EB', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, opacity: saving === fo.id || !assignState[fo.id] ? 0.5 : 1 }}
                  >
                    {saving === fo.id ? 'Saving…' : 'Assign'}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* All users — role management */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <User size={13} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
              All Users ({users.length}) — Manage Roles
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
                  {['Name', 'Email', 'Current Role', 'Change Role', ''].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#374151', fontSize: 12, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid #F1F5F9', background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{u.full_name || '—'}</td>
                    <td style={{ padding: '10px 12px', color: '#6B7280' }}>{u.email || u.id}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        background: u.role === 'admin' ? '#FEE2E2' : u.role === 'caller' ? '#EFF6FF' : '#F0FDF4',
                        color: u.role === 'admin' ? '#DC2626' : u.role === 'caller' ? '#2563EB' : '#16A34A',
                        borderRadius: 6, padding: '3px 10px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                      }}>{u.role}</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <select
                        value={roleChanges[u.id] ?? u.role}
                        onChange={e => setRoleChanges(s => ({ ...s, [u.id]: e.target.value }))}
                        style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: '5px 8px', fontSize: 12 }}
                      >
                        <option value="field_officer">Field Officer</option>
                        <option value="caller">Caller</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <button
                        onClick={() => handleRoleChange(u.id)}
                        disabled={saving === u.id + '_role' || roleChanges[u.id] === u.role || !roleChanges[u.id]}
                        style={{ background: '#10B981', color: '#fff', border: 'none', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', fontSize: 12, opacity: (saving === u.id + '_role' || roleChanges[u.id] === u.role || !roleChanges[u.id]) ? 0.4 : 1 }}
                      >
                        {saving === u.id + '_role' ? '…' : 'Save'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'map' | 'report' | 'team';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [selectedDate, setSelectedDate] = useState(todayIST());
  const [adminToken, setAdminToken] = useState('');

  // Overview stats (from visit dashboard data)
  const [overviewDate] = useState(todayIST());

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Visit Dashboard', icon: <Activity size={15} /> },
    { id: 'map', label: 'GPS Map', icon: <MapPin size={15} /> },
    { id: 'report', label: 'Daily Report', icon: <FileSpreadsheet size={15} /> },
    { id: 'team', label: 'Team Management', icon: <Users size={15} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', background: '#F8FAFC' }}>
      {/* Top nav */}
      <div style={{ background: '#0F172A', padding: '0 20px', display: 'flex', alignItems: 'center', gap: 16, height: 54, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, background: '#2563EB', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Navigation size={14} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#fff', letterSpacing: '0.02em' }}>FSC Daily Portal</div>
            <div style={{ fontSize: 10, color: '#94A3B8' }}>Field Officer Management</div>
          </div>
        </div>

        {/* Tab nav */}
        <div style={{ display: 'flex', gap: 2, marginLeft: 20 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? '#1E293B' : 'transparent',
                color: activeTab === tab.id ? '#fff' : '#94A3B8',
                border: 'none',
                borderRadius: 8,
                padding: '6px 14px',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: activeTab === tab.id ? 700 : 400,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Date */}
        <div style={{ marginLeft: 'auto', fontSize: 12, color: '#64748B' }}>
          📅 {new Date().toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
        </div>
      </div>

      {/* Token banner */}
      <TokenBanner token={adminToken} onSet={setAdminToken} />

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'dashboard' && <VisitDashboardTab token={adminToken} />}
        {activeTab === 'map' && <GPSMapTab />}
        {activeTab === 'report' && <ReportTab token={adminToken} />}
        {activeTab === 'team' && <TeamManagementTab token={adminToken} />}
      </div>
    </div>
  );
}
