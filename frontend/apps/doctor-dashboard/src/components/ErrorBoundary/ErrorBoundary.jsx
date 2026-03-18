import { Component } from 'react';
import './ErrorBoundary.css';

/**
 * Global error boundary for the CDSS dashboard.
 * Catches render errors and shows a friendly message with retry.
 */
export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('CDSS ErrorBoundary:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <div className="error-boundary__card">
            <div className="error-boundary__icon">⚠️</div>
            <h1 className="error-boundary__title">Something went wrong</h1>
            <p className="error-boundary__message">
              The app encountered an error. Please try again or refresh the page.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <pre className="error-boundary__detail">{this.state.error.message}</pre>
            )}
            <div className="error-boundary__actions">
              <button type="button" className="error-boundary__btn" onClick={this.handleRetry}>
                Try again
              </button>
              <button
                type="button"
                className="error-boundary__btn error-boundary__btn--secondary"
                onClick={() => window.location.reload()}
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
