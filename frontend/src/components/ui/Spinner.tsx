import "./Spinner.css";

interface SpinnerProps {
  fullPage?: boolean;
  label?: string;
}

export default function Spinner({ fullPage = false, label = "Loading..." }: SpinnerProps) {
  if (fullPage) {
    return (
      <div className="spinner-page" role="status" aria-label={label}>
        <span className="spinner" />
      </div>
    );
  }

  return <span className="spinner" role="status" aria-label={label} />;
}
