import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';
import { isAuthenticated } from '../auth';

const styles = {
  container: {
    maxWidth: '800px',
    margin: '32px auto',
    padding: '0 24px',
  },
  title: {
    color: 'var(--text-h)',
    margin: '0 0 16px',
    lineHeight: '1.3',
  },
  meta: {
    fontSize: '13px',
    color: 'var(--text)',
    margin: '0 0 24px',
  },
  likeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '24px',
  },
  likeButton: {
    background: 'none',
    border: '1px solid var(--border, #ccc)',
    borderRadius: '6px',
    padding: '6px 14px',
    fontSize: '16px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: 'var(--text)',
    transition: 'color 0.15s, border-color 0.15s',
  },
  likeButtonLiked: {
    background: 'none',
    border: '1px solid var(--accent)',
    borderRadius: '6px',
    padding: '6px 14px',
    fontSize: '16px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: 'var(--accent)',
    transition: 'color 0.15s, border-color 0.15s',
  },
  likeCount: {
    fontSize: '14px',
    color: 'var(--text)',
  },
  body: {
    fontSize: '15px',
    color: 'var(--text)',
    lineHeight: '1.7',
    whiteSpace: 'pre-wrap',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '24px',
    fontSize: '14px',
    color: 'var(--accent)',
    textDecoration: 'none',
  },
  error: {
    textAlign: 'center',
    marginTop: '80px',
    color: 'var(--text)',
  },
  loading: {
    textAlign: 'center',
    marginTop: '80px',
    color: 'var(--text)',
  },
  commentSection: {
    marginTop: '32px',
    borderTop: '1px solid var(--border)',
  },
  commentItem: {
    padding: '12px 0',
    borderBottom: '1px solid var(--border, #eee)',
  },
  commentMeta: {
    fontSize: '13px',
    color: 'var(--text)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  commentBody: {
    fontSize: '14px',
    margin: '4px 0 0',
    color: 'var(--text)',
    whiteSpace: 'pre-wrap',
  },
  commentForm: {
    marginTop: '16px',
    display: 'flex',
    gap: '8px',
  },
  textarea: {
    flex: 1,
    padding: '8px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    fontSize: '14px',
    resize: 'vertical',
    minHeight: '60px',
  },
  submitButton: {
    padding: '8px 16px',
    background: 'var(--accent)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  deleteButton: {
    background: 'none',
    border: 'none',
    color: 'var(--text)',
    cursor: 'pointer',
    fontSize: '13px',
    padding: '0 4px',
    opacity: 0.6,
  },
  commentError: {
    color: '#c0392b',
    fontSize: '13px',
    marginTop: '8px',
  },
};

export default function ArticleDetail() {
  const { id } = useParams();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState('');
  const [commentError, setCommentError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function fetchArticle() {
      setLoading(true);
      setError('');
      try {
        const res = await api.get(`/articles/${id}`);
        if (!cancelled) {
          setArticle(res.data);
          setLiked(!!res.data.user_has_liked);
          setLikeCount(res.data.like_count || 0);
        }
      } catch (err) {
        if (!cancelled) {
          const status = err.response?.status;
          if (status === 404) {
            setError('Article not found.');
          } else if (status === 403) {
            setError('You do not have permission to view this article.');
          } else {
            setError(err.response?.data?.message || 'Failed to load article.');
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchArticle();
    return () => { cancelled = true; };
  }, [id]);

  useEffect(() => {
    if (article && article.is_public) {
      api.get(`/articles/${id}/comments`)
        .then(res => setComments(res.data))
        .catch(() => {});
    }
  }, [article, id]);

  async function handleLike() {
    try {
      const res = await api.post(`/articles/${id}/like`);
      setLiked(res.data.liked);
      setLikeCount(res.data.like_count);
    } catch {
      // silently ignore like errors
    }
  }

  async function handleCommentSubmit(e) {
    e.preventDefault();
    setCommentError('');
    const trimmed = commentText.trim();
    if (!trimmed) return;
    try {
      const res = await api.post(`/articles/${id}/comments`, { body: trimmed });
      setComments(prev => [...prev, res.data]);
      setCommentText('');
    } catch (err) {
      setCommentError(err.response?.data?.message || 'Failed to post comment.');
    }
  }

  async function handleDeleteComment(commentId) {
    try {
      await api.delete(`/comments/${commentId}`);
      setComments(prev => prev.filter(c => c.id !== commentId));
    } catch {
      // backend enforces auth; silently ignore errors
    }
  }

  if (loading) {
    return <div style={styles.loading}><p>Loading…</p></div>;
  }

  if (error) {
    return (
      <div style={styles.error}>
        <p>{error}</p>
        <Link to="/articles" style={styles.backLink}>← Back to articles</Link>
      </div>
    );
  }

  if (!article) return null;

  return (
    <div style={styles.container}>
      <Link to="/articles" style={styles.backLink}>← Back to articles</Link>
      <h1 style={styles.title}>{article.title}</h1>
      <p style={styles.meta}>
        {article.author_username ? `By ${article.author_username} · ` : ''}
        {new Date(article.created_at).toLocaleDateString()}
        {article.is_public === false && ' · Private'}
      </p>
      {article.is_public && (
        <div style={styles.likeRow}>
          <button
            style={liked ? styles.likeButtonLiked : styles.likeButton}
            onClick={handleLike}
            aria-label={liked ? 'Unlike this article' : 'Like this article'}
          >
            {liked ? '♥' : '♡'}
          </button>
          <span style={styles.likeCount}>
            {likeCount} {likeCount === 1 ? 'like' : 'likes'}
          </span>
        </div>
      )}
      <div style={styles.body}>{article.body}</div>
      {article.is_public && (
        <div style={styles.commentSection}>
          <h2 style={{ margin: '24px 0 16px', color: 'var(--text-h)' }}>Comments</h2>
          {comments.length === 0 && (
            <p style={{ fontSize: '14px', color: 'var(--text)' }}>No comments yet.</p>
          )}
          {comments.map(comment => (
            <div key={comment.id} style={styles.commentItem}>
              <div style={styles.commentMeta}>
                <span>
                  <strong>{comment.author_username}</strong>{' · '}
                  {new Date(comment.created_at).toLocaleString()}
                </span>
                <button
                  style={styles.deleteButton}
                  onClick={() => handleDeleteComment(comment.id)}
                  aria-label="Delete comment"
                >
                  ×
                </button>
              </div>
              <p style={styles.commentBody}>{comment.body}</p>
            </div>
          ))}
          {isAuthenticated() && (
            <form onSubmit={handleCommentSubmit} style={styles.commentForm}>
              <textarea
                style={styles.textarea}
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Write a comment…"
                aria-label="Comment text"
              />
              <button type="submit" style={styles.submitButton}>Post</button>
            </form>
          )}
          {commentError && <p style={styles.commentError}>{commentError}</p>}
        </div>
      )}
    </div>
  );
}
