import { useState, useEffect } from 'react';
import api from '../api';
import { decodeToken } from '../auth';

const styles = {
  container: {
    maxWidth: '800px',
    margin: '32px auto',
    padding: '0 24px',
  },
  title: {
    color: 'var(--text-h)',
    margin: '0 0 24px',
  },
  denied: {
    textAlign: 'center',
    marginTop: '80px',
    color: 'var(--text)',
  },
  form: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
    alignItems: 'flex-end',
    marginBottom: '32px',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  label: {
    fontSize: '13px',
    color: 'var(--text)',
  },
  input: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: 'var(--text-h)',
    width: '180px',
  },
  button: {
    padding: '8px 16px',
    fontSize: '14px',
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '4px 10px',
    fontSize: '13px',
    background: '#e53e3e',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  message: {
    padding: '8px 12px',
    borderRadius: '4px',
    marginBottom: '16px',
    fontSize: '14px',
  },
  success: {
    background: '#c6f6d5',
    color: '#22543d',
  },
  error: {
    background: '#fed7d7',
    color: '#822727',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    borderBottom: '2px solid var(--border)',
    color: 'var(--text-h)',
    fontSize: '14px',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid var(--border)',
    color: 'var(--text)',
    fontSize: '14px',
  },
};

export default function AdminPanel() {
  const decoded = decodeToken();

  const [users, setUsers] = useState([]);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null); // { type: 'success'|'error', text }

  useEffect(() => {
    if (decoded?.is_admin) fetchUsers();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchUsers() {
    try {
      const res = await api.get('/users');
      setUsers(res.data.users ?? res.data);
    } catch {
      setMsg({ type: 'error', text: 'Failed to load users' });
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    try {
      await api.post('/users', { username, email, password });
      setMsg({ type: 'success', text: 'User created successfully' });
      setUsername('');
      setEmail('');
      setPassword('');
      await fetchUsers();
    } catch (err) {
      setMsg({ type: 'error', text: err.response?.data?.message || 'Failed to create user' });
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(userId, name) {
    if (!window.confirm(`Delete user "${name}"?`)) return;
    setMsg(null);
    try {
      await api.delete(`/users/${userId}`);
      setMsg({ type: 'success', text: `User "${name}" deleted` });
      await fetchUsers();
    } catch (err) {
      setMsg({ type: 'error', text: err.response?.data?.message || 'Failed to delete user' });
    }
  }

  if (!decoded?.is_admin) {
    return <p style={styles.denied}>Access denied. Admin privileges required.</p>;
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Admin Panel</h2>

      {msg && (
        <div style={{ ...styles.message, ...(msg.type === 'success' ? styles.success : styles.error) }} role="alert">
          {msg.text}
        </div>
      )}

      <form style={styles.form} onSubmit={handleCreate}>
        <div style={styles.fieldGroup}>
          <label htmlFor="new-username" style={styles.label}>Username</label>
          <input id="new-username" style={styles.input} type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div style={styles.fieldGroup}>
          <label htmlFor="new-email" style={styles.label}>Email</label>
          <input id="new-email" style={styles.input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div style={styles.fieldGroup}>
          <label htmlFor="new-password" style={styles.label}>Password</label>
          <input id="new-password" style={styles.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? 'Creating…' : 'Create User'}
        </button>
      </form>

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Username</th>
            <th style={styles.th}>Email</th>
            <th style={styles.th}>Admin</th>
            <th style={styles.th}>Created</th>
            <th style={styles.th}></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td style={styles.td}>{u.username}</td>
              <td style={styles.td}>{u.email}</td>
              <td style={styles.td}>{u.is_admin ? 'Yes' : 'No'}</td>
              <td style={styles.td}>{new Date(u.created_at).toLocaleDateString()}</td>
              <td style={styles.td}>
                <button style={styles.deleteBtn} onClick={() => handleDelete(u.id, u.username)}>Delete</button>
              </td>
            </tr>
          ))}
          {users.length === 0 && (
            <tr><td style={styles.td} colSpan={5}>No users found</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
