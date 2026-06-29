import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { setToken } from '../auth';

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '80vh',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '32px',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    width: '320px',
  },
  input: {
    padding: '10px 12px',
    fontSize: '16px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: 'var(--text-h)',
  },
  button: {
    padding: '10px',
    fontSize: '16px',
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  error: {
    color: '#e53e3e',
    fontSize: '14px',
    margin: 0,
  },
  title: {
    margin: '0 0 8px',
    textAlign: 'center',
    color: 'var(--text-h)',
  },
};

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/login', { username, password });
      setToken(res.data.token);
      navigate('/articles');
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <form style={styles.form} onSubmit={handleSubmit}>
        <h2 style={styles.title}>Login</h2>
        {error && <p style={styles.error} role="alert">{error}</p>}
        <label htmlFor="username" style={{ display: 'none' }}>Username</label>
        <input
          id="username"
          style={styles.input}
          type="text"
          placeholder="Username"
          aria-label="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <label htmlFor="password" style={{ display: 'none' }}>Password</label>
        <input
          id="password"
          style={styles.input}
          type="password"
          placeholder="Password"
          aria-label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? 'Logging in…' : 'Login'}
        </button>
      </form>
    </div>
  );
}
