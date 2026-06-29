import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { removeToken, decodeToken } from '../auth';

const styles = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '12px 24px',
    borderBottom: '1px solid var(--border)',
    flexWrap: 'wrap',
  },
  brand: {
    fontWeight: 600,
    fontSize: '18px',
    color: 'var(--text-h)',
    textDecoration: 'none',
    marginRight: 'auto',
  },
  link: {
    color: 'var(--text)',
    textDecoration: 'none',
    fontSize: '15px',
  },
  button: {
    padding: '6px 14px',
    fontSize: '14px',
    background: 'transparent',
    color: 'var(--text)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

export default function NavBar() {
  const navigate = useNavigate();
  const decoded = decodeToken();

  async function handleLogout() {
    try {
      await api.post('/auth/logout');
    } catch {
      // proceed even if logout call fails
    }
    removeToken();
    navigate('/login');
  }

  return (
    <nav style={styles.nav}>
      <Link to="/articles" style={styles.brand}>Blog Portal</Link>
      <Link to="/articles" style={styles.link}>Public Articles</Link>
      <Link to="/articles/mine" style={styles.link}>My Articles</Link>
      <Link to="/articles/new" style={styles.link}>New Article</Link>
      {decoded?.is_admin && (
        <Link to="/admin" style={styles.link}>Admin</Link>
      )}
      <button style={styles.button} onClick={handleLogout}>Logout</button>
    </nav>
  );
}
