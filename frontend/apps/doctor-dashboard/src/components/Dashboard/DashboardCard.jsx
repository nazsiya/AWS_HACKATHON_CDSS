/**
 * Reusable card for dashboard overview stats.
 * Minimal icon, large number, small label, subtext.
 */
export default function DashboardCard({ icon, value, label, subtext }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 min-h-[120px] flex flex-col">
      <div className="flex items-start justify-between gap-2">
        {icon && (
          <span className="text-2xl text-gray-400 flex-shrink-0" aria-hidden>
            {icon}
          </span>
        )}
      </div>
      <div className="mt-2">
        <p className="text-3xl font-semibold text-gray-900 tracking-tight">{value}</p>
        <p className="text-sm font-medium text-gray-600 mt-0.5">{label}</p>
        {subtext && (
          <p className="text-xs text-gray-500 mt-2">{subtext}</p>
        )}
      </div>
    </div>
  );
}
