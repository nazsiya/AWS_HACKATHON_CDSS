/**
 * Dev-only connection status indicator: links to Debug page.
 * Shows in patient app header when import.meta.env.DEV is true.
 */
import { Link } from 'react-router-dom';

export default function ConnectionStatus() {
  if (!import.meta.env.DEV) return null;
  return (
    <Link
      to="/debug"
      className="connection-status"
      title="Connection status &amp; debug"
    >
      Status
    </Link>
  );
}
