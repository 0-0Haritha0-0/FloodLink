/**
 * FloodLink API Client Service
 * Encapsulates HTTP communication with the FastAPI backend using native fetch.
 */

const API_BASE_URL = "http://localhost:8000/api";

/**
 * Generic helper for handling fetch requests and JSON responses.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    "Content-Type": "application/json",
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const res = await fetch(url, config);
    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMsg = data?.detail || `HTTP Error ${res.status}: ${res.statusText}`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      throw new Error(
        "Cannot connect to the FloodLink backend server at http://localhost:8000. Please ensure FastAPI is running."
      );
    }
    throw err;
  }
}

// ---------------- CITIZEN APIS ----------------

export async function submitCitizenReport(reportData) {
  return request("/reports", {
    method: "POST",
    body: JSON.stringify(reportData),
  });
}

export async function trackCitizenReport(reportId) {
  return request(`/reports/${encodeURIComponent(reportId.trim())}`);
}

export async function fetchPublicReports(params = {}) {
  const query = new URLSearchParams();
  if (params.severity) query.append("severity", params.severity);
  if (params.status) query.append("status", params.status);
  if (params.search) query.append("search", params.search);
  const qs = query.toString() ? `?${query.toString()}` : "";
  return request(`/reports${qs}`);
}

// ---------------- AUTH APIS ----------------

export async function loginUser(username, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function fetchUserProfile(token) {
  return request("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function logoutUser(token) {
  return request("/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ---------------- ADMIN APIS ----------------

export async function fetchAdminStats(token) {
  return request("/admin/stats", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchAdminReports(token, params = {}) {
  const query = new URLSearchParams();
  if (params.severity) query.append("severity", params.severity);
  if (params.status) query.append("status", params.status);
  if (params.search) query.append("search", params.search);
  const qs = query.toString() ? `?${query.toString()}` : "";
  return request(`/admin/reports${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateReportByAdmin(token, reportId, updateData) {
  return request(`/admin/reports/${encodeURIComponent(reportId)}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(updateData),
  });
}

// ---------------- RESCUE TEAM APIS ----------------

export async function fetchRescueTeams(token) {
  return request("/rescue/teams", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchRescueAssignments(token, teamName = "") {
  const qs = teamName ? `?team_name=${encodeURIComponent(teamName)}` : "";
  return request(`/rescue/assignments${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateRescueProgress(token, reportId, progressData) {
  return request(`/rescue/reports/${encodeURIComponent(reportId)}/progress`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(progressData),
  });
}
