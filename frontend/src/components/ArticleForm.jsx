import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
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
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: 'var(--text-h)',
  },
  textarea: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: 'var(--text-h)',
    minHeight: '200px',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  select: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: 'var(--text-h)',
    width: '180px',
  },
  wordCount: {
    fontSize: '12px',
    color: 'var(--text)',
    textAlign: 'right',
    margin: 0,
  },
  wordCountOver: {
    fontSize: '12px',
    color: '#e53e3e',
    textAlign: 'right',
    margin: 0,
  },
  button: {
    padding: '10px 20px',
    fontSize: '16px',
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  error: {
    background: '#fed7d7',
    color: '#822727',
    padding: '8px 12px',
    borderRadius: '4px',
    fontSize: '14px',
  },
};

function countWords(text) {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

export default function ArticleForm() {
  const [titleVal, setTitleVal] = useState('');
  const [body, setBody] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const wordCount = countWords(body);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/articles', { title: titleVal, body, visibility });
      navigate(`/articles/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create article');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>New Article</h2>

      {error && <div style={styles.error} role="alert">{error}</div>}

      <form style={styles.form} onSubmit={handleSubmit}>
        <div style={styles.fieldGroup}>
          <label htmlFor="article-title" style={styles.label}>Title</label>
          <input
            id="article-title"
            style={styles.input}
            type="text"
            value={titleVal}
            onChange={(e) => setTitleVal(e.target.value)}
            placeholder="Article title"
            required
          />
        </div>

        <div style={styles.fieldGroup}>
          <label htmlFor="article-body" style={styles.label}>Body</label>
          <textarea
            id="article-body"
            style={styles.textarea}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your article…"
          />
          <p style={wordCount > 1000 ? styles.wordCountOver : styles.wordCount}>
            {wordCount} / 1000 words
          </p>
        </div>

        <div style={styles.fieldGroup}>
          <label htmlFor="article-visibility" style={styles.label}>Visibility</label>
          <select
            id="article-visibility"
            style={styles.select}
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
          >
            <option value="public">Public</option>
            <option value="private">Private</option>
          </select>
        </div>

        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? 'Publishing…' : 'Publish Article'}
        </button>
      </form>
    </div>
  );
}
