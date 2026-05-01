import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AuthShell from '../components/auth/AuthShell';

function Register() {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username.trim()) {
      setError('Please enter a username.');
      return;
    }
    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }
    if (!password) {
      setError('Please enter a password.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await register(username.trim(), email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const termsFooter = (
    <p className="text-center text-xs leading-relaxed text-muted">
      By creating an account, you agree to our{' '}
      <Link to="/settings/terms" className="font-medium text-brand transition hover:text-brand/80 hover:underline">
        Terms of Service
      </Link>{' '}
      and{' '}
      <Link to="/settings/privacy" className="font-medium text-brand transition hover:text-brand/80 hover:underline">
        Privacy Policy
      </Link>
      .
    </p>
  );

  return (
    <AuthShell footer={termsFooter}>
      <h1 className="border-b border-studio pb-4 text-2xl font-semibold tracking-tight text-text-high">
        Create an account
      </h1>
      <p className="mb-8 mt-4 text-sm leading-relaxed text-muted">
        Register to access forensic composite generation and session tools.
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
            placeholder="Choose a username"
            className="input-studio w-full"
            autoComplete="username"
          />
        </div>

        <div>
          <label htmlFor="email" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
            Email address
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input-studio w-full"
            autoComplete="email"
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
            placeholder="At least 8 characters"
            className="input-studio w-full"
            autoComplete="new-password"
          />
        </div>

        <div>
          <label
            htmlFor="confirmPassword"
            className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted"
          >
            Confirm password
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat your password"
            className="input-studio w-full"
            autoComplete="new-password"
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full py-3 text-sm shadow-panel">
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-8 border-t border-studio pt-6 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand transition hover:text-brand/80 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}

export default Register;
