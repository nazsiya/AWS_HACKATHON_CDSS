import { useState } from 'react';
import { doctorsList } from '../../data/mockData';
import './Doctors.css';

export default function Doctors() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // all | active | inactive

  const filtered = doctorsList.filter((d) => {
    const matchSearch =
      !search ||
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.specialization.toLowerCase().includes(search.toLowerCase()) ||
      d.department.toLowerCase().includes(search.toLowerCase()) ||
      (d.email && d.email.toLowerCase().includes(search.toLowerCase()));
    const matchStatus = filter === 'all' || d.status.toLowerCase() === filter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="doctors-page page-enter">
      <div className="doctors-page__header">
        <h1 className="doctors-page__title">Doctors</h1>
        <p className="doctors-page__desc">Manage doctor directory and availability.</p>
      </div>

      <div className="doctors-page__toolbar">
        <label className="doctors-page__search-wrap">
          <span className="doctors-page__search-icon" aria-hidden>🔍</span>
          <input
            type="search"
            className="doctors-page__search"
            placeholder="Search by name, specialization, department, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search doctors"
          />
        </label>
        <div className="doctors-page__filters">
          <button
            type="button"
            className={`doctors-page__filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            type="button"
            className={`doctors-page__filter-btn ${filter === 'active' ? 'active' : ''}`}
            onClick={() => setFilter('active')}
          >
            Active
          </button>
          <button
            type="button"
            className={`doctors-page__filter-btn ${filter === 'inactive' ? 'active' : ''}`}
            onClick={() => setFilter('inactive')}
          >
            Inactive
          </button>
        </div>
      </div>

      <div className="doctors-page__card">
        <table className="doctors-page__table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Specialization</th>
              <th>Department</th>
              <th>Email</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="doctors-page__empty">No doctors match your filters.</td>
              </tr>
            ) : (
              filtered.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.id}</td>
                  <td className="doctors-page__name">{doc.name}</td>
                  <td>{doc.specialization}</td>
                  <td>{doc.department}</td>
                  <td>{doc.email}</td>
                  <td>
                    <span className={`doctors-page__status doctors-page__status--${doc.status.toLowerCase()}`}>
                      {doc.status}
                    </span>
                  </td>
                  <td>
                    <button type="button" className="doctors-page__action">View</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
