import './Notifications.css';

const NOTIFICATIONS = [
  { id: '1', title: 'New appointment scheduled', body: 'John Doe — Tomorrow 10:00 AM', time: '2 min ago', unread: true },
  { id: '2', title: 'Lab results ready', body: 'Patient Ananya Singh — CBC report available', time: '15 min ago', unread: true },
  { id: '3', title: 'Surgery reminder', body: 'Pre-op check for Mohammed Farhan at 2:00 PM', time: '1 hour ago', unread: false },
  { id: '4', title: 'System update', body: 'CDSS dashboard updated to latest version.', time: 'Yesterday', unread: false },
];

export default function Notifications() {
  return (
    <div className="page-enter" style={{ maxWidth: 640, margin: '0 auto' }}>
      <h1 className="notifications-page__title">Notifications</h1>
      <ul className="notifications-page__list" aria-label="All notifications">
        {NOTIFICATIONS.map((n) => (
          <li
            key={n.id}
            className={`notifications-page__item ${n.unread ? 'notifications-page__item--unread' : ''}`}
          >
            <div className="notifications-page__item-title">{n.title}</div>
            <div className="notifications-page__item-body">{n.body}</div>
            <div className="notifications-page__item-time">{n.time}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
