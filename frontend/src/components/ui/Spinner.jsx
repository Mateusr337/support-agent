import "./Spinner.css";

export default function Spinner({ fullPage = false, label = "Loading..." }) {
  if (fullPage) {
    return (
      <div className="spinner-page" role="status" aria-label={label}>
        <span className="spinner" />
      </div>
    );
  }

  return (
    <span className="spinner" role="status" aria-label={label} />
  );
}
