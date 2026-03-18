import './LoadingSpinner.css';

/**
 * Reusable loading indicator for data fetches and auth.
 */
export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="loading-spinner" role="status" aria-live="polite">
      <div className="loading-spinner__dots">
        <div className="loading-spinner__dot" />
        <div className="loading-spinner__dot" />
        <div className="loading-spinner__dot" />
      </div>
      {message && <p className="loading-spinner__message">{message}</p>}
    </div>
  );
}
