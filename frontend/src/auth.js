const TOKEN_KEY = 'blog_portal_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return !!getToken();
}

/**
 * Decode the JWT payload for UI display purposes only (e.g., showing/hiding
 * the admin link). This does NOT verify the token signature — all actual
 * authorization is enforced server-side. Never use these claims to gate
 * security-sensitive operations on the client.
 */
export function decodeToken() {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return { user_id: payload.user_id, is_admin: payload.is_admin };
  } catch {
    return null;
  }
}
