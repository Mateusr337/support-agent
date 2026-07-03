import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../../../services/api.js";
import Button from "../../../components/ui/Button.jsx";
import Input from "../../../components/ui/Input.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import "./AuthForm.css";

export default function RegisterForm() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      await register(email.trim(), name.trim(), password);
      navigate("/chat", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to create account. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form-header">
        <div className="auth-logo" aria-hidden="true">
          HP
        </div>
        <h1>Create account</h1>
        <p>Get started with the HP document assistant</p>
      </div>

      {error && (
        <div className="auth-alert" role="alert">
          {error}
        </div>
      )}

      <Input
        label="Full name"
        name="name"
        type="text"
        autoComplete="name"
        placeholder="Jane Doe"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />

      <Input
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <Input
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        placeholder="At least 8 characters"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        hint="Minimum 8 characters"
        required
      />

      <Button type="submit" fullWidth loading={loading}>
        Create account
      </Button>

      <p className="auth-footer">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </form>
  );
}
