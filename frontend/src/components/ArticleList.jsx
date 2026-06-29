import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

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
  card: {
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '16px',
    textDecoration: 'none',
    display: 'block',
    color: 'inherit',
  },
  cardTitle: {
    margin: '0 0 8px',
    fontSize: '18px',
    color: 'var(--text-h)',
  },
  meta: {
    fontSize: '13px',
    color: 'var(--text)',
    margin: '0 0 12px',
  },
  preview: {
    fontSize: '14px',
    color: 'var(--text)',
    margin: 0,
    lineHeight: '1.5',
  },
  counts: {
    display: 'flex',
    gap: '12px',
    fontSize: '13px',
    color: 'var(--text)',
    marginTop: '10px',
  },
  empty: {
    textAlign: 'center',
    color: 'var(--text)',
    marginTop: '48px',
  },
  error: {
    padding: '8px 12px',
    borderRadius: '4px',
    background: '#fed7d7',
    color: '#822727',
    fontSize: '14px',
  },
};

export default function ArticleList({ endpoint, title }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function fetchArticles() {
      setLoading(true);
      setError('');
      try {
        const res = await api.get(endpoint);
        if (!cancelled) setArticles(res.data);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.message || 'Failed to load articles');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchArticles();
    return () => { cancelled = true; };
  }, [endpoint]);

  if (loading) {
    return <div style={styles.container}><p style={styles.empty}>Loading…</p></div>;
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{title}</h2>

      {error && <div style={styles.error} role="alert">{error}</div>}

      {!error && articles.length === 0 && (
        <p style={styles.empty}>No articles found.</p>
      )}

      {articles.map((article) => (
        <Link key={article.id} to={`/articles/${article.id}`} style={styles.card}>
          <h3 style={styles.cardTitle}>{article.title}</h3>
          <p style={styles.meta}>
            {article.author_username ? `By ${article.author_username} · ` : ''}
            {new Date(article.created_at).toLocaleDateString()}
          </p>
          <p style={styles.preview}>
            {article.preview ?? article.body?.slice(0, 200) ?? ''}
          </p>
          <div style={styles.counts}>
            <span>♥ {article.like_count ?? 0}</span>
            <span>💬 {article.comment_count ?? 0}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
