import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AuthShell from '../components/auth/AuthShell';

function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username.trim()) {
      setError('Please enter your username.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
      <h1 className="border-b border-studio pb-4 text-2xl font-semibold tracking-tight text-text-high">
        Sign in
      </h1>
      <p className="mb-8 mt-4 text-sm leading-relaxed text-muted">
        Welcome back. Sign in to continue to the composite workspace.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div
            role="alert"
            className="rounded-2xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger"
          >
            {error}
          </div>
        )}

        <div>
          <label htmlFor="username" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Your username"
            className="input-studio w-full"
            autoComplete="username"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            className="input-studio w-full"
            autoComplete="current-password"
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full py-3 text-sm shadow-panel">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="mt-8 border-t border-studio pt-6 text-center text-sm text-muted">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="font-semibold text-brand transition hover:text-brand/80 hover:underline">
          Create account
        </Link>
      </p>
    </AuthShell>
  );
}

export default Login;
