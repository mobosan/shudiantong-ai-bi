export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem('sdt_token');
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers } });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.includes('/login')) { sessionStorage.removeItem('sdt_token'); window.dispatchEvent(new Event('auth-expired')); }
    throw new Error(typeof data.detail === 'string' ? data.detail : '请求参数无效，请检查输入');
  }
  return data as T;
}
