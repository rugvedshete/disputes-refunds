export const Loading = ({ text = "Loading…" }: { text?: string }) => (
  <div className="state" role="status"><span className="spinner" aria-hidden />{text}</div>
);

export const ErrorBox = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="state error" role="alert">
    <p>{message}</p>
    {onRetry && <button onClick={onRetry}>Try again</button>}
  </div>
);

export const Empty = ({ children }: { children: React.ReactNode }) => <div className="state">{children}</div>;
