export const AUTH_STORAGE_KEY = "agent-rh-auth-token";

function getLocalStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readAuthToken() {
  const storage = getLocalStorage();
  if (!storage) {
    return "";
  }

  try {
    return storage.getItem(AUTH_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function writeAuthToken(token) {
  const storage = getLocalStorage();
  if (!storage) {
    return false;
  }

  try {
    storage.setItem(AUTH_STORAGE_KEY, token);
    return true;
  } catch {
    return false;
  }
}

export function clearAuthToken() {
  const storage = getLocalStorage();
  if (!storage) {
    return false;
  }

  try {
    storage.removeItem(AUTH_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
