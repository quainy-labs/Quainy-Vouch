const API_BASES = Array.from(
  new Set([import.meta.env.VITE_API_BASE, "http://127.0.0.1:8000", "http://127.0.0.1:8001"].filter(Boolean) as string[]),
);

let resolvedApiBase: string | null = null;

export const AUTH_TOKEN_KEY = "quainy_vouch_auth_token";

function fieldNameFromLocation(location: unknown[]): string {
  const parts = location
    .filter((item) => typeof item === "string")
    .filter((item) => !["body", "query", "path"].includes(item));
  const field = parts[parts.length - 1];
  if (!field) return "Request";
  return field.replace(/_/g, " ");
}

async function responseErrorMessage(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}.`;
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    try {
      const text = await response.text();
      return text || fallback;
    } catch {
      return fallback;
    }
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!item || typeof item !== "object") return "";
          const issue = item as { loc?: unknown[]; msg?: unknown };
          const label = Array.isArray(issue.loc) ? fieldNameFromLocation(issue.loc) : "Field";
          return `${label}: ${String(issue.msg ?? "Invalid value")}`;
        })
        .filter(Boolean);
      if (messages.length > 0) return messages.join("\n");
    }
  }
  return fallback;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const bases = resolvedApiBase ? [resolvedApiBase, ...API_BASES.filter((base) => base !== resolvedApiBase)] : API_BASES;
  let lastError: unknown = null;
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  for (const base of bases) {
    let response: Response;
    try {
      response = await fetch(`${base}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(init?.headers ?? {}),
        },
      });
    } catch (error) {
      lastError = error;
      continue;
    }
    resolvedApiBase = base;
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response));
    }
    return response.json();
  }
  throw new Error(
    `The workspace service is unavailable. Please check that the app services are running and try again.${
      lastError instanceof Error ? ` ${lastError.message}` : ""
    }`,
  );
}
