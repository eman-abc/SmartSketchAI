import { API_BASE_URL } from '../config';
import type { ForensicStreamEvent, ForensicStreamEventType } from '../types';
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from './authStore';

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: any;
  skipAuth?: boolean;
};

/**
 * Call the refresh endpoint and return the new access token, or null if refresh fails.
 */
async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${API_BASE_URL}/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) return null;
  const data = (await res.json()) as { access: string };
  setTokens(data.access, refresh);
  return data.access;
}

/**
 * Redirect to login when session is invalid (e.g. refresh failed).
 */
function redirectToLogin(): void {
  clearTokens();
  window.location.href = '/login';
}

/**
 * API request with:
 * - Base URL prefix
 * - JSON body/headers when body is an object
 * - Authorization: Bearer <access> for protected calls (unless skipAuth)
 * - On 401: try refresh once, retry request; if refresh fails, redirect to login
 */
export async function request<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, skipAuth = false, headers = {}, ...init } = options;

  const url = path.startsWith('http') ? path : `${API_BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
  const reqHeaders: HeadersInit = {
    ...(typeof headers === 'object' && !(headers instanceof Headers)
      ? headers
      : {}),
  } as Record<string, string>;

  if (body !== undefined) {
    reqHeaders['Content-Type'] = 'application/json';
  }
  if (!skipAuth) {
    const access = getAccessToken();
    if (access) reqHeaders['Authorization'] = `Bearer ${access}`;
  }

  let res = await fetch(url, {
    ...init,
    headers: reqHeaders,
    body:
      body === undefined
        ? undefined
        : typeof body === 'string'
          ? body
          : JSON.stringify(body),
  });

  if (res.status === 401 && !skipAuth) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      reqHeaders['Authorization'] = `Bearer ${newAccess}`;
      res = await fetch(url, {
        ...init,
        headers: reqHeaders,
        body:
          body === undefined
            ? undefined
            : typeof body === 'string'
              ? body
              : JSON.stringify(body),
      });
    }
    if (res.status === 401) {
      redirectToLogin();
      throw new Error('Unauthorized');
    }
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = (await res.json()) as { error?: string; detail?: string };
      message = data.error ?? data.detail ?? message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  const contentType = res.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

/** POST /api/token/ - login, no auth */
export async function loginWithToken(username: string, password: string) {
  return request<{ access: string; refresh: string }>('token/', {
    method: 'POST',
    body: { username, password },
    skipAuth: true,
  });
}

/** POST /api/token/refresh/ - refresh, no auth */
export async function refreshToken() {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token');
  return request<{ access: string }>('token/refresh/', {
    method: 'POST',
    body: { refresh },
    skipAuth: true,
  });
}

/** POST /api/register/ - register, no auth */
export async function registerUser(body: {
  username: string;
  email: string;
  password: string;
  role?: string;
}) {
  return request<unknown>('register/', {
    method: 'POST',
    body: { ...body, role: body.role ?? 'general' },
    skipAuth: true,
  });
}

/** POST /api/forensic/generate/ */
export async function generateForensicSketch(body: {
  prompt: string;
  case_type?: string;
  age?: number | null;
}) {
  return request<any>('forensic/generate/', {
    method: 'POST',
    body,
  });
}

/** POST /api/forensic/edit/ */
export async function editForensicSketch(body: {
  original_image_id: number;
  edit_prompt: string;
  strength?: number;
}) {
  return request<any>('forensic/edit/', {
    method: 'POST',
    body,
  });
}

/** POST /api/forensic/age/ */
export async function ageForensicSketch(body: {
  original_image_id: number;
  years: number;
}) {
  return request<any>('forensic/age/', {
    method: 'POST',
    body,
  });
}

/** GET /api/my-images/ */
export async function fetchUserImages() {
  return request<any[]>('my-images/', {
    method: 'GET',
  });
}

/** POST /api/forensic/chat/ */
export async function agentChat(body: {
  message: string;
  thread_id?: string;
  case_number?: string;
}) {
  return request<any>('forensic/chat/', {
    method: 'POST',
    body,
  });
}

/**
 * POST /api/forensic/chat/stream/ using fetch streaming and SSE-formatted chunks.
 * Uses Bearer token auth (native EventSource cannot set headers).
 */
export async function agentChatStream(
  body: { message: string; thread_id?: string; case_number?: string },
  onEvent: (event: ForensicStreamEvent) => void
): Promise<void> {
  const access = getAccessToken();
  const url = `${API_BASE_URL.replace(/\/$/, '')}/forensic/chat/stream/`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let message = res.statusText || 'Stream request failed';
    try {
      const err = (await res.json()) as { error?: string; detail?: string };
      message = err.error ?? err.detail ?? message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  if (!res.body) {
    throw new Error('Streaming response body is not available');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const flushBlock = (block: string) => {
    const lines = block.split('\n');
    let eventName: ForensicStreamEventType = 'status';
    let dataStr = '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const value = line.slice(7).trim();
        if (value === 'status' || value === 'progress' || value === 'result' || value === 'error') {
          eventName = value;
        }
      } else if (line.startsWith('data: ')) {
        dataStr += line.slice(6);
      }
    }

    if (!dataStr) return;
    try {
      const parsed = JSON.parse(dataStr) as ForensicStreamEvent['data'];
      onEvent({ event: eventName, data: parsed });
    } catch {
      onEvent({ event: 'error', data: { error: 'Failed to parse stream payload' } });
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (block) flushBlock(block);
      boundary = buffer.indexOf('\n\n');
    }
  }

  const trailing = buffer.trim();
  if (trailing) {
    flushBlock(trailing);
  }
}

/** POST /api/forensic/sketch-style/ — convert to pencil/charcoal */
export async function convertSketchStyle(body: {
  generation_id: string;
  style: 'pencil' | 'charcoal';
}) {
  return request<any>('forensic/sketch-style/', {
    method: 'POST',
    body,
  });
}

/** POST /api/forensic/export-report/ — download PDF forensic report */
export async function exportForensicReport(generationId: string): Promise<Blob> {
  const access = getAccessToken();
  const url = `${API_BASE_URL.replace(/\/$/, '')}/forensic/export-report/`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
    body: JSON.stringify({ generation_id: generationId }),
  });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.statusText}`);
  }
  return res.blob();
}
