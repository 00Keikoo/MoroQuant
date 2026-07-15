/**
 * Error normalization utility for consistent error handling across widgets.
 */

export interface NormalizedError {
  title: string;
  message: string;
  retryable: boolean;
  status?: number;
}

export function normalizeError(error: unknown): NormalizedError {
  if (!error) {
    return {
      title: 'Unknown Error',
      message: 'An unexpected error occurred',
      retryable: true,
    };
  }

  const err = error as any;

  // Timeout errors
  if (err.name === 'TimeoutError' || err.message?.includes('timed out')) {
    return {
      title: 'Request Timed Out',
      message: 'The request took too long to complete. Please try again.',
      retryable: true,
    };
  }

  // Abort errors
  if (err.name === 'AbortError') {
    return {
      title: 'Request Cancelled',
      message: 'The request was cancelled',
      retryable: false,
    };
  }

  // Network errors
  if (
    err.message?.includes('Network') ||
    err.message?.includes('fetch failed') ||
    err.message?.includes('Failed to fetch') ||
    err instanceof TypeError
  ) {
    return {
      title: 'Network Error',
      message: 'Unable to connect to the server. Check your connection.',
      retryable: true,
    };
  }

  // HTTP 4xx errors
  if (err.status >= 400 && err.status < 500) {
    return {
      title: 'Client Error',
      message: err.message || `Request failed with status ${err.status}`,
      retryable: false,
      status: err.status,
    };
  }

  // HTTP 5xx errors
  if (err.status >= 500) {
    return {
      title: 'Server Error',
      message: 'The server encountered an error. Please try again later.',
      retryable: true,
      status: err.status,
    };
  }

  // Client error messages (from backend)
  if (err.message?.includes('Client error:')) {
    return {
      title: 'Request Failed',
      message: err.message,
      retryable: false,
    };
  }

  // Server error messages (from backend)
  if (err.message?.includes('Server error:')) {
    return {
      title: 'Server Error',
      message: err.message,
      retryable: true,
    };
  }

  // Generic error with message
  if (err.message) {
    return {
      title: 'Error',
      message: err.message,
      retryable: true,
    };
  }

  // Fallback
  return {
    title: 'Error',
    message: String(error),
    retryable: true,
  };
}
