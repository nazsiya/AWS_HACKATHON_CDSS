/**
 * Single operational alert for Vital Alert Center.
 * Types: emergency (red), staffing (orange), shift (blue), info (gray).
 */
export default function OperationalAlertCard({ alert, onAction }) {
  const { type, title, message, time, action } = alert;
  const typeStyles = {
    emergency: 'border-l-red-500 bg-red-50/50',
    staffing: 'border-l-orange-500 bg-orange-50/50',
    shift: 'border-l-blue-500 bg-blue-50/50',
    info: 'border-l-gray-400 bg-gray-50/50',
  };
  const typeLabels = {
    emergency: 'Emergency',
    staffing: 'Staffing',
    shift: 'Shift',
    info: 'Info',
  };
  const style = typeStyles[type] || typeStyles.info;
  const typeLabel = typeLabels[type] || 'Info';

  return (
    <div
      className={`rounded-xl border border-gray-100 border-l-[3px] p-4 transition-all hover:border-gray-200 ${style} group`}
      data-alert-type={type}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 group-hover:text-gray-500 transition-colors">
              {typeLabel}
            </span>
            <span className="w-1 h-1 rounded-full bg-gray-300" />
            <span className="text-[10px] font-medium text-gray-400">{time}</span>
          </div>
          <p className="font-bold text-gray-900 leading-snug">{title}</p>
          <p className="text-[13px] text-gray-500 mt-1.5 leading-relaxed">{message}</p>
        </div>
      </div>
      {action && (
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={() => onAction?.(alert)}
            className="text-xs font-bold text-[#2563EB] hover:text-blue-700 transition-colors py-1 px-2 -mr-2"
          >
            {action}
          </button>
        </div>
      )}
    </div>
  );
}
