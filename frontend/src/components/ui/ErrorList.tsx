type ErrorListProps = {
  errors: string[];
};

export function ErrorList({ errors }: ErrorListProps) {
  const uniqueErrors = Array.from(new Set(errors.map((error) => error.trim()).filter(Boolean)));
  if (uniqueErrors.length === 0) return null;
  return (
    <div className="form-error" role="alert">
      <strong>Check these details</strong>
      <ul>
        {uniqueErrors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}
