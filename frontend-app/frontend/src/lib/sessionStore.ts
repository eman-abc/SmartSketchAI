import type { ChatSession } from '../types';

const STORAGE_KEY = 'smartsketch_sessions';
const CURRENT_SESSION_KEY = 'smartsketch_current_session';

function generateId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function getSessions(): ChatSession[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function getCurrentSessionId(): string | null {
  return localStorage.getItem(CURRENT_SESSION_KEY);
}

export function setCurrentSessionId(id: string | null): void {
  if (id) {
    localStorage.setItem(CURRENT_SESSION_KEY, id);
  } else {
    localStorage.removeItem(CURRENT_SESSION_KEY);
  }
}

export function createSession(): ChatSession {
  const session: ChatSession = {
    id: generateId(),
    title: 'New Session',
    prompt: '',
    generateResult: null,
    editResult: null,
    createdAt: Date.now(),
  };
  
  const sessions = getSessions();
  sessions.unshift(session);
  saveSessions(sessions);
  setCurrentSessionId(session.id);
  
  return session;
}

export function updateSession(
  sessionId: string,
  updates: Partial<Pick<ChatSession, 'title' | 'prompt' | 'generateResult' | 'editResult'>>
): ChatSession | null {
  const sessions = getSessions();
  const index = sessions.findIndex(s => s.id === sessionId);
  
  if (index === -1) return null;
  
  sessions[index] = { ...sessions[index], ...updates };
  
  // Auto-generate title from prompt if not set
  if (updates.prompt && sessions[index].title === 'New Session') {
    sessions[index].title = updates.prompt.slice(0, 30) + (updates.prompt.length > 30 ? '...' : '');
  }
  
  saveSessions(sessions);
  return sessions[index];
}

export function getSession(sessionId: string): ChatSession | null {
  const sessions = getSessions();
  return sessions.find(s => s.id === sessionId) || null;
}

export function deleteSession(sessionId: string): void {
  const sessions = getSessions().filter(s => s.id !== sessionId);
  saveSessions(sessions);
  
  if (getCurrentSessionId() === sessionId) {
    setCurrentSessionId(sessions[0]?.id || null);
  }
}

export function clearAllSessions(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(CURRENT_SESSION_KEY);
}
