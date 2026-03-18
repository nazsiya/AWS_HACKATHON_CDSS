import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getResources } from '../../api/client';
import './Resources.css';

const mockCapacity = { staff: 42, assets: 28 };
const mockCategories = [
  { id: 'doctors', label: 'Doctors', icon: '👨‍⚕️' },
  { id: 'nurses', label: 'Nurses', icon: '👩‍⚕️' },
  { id: 'ots', label: 'OTs', icon: '🏥' },
  { id: 'equipment', label: 'Equipment', icon: '🛠️' },
];
const mockInventory = [
  { id: 'R1', name: 'Dr. Priya Sharma', specialty: 'General Medicine', status: 'Available', assignedTo: '—', area: '—' },
  { id: 'R2', name: 'Dr. Vikram Patel', specialty: 'Orthopedics', status: 'Busy', assignedTo: 'PT-1005', area: 'OT-3' },
  { id: 'R3', name: 'Nurse Anjali', specialty: 'ICU', status: 'Available', assignedTo: '—', area: '—' },
  { id: 'R4', name: 'OT-1', specialty: 'Operation Theater', status: 'Busy', assignedTo: 'SRG-003', area: 'OT-1' },
  { id: 'R5', name: 'OT-2', specialty: 'Operation Theater', status: 'Available', assignedTo: '—', area: '—' },
  { id: 'R6', name: 'Ventilator V1', specialty: 'Equipment', status: 'Critical', assignedTo: 'PT-1003', area: 'ICU' },
];

export default function Resources() {
  const [capacity, setCapacity] = useState(mockCapacity);
  const [inventory, setInventory] = useState(mockInventory);
  const [loading, setLoading] = useState(!isMockMode());
  const [activeCategory, setActiveCategory] = useState('doctors');

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getResources()
      .then((data) => {
        if (cancelled) return;
        setCapacity(data.capacity || mockCapacity);
        setInventory(data.inventory || data.items || mockInventory);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const statusClass = (s) => (s || '').toLowerCase().replace(/\s/g, '-');

  return (
    <div className="resources-page page-enter">
      <h1 className="resources-page__title">🛠️ Resource Monitoring</h1>
      <p className="resources-page__desc">Hospital capacity, category browsing, and resource inventory.</p>

      {/* Hospital Capacity Cards */}
      <div className="resources-capacity">
        <div className="capacity-card">
          <span className="capacity-card__icon">👥</span>
          <span className="capacity-card__value">{capacity.staff}</span>
          <span className="capacity-card__label">Staff Available</span>
        </div>
        <div className="capacity-card">
          <span className="capacity-card__icon">🛠️</span>
          <span className="capacity-card__value">{capacity.assets}</span>
          <span className="capacity-card__label">Assets Available</span>
        </div>
      </div>

      {/* Category Browsing */}
      <div className="resources-categories">
        <span className="resources-categories__label">Category:</span>
        {mockCategories.map((cat) => (
          <button
            key={cat.id}
            className={`resources-cat-btn ${activeCategory === cat.id ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat.id)}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {/* Resource Inventory */}
      <div className="resources-inventory">
        <h2 className="resources-inventory__title">Resource Inventory</h2>
        {loading && !isMockMode() ? (
          <p>Loading…</p>
        ) : (
          <table className="resources-table">
            <thead>
              <tr>
                <th>Resource name</th>
                <th>Specialty</th>
                <th>Status</th>
                <th>Assigned Patient / Area</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.specialty}</td>
                  <td>
                    <span className={`resource-status resource-status--${statusClass(r.status)}`}>
                      {r.status}
                    </span>
                  </td>
                  <td>{r.assignedTo !== '—' ? `${r.assignedTo} / ${r.area}` : r.area || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
