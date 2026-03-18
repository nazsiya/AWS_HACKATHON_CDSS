/**
 * Checklist-style pending tasks (no AI). Used in main work area.
 */
export default function PendingTasksChecklist({ items, onToggle }) {
  return (
    <ul className="space-y-0">
      {items.map((item) => (
        <li
          key={item.id}
          className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0"
        >
          <button
            type="button"
            onClick={() => onToggle?.(item.id)}
            className="flex-shrink-0 w-5 h-5 rounded border-2 border-gray-300 flex items-center justify-center hover:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-1"
            aria-label={item.done ? 'Mark incomplete' : 'Mark complete'}
          >
            {item.done && (
              <span className="text-[#2563EB] text-sm font-bold" aria-hidden>✓</span>
            )}
          </button>
          <span
            className={`text-sm ${item.done ? 'text-gray-400 line-through' : 'text-gray-800'}`}
          >
            {item.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
