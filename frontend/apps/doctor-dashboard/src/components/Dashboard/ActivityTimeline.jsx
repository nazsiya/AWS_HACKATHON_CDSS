/**
 * Chronological activity timeline for dashboard bottom section.
 */
const actionLabels = {
  view_dashboard: 'Viewed Dashboard',
  view_patient_list: 'Viewed Patient List',
  view_patient: 'Reviewed Patient',
  start_consultation: 'Started Consultation',
  save_consultation: 'Saved Consultation Notes',
  sign_discharge: 'Signed discharge summary',
  accept_ot_extension: 'Accepted OT extension',
  view_medications: 'Viewed Medications',
  view_surgery: 'Viewed Surgery',
  view_activity: 'Viewed My Activity',
};

function formatTime(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hr ago`;
  return d.toLocaleDateString();
}

export default function ActivityTimeline({ activities }) {
  return (
    <div className="relative pl-1">
      <ul className="relative space-y-0">
        {activities.slice(0, 8).map((entry, i) => (
          <li key={entry.id} className="relative flex gap-4 pb-6 last:pb-0">
            <div className="absolute left-0 top-2 w-3 h-3 rounded-full bg-[#2563EB] border-2 border-white shadow-sm z-[1]" />
            {i < activities.length - 1 && (
              <div className="absolute left-[5px] top-5 bottom-0 w-0.5 bg-gray-200 -mb-6" />
            )}
            <div className="flex-1 min-w-0 pl-6 pt-0.5">
              <p className="text-sm font-medium text-gray-900">
                {actionLabels[entry.type] || entry.type.replace(/_/g, ' ')}
              </p>
              {entry.detail && (
                <p className="text-xs text-gray-600 mt-0.5">{entry.detail}</p>
              )}
              {entry.patientId && (
                <p className="text-xs text-gray-500 mt-0.5">Patient: {entry.patientId}</p>
              )}
              <p className="text-xs text-gray-400 mt-1">{formatTime(entry.timestamp)}</p>
            </div>
          </li>
        ))}
      </ul>
      {activities.length === 0 && (
        <p className="text-sm text-gray-500 py-4">No recent activity.</p>
      )}
    </div>
  );
}
