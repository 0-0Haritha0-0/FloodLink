import React, { useState, useEffect } from "react";
import {
  submitCitizenReport,
  trackCitizenReport,
  fetchPublicReports,
  loginUser,
  fetchAdminStats,
  fetchAdminReports,
  updateReportByAdmin,
  fetchRescueTeams,
  fetchRescueAssignments,
  updateRescueProgress,
} from "./services/api";

export default function App() {
  const [currentTab, setCurrentTab] = useState("home");
  const [authSession, setAuthSession] = useState(() => {
    const saved = localStorage.getItem("floodlink_auth");
    return saved ? JSON.parse(saved) : null;
  });

  const saveAuth = (session) => {
    setAuthSession(session);
    if (session) {
      localStorage.setItem("floodlink_auth", JSON.stringify(session));
    } else {
      localStorage.removeItem("floodlink_auth");
    }
  };

  const handleLogout = () => {
    saveAuth(null);
    setCurrentTab("home");
  };

  return (
    <div>
      {/* Main Navigation Header */}
      <header className="header-bar">
        <div className="brand" onClick={() => setCurrentTab("home")}>
          <span className="brand-icon">🌊</span>
          <div>
            <div className="brand-title">FloodLink</div>
            <div className="brand-subtitle">Emergency Disaster Platform</div>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${currentTab === "home" ? "active" : ""}`}
            onClick={() => setCurrentTab("home")}
          >
            Overview
          </button>
          <button
            className={`nav-btn ${currentTab === "report" ? "active" : ""}`}
            onClick={() => setCurrentTab("report")}
          >
            🆘 Report Flood
          </button>
          <button
            className={`nav-btn ${currentTab === "track" ? "active" : ""}`}
            onClick={() => setCurrentTab("track")}
          >
            🔍 Track Report
          </button>
          <button
            className={`nav-btn ${currentTab === "feed" ? "active" : ""}`}
            onClick={() => setCurrentTab("feed")}
          >
            📋 Incident Feed
          </button>
          <button
            className={`nav-btn ${currentTab === "map" ? "active" : ""}`}
            onClick={() => setCurrentTab("map")}
          >
            🗺️ Incident Map
          </button>
          <button
            className={`nav-btn ${currentTab === "admin" ? "active" : ""}`}
            onClick={() => setCurrentTab("admin")}
          >
            🛡️ Admin Panel
          </button>
          <button
            className={`nav-btn ${currentTab === "rescue" ? "active" : ""}`}
            onClick={() => setCurrentTab("rescue")}
          >
            🚤 Rescue Team
          </button>

          {authSession && (
            <div className="user-badge">
              <span>👤 {authSession.username} ({authSession.role})</span>
              <button className="logout-btn" onClick={handleLogout}>
                Exit
              </button>
            </div>
          )}
        </nav>
      </header>

      {/* Main Container Views */}
      <main className="container">
        {currentTab === "home" && (
          <HomeView onNavigate={(tab) => setCurrentTab(tab)} />
        )}
        {currentTab === "report" && (
          <ReportView onTrackCreated={(id) => {
            setCurrentTab("track");
            window.sessionStorage.setItem("prefill_id", id);
          }} />
        )}
        {currentTab === "track" && <TrackView />}
        {currentTab === "feed" && <FeedView />}
        {currentTab === "map" && (
          <MapView
            onTrackReport={(id) => {
              setCurrentTab("track");
              window.sessionStorage.setItem("prefill_id", id);
            }}
          />
        )}
        {currentTab === "admin" && (
          <AdminView authSession={authSession} onLoginSuccess={saveAuth} />
        )}
        {currentTab === "rescue" && (
          <RescueView authSession={authSession} onLoginSuccess={saveAuth} />
        )}
      </main>
    </div>
  );
}

/* -------------------------------------------------------------
   1. HOME VIEW
------------------------------------------------------------- */
function HomeView({ onNavigate }) {
  return (
    <div>
      <div className="card hero-card">
        <h1 className="hero-title">Real-Time Flood Response & Coordination</h1>
        <p className="hero-desc">
          An emergency platform empowering citizens to submit instant distress reports and enabling rescue teams & disaster coordinators to dispatch aid rapidly with end-to-end status tracking.
        </p>
        <div className="sdg-tags">
          <span className="sdg-tag">🌍 SDG 13: Climate Action</span>
          <span className="sdg-tag">🏙️ SDG 11: Sustainable Cities & Communities</span>
        </div>
      </div>

      <div className="grid-2">
        <div className="action-card" onClick={() => onNavigate("report")}>
          <div className="action-icon">🆘</div>
          <div className="action-title">Submit Flood / SOS Report</div>
          <div className="action-desc">
            Report flood water rise, trapped citizens, or urgent evacuation requirements. Receive an instant tracking ID.
          </div>
        </div>

        <div className="action-card" onClick={() => onNavigate("track")}>
          <div className="action-icon">🔍</div>
          <div className="action-title">Track Status by ID</div>
          <div className="action-desc">
            Check live response progress for your emergency submission (Pending → Assigned → In Progress → Resolved).
          </div>
        </div>

        <div className="action-card" onClick={() => onNavigate("feed")}>
          <div className="action-icon">📋</div>
          <div className="action-title">Public Incident Feed</div>
          <div className="action-desc">
            Browse active flood reports across sectors with severity and status filters.
          </div>
        </div>

        <div className="action-card" onClick={() => onNavigate("map")}>
          <div className="action-icon">🗺️</div>
          <div className="action-title">Location Incident Map</div>
          <div className="action-desc">
            Interactive sector map clustering flood distress reports across municipal wards and zones.
          </div>
        </div>

        <div className="action-card" onClick={() => onNavigate("admin")}>
          <div className="action-icon">🛡️</div>
          <div className="action-title">Coordinator & Rescue Dispatch</div>
          <div className="action-desc">
            Authorized management center to view live metrics, assign rescue squads, and record field progress.
          </div>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------
   2. CITIZEN REPORT FORM VIEW
------------------------------------------------------------- */
function ReportView({ onTrackCreated }) {
  const [formData, setFormData] = useState({
    citizen_name: "",
    location: "",
    description: "",
    severity: "Medium",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [createdReport, setCreatedReport] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.citizen_name.trim() || !formData.location.trim() || !formData.description.trim()) {
      setError("Please fill in all mandatory fields.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await submitCitizenReport(formData);
      setCreatedReport(res);
      setFormData({
        citizen_name: "",
        location: "",
        description: "",
        severity: "Medium",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: "680px", margin: "0 auto" }}>
      <h2 style={{ color: "#0369a1", marginBottom: "6px" }}>🆘 Report a Flood Emergency</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "20px", fontSize: "0.95rem" }}>
        Submit details regarding local waterlogging, rising flood levels, or trapped citizens.
      </p>

      {error && <div className="alert-box alert-error">❌ {error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Reporter Name *</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. Aditi Sharma"
            value={formData.citizen_name}
            onChange={(e) => setFormData({ ...formData, citizen_name: e.target.value })}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Incident Location & Landmark *</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. Near River Bridge, Sector 4, Ward 7"
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Severity Level *</label>
          <select
            className="form-select"
            value={formData.severity}
            onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
          >
            <option value="Low">Low — Minor road puddling or slow water accumulation</option>
            <option value="Medium">Medium — Water entering ground floors, vehicles immobilized</option>
            <option value="High">High — Water above knee level, evacuation required</option>
            <option value="Critical">Critical — Immediate life danger, stranded on roof / urgent rescue</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Situation Description *</label>
          <textarea
            className="form-textarea"
            placeholder="Describe the number of people, water level depth, specific hazards, etc."
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
          />
        </div>

        <button type="submit" className="btn-primary" style={{ width: "100%" }} disabled={submitting}>
          {submitting ? "Submitting Emergency Report..." : "Submit Distress Report"}
        </button>
      </form>

      {/* Confirmation Modal */}
      {createdReport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title" style={{ color: "#16a34a" }}>✅ Report Logged Successfully</h3>
              <button className="modal-close" onClick={() => setCreatedReport(null)}>×</button>
            </div>
            <p style={{ color: "var(--text-muted)", marginBottom: "16px" }}>
              Your emergency request has been received and routed to our central disaster dispatch queue.
            </p>
            <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", textAlign: "center", marginBottom: "20px" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>YOUR TRACKING ID</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#0369a1", letterSpacing: "1px", margin: "6px 0" }}>
                {createdReport.report_id}
              </div>
              <span className={`badge stat-${createdReport.status.replace(/\s+/g, '')}`}>
                Status: {createdReport.status}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                className="btn-primary"
                style={{ flex: 1 }}
                onClick={() => onTrackCreated(createdReport.report_id)}
              >
                Track Status Now
              </button>
              <button
                className="btn-outline"
                style={{ flex: 1 }}
                onClick={() => setCreatedReport(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   3. REPORT TRACKING VIEW
------------------------------------------------------------- */
function TrackView() {
  const [reportIdInput, setReportIdInput] = useState(() => {
    return window.sessionStorage.getItem("prefill_id") || "";
  });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTrack = async (e) => {
    if (e) e.preventDefault();
    if (!reportIdInput.trim()) return;

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const data = await trackCitizenReport(reportIdInput);
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (reportIdInput) {
      handleTrack();
    }
  }, []);

  const steps = ["Pending", "Assigned", "In Progress", "Resolved"];
  const currentStepIndex = report ? steps.indexOf(report.status) : -1;

  return (
    <div className="card" style={{ maxWidth: "780px", margin: "0 auto" }}>
      <h2 style={{ color: "#0369a1", marginBottom: "6px" }}>🔍 Track Your Emergency Request</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "20px", fontSize: "0.95rem" }}>
        Enter your unique Tracking ID (e.g. <code>FL-XXXXXXXX</code>) to view dispatch updates and rescue status.
      </p>

      <form onSubmit={handleTrack} style={{ display: "flex", gap: "10px", marginBottom: "24px" }}>
        <input
          type="text"
          className="form-input"
          placeholder="Enter Report ID (e.g. FL-A89D2F)"
          value={reportIdInput}
          onChange={(e) => setReportIdInput(e.target.value)}
          required
        />
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Searching..." : "Track"}
        </button>
      </form>

      {error && <div className="alert-box alert-error">❌ {error}</div>}

      {report && (
        <div style={{ marginTop: "24px", borderTop: "1px solid var(--border-color)", paddingTop: "24px" }}>
          {/* Progress Timeline */}
          <div className="timeline">
            {steps.map((step, idx) => {
              const isCompleted = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;
              return (
                <div
                  key={step}
                  className={`timeline-step ${isCompleted ? "completed" : ""} ${isCurrent ? "current" : ""}`}
                >
                  <div className="step-circle">{idx + 1}</div>
                  <div className="step-label">{step}</div>
                </div>
              );
            })}
          </div>

          <div className="grid-2" style={{ marginTop: "24px" }}>
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>TRACKING ID</div>
              <div style={{ fontSize: "1.2rem", fontWeight: "700", color: "#0369a1" }}>{report.report_id}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>SEVERITY & STATUS</div>
              <div style={{ marginTop: "4px" }}>
                <span className={`badge sev-${report.severity}`} style={{ marginRight: "8px" }}>
                  {report.severity} Severity
                </span>
                <span className={`badge stat-${report.status.replace(/\s+/g, '')}`}>
                  {report.status}
                </span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>INCIDENT LOCATION</div>
              <div style={{ fontWeight: "500", marginTop: "2px" }}>{report.location}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>ASSIGNED RESCUE SQUAD</div>
              <div style={{ fontWeight: "600", color: report.assigned_team ? "#0284c7" : "var(--text-muted)", marginTop: "2px" }}>
                {report.assigned_team || "Awaiting Coordinator Assignment"}
              </div>
            </div>
          </div>

          <div style={{ marginTop: "16px" }}>
            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "600" }}>DESCRIPTION</div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", marginTop: "4px", fontSize: "0.95rem" }}>
              {report.description}
            </div>
          </div>

          {report.admin_notes && (
            <div style={{ marginTop: "16px" }}>
              <div style={{ fontSize: "0.85rem", color: "#0369a1", fontWeight: "700" }}>RESCUE DISPATCH & PROGRESS NOTES</div>
              <pre style={{
                background: "#e0f2fe",
                color: "#0369a1",
                padding: "12px",
                borderRadius: "8px",
                marginTop: "4px",
                fontSize: "0.85rem",
                whiteSpace: "pre-wrap",
                fontFamily: "inherit"
              }}>
                {report.admin_notes}
              </pre>
            </div>
          )}

          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "16px" }}>
            Logged: {new Date(report.created_at).toLocaleString()} | Last Updated: {new Date(report.updated_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   4. INCIDENT FEED VIEW
------------------------------------------------------------- */
function FeedView() {
  const [reports, setReports] = useState([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await fetchPublicReports({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setReports(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [severityFilter, statusFilter]);

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ color: "#0369a1" }}>📋 Public Incident Feed</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>Live register of reported flood emergencies.</p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <select
            className="form-select"
            style={{ width: "auto" }}
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="Critical">Critical Only</option>
            <option value="High">High Only</option>
            <option value="Medium">Medium Only</option>
            <option value="Low">Low Only</option>
          </select>

          <select
            className="form-select"
            style={{ width: "auto" }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="Assigned">Assigned</option>
            <option value="In Progress">In Progress</option>
            <option value="Resolved">Resolved</option>
          </select>

          <form onSubmit={(e) => { e.preventDefault(); loadReports(); }} style={{ display: "flex", gap: "6px" }}>
            <input
              type="text"
              className="form-input"
              placeholder="Search location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: "180px" }}
            />
            <button type="submit" className="btn-outline">Filter</button>
          </form>
        </div>
      </div>

      {loading ? (
        <p style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px" }}>Loading incident reports...</p>
      ) : reports.length === 0 ? (
        <p style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px" }}>No matching reports found.</p>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tracking ID</th>
                <th>Location</th>
                <th>Description</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Assigned Unit</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.report_id}>
                  <td><strong>{r.report_id}</strong></td>
                  <td>{r.location}</td>
                  <td style={{ maxWidth: "280px" }}>{r.description}</td>
                  <td><span className={`badge sev-${r.severity}`}>{r.severity}</span></td>
                  <td><span className={`badge stat-${r.status.replace(/\s+/g, '')}`}>{r.status}</span></td>
                  <td>{r.assigned_team || "—"}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   5. ADMIN MANAGEMENT VIEW
------------------------------------------------------------- */
function AdminView({ authSession, onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [teams, setTeams] = useState([]);
  const [activeModalReport, setActiveModalReport] = useState(null);
  const [updateStatus, setUpdateStatus] = useState("");
  const [updateTeam, setUpdateTeam] = useState("");
  const [updateNotes, setUpdateNotes] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    try {
      const data = await loginUser(username, password);
      if (data.role !== "admin") {
        setLoginError("Access denied. Admin privileges required.");
        return;
      }
      onLoginSuccess(data);
    } catch (err) {
      setLoginError(err.message);
    }
  };

  const loadAdminData = async () => {
    if (!authSession || authSession.role !== "admin") return;
    try {
      const [statsData, reportsData, teamsData] = await Promise.all([
        fetchAdminStats(authSession.access_token),
        fetchAdminReports(authSession.access_token),
        fetchRescueTeams(authSession.access_token),
      ]);
      setStats(statsData);
      setReports(reportsData);
      setTeams(teamsData);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, [authSession]);

  const handleOpenModal = (r) => {
    setActiveModalReport(r);
    setUpdateStatus(r.status);
    setUpdateTeam(r.assigned_team || "");
    setUpdateNotes(r.admin_notes || "");
  };

  const handleSaveUpdate = async (e) => {
    e.preventDefault();
    try {
      await updateReportByAdmin(authSession.access_token, activeModalReport.report_id, {
        status: updateStatus,
        assigned_team: updateTeam || null,
        admin_notes: updateNotes || null,
      });
      setActiveModalReport(null);
      loadAdminData();
    } catch (err) {
      alert("Error updating report: " + err.message);
    }
  };

  if (!authSession || authSession.role !== "admin") {
    return (
      <div className="card" style={{ maxWidth: "440px", margin: "40px auto" }}>
        <h2 style={{ color: "#0369a1", marginBottom: "8px" }}>🛡️ Admin Coordinator Login</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "20px" }}>
          Authorized access to emergency dispatch command center.
        </p>

        {loginError && <div className="alert-box alert-error">❌ {loginError}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              className="form-input"
              placeholder="Enter admin username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Enter admin password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Authenticate & Open Dashboard
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h2 style={{ color: "#0369a1" }}>🛡️ Emergency Operations Command</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>Live incident triage and rescue dispatch center.</p>
        </div>
        <button className="btn-outline" onClick={loadAdminData}>🔄 Refresh Data</button>
      </div>

      {/* KPI Counters */}
      {stats && (
        <div className="grid-4" style={{ marginBottom: "24px" }}>
          <div className="stat-card">
            <div className="stat-number">{stats.total_reports}</div>
            <div className="stat-label">Total Incidents</div>
          </div>
          <div className="stat-card">
            <div className="stat-number" style={{ color: "var(--stat-pending)" }}>{stats.pending}</div>
            <div className="stat-label">Pending Triage</div>
          </div>
          <div className="stat-card">
            <div className="stat-number" style={{ color: "var(--stat-inprogress)" }}>{stats.in_progress}</div>
            <div className="stat-label">In Progress</div>
          </div>
          <div className="stat-card">
            <div className="stat-number" style={{ color: "var(--stat-resolved)" }}>{stats.resolved}</div>
            <div className="stat-label">Resolved</div>
          </div>
        </div>
      )}

      {/* Incident Management Table */}
      <div className="card">
        <h3 style={{ marginBottom: "16px", color: "#334155" }}>All Emergency Incident Submissions</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Citizen Name</th>
                <th>Location</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Assigned Squad</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.report_id}>
                  <td><strong>{r.report_id}</strong></td>
                  <td>{r.citizen_name}</td>
                  <td>{r.location}</td>
                  <td><span className={`badge sev-${r.severity}`}>{r.severity}</span></td>
                  <td><span className={`badge stat-${r.status.replace(/\s+/g, '')}`}>{r.status}</span></td>
                  <td>{r.assigned_team || <span style={{ color: "#94a3b8" }}>Unassigned</span>}</td>
                  <td>
                    <button className="btn-outline" style={{ padding: "4px 10px", fontSize: "0.85rem" }} onClick={() => handleOpenModal(r)}>
                      Manage / Assign
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Admin Action Modal */}
      {activeModalReport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Incident {activeModalReport.report_id}</h3>
              <button className="modal-close" onClick={() => setActiveModalReport(null)}>×</button>
            </div>

            <form onSubmit={handleSaveUpdate}>
              <div className="form-group">
                <label className="form-label">Update Status</label>
                <select
                  className="form-select"
                  value={updateStatus}
                  onChange={(e) => setUpdateStatus(e.target.value)}
                >
                  <option value="Pending">Pending</option>
                  <option value="Assigned">Assigned</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Resolved">Resolved</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Assign Rescue Squad</label>
                <select
                  className="form-select"
                  value={updateTeam}
                  onChange={(e) => setUpdateTeam(e.target.value)}
                >
                  <option value="">-- No Squad Assigned --</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.name}>{t.name} ({t.specialty})</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Coordinator Notes / Dispatch Log</label>
                <textarea
                  className="form-textarea"
                  value={updateNotes}
                  onChange={(e) => setUpdateNotes(e.target.value)}
                  placeholder="Record coordination instructions or squad dispatch notes..."
                />
              </div>

              <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
                <button type="submit" className="btn-primary" style={{ flex: 1 }}>Save Changes</button>
                <button type="button" className="btn-outline" style={{ flex: 1 }} onClick={() => setActiveModalReport(null)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   6. RESCUE TEAM WORKFLOW VIEW
------------------------------------------------------------- */
function RescueView({ authSession, onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [assignments, setAssignments] = useState([]);
  const [activeRescueReport, setActiveRescueReport] = useState(null);
  const [progressStatus, setProgressStatus] = useState("In Progress");
  const [progressNotes, setProgressNotes] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    try {
      const data = await loginUser(username, password);
      onLoginSuccess(data);
    } catch (err) {
      setLoginError(err.message);
    }
  };

  const loadAssignments = async () => {
    if (!authSession) return;
    try {
      const data = await fetchRescueAssignments(authSession.access_token);
      setAssignments(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadAssignments();
  }, [authSession]);

  const handleOpenRescueModal = (r) => {
    setActiveRescueReport(r);
    setProgressStatus(r.status === "Assigned" ? "In Progress" : r.status);
    setProgressNotes("");
  };

  const handleSaveRescueProgress = async (e) => {
    e.preventDefault();
    if (!progressNotes.trim()) {
      alert("Please enter field notes describing the rescue progress.");
      return;
    }
    try {
      await updateRescueProgress(authSession.access_token, activeRescueReport.report_id, {
        status: progressStatus,
        progress_notes: progressNotes,
      });
      setActiveRescueReport(null);
      loadAssignments();
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  if (!authSession) {
    return (
      <div className="card" style={{ maxWidth: "440px", margin: "40px auto" }}>
        <h2 style={{ color: "#0369a1", marginBottom: "8px" }}>🚤 Rescue Field Team Login</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "20px" }}>
          Log in with your rescue squad account to view dispatches and update emergency status.
        </p>

        {loginError && <div className="alert-box alert-error">❌ {loginError}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Squad Username</label>
            <input
              type="text"
              className="form-input"
              placeholder="Enter squad username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Squad Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Enter squad password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Access Field Dispatch Queue
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h2 style={{ color: "#0369a1" }}>🚤 Rescue Team Operations</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
            Field dispatch queue for active flood evacuations.
          </p>
        </div>
        <button className="btn-outline" onClick={loadAssignments}>🔄 Refresh Dispatches</button>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: "16px", color: "#334155" }}>Active Dispatched Incidents ({assignments.length})</h3>

        {assignments.length === 0 ? (
          <p style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px" }}>
            No pending rescue operations assigned to squads. All clear!
          </p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Location</th>
                  <th>Situation</th>
                  <th>Severity</th>
                  <th>Assigned Squad</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((r) => (
                  <tr key={r.report_id}>
                    <td><strong>{r.report_id}</strong></td>
                    <td>{r.location}</td>
                    <td style={{ maxWidth: "260px" }}>{r.description}</td>
                    <td><span className={`badge sev-${r.severity}`}>{r.severity}</span></td>
                    <td><strong>{r.assigned_team}</strong></td>
                    <td><span className={`badge stat-${r.status.replace(/\s+/g, '')}`}>{r.status}</span></td>
                    <td>
                      <button
                        className="btn-primary"
                        style={{ padding: "4px 10px", fontSize: "0.85rem" }}
                        onClick={() => handleOpenRescueModal(r)}
                      >
                        Update Progress / Resolve
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rescue Progress Modal */}
      {activeRescueReport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Rescue Action: {activeRescueReport.report_id}</h3>
              <button className="modal-close" onClick={() => setActiveRescueReport(null)}>×</button>
            </div>

            <form onSubmit={handleSaveRescueProgress}>
              <div className="form-group">
                <label className="form-label">Operational Status</label>
                <select
                  className="form-select"
                  value={progressStatus}
                  onChange={(e) => setProgressStatus(e.target.value)}
                >
                  <option value="In Progress">In Progress — Team en route / conducting rescue</option>
                  <option value="Resolved">Resolved — Citizens evacuated to safety</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Field Notes & Action Report *</label>
                <textarea
                  className="form-textarea"
                  value={progressNotes}
                  onChange={(e) => setProgressNotes(e.target.value)}
                  placeholder="e.g. Evacuated 4 family members using inflatable dinghy to Sector 4 relief camp."
                  required
                />
              </div>

              <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
                <button type="submit" className="btn-primary" style={{ flex: 1 }}>Submit Field Update</button>
                <button type="button" className="btn-outline" style={{ flex: 1 }} onClick={() => setActiveRescueReport(null)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   7. INCIDENT MAP & LOCATION CLUSTERS VIEW (PROTOTYPE)
------------------------------------------------------------- */
function MapView({ onTrackReport }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedZoneId, setSelectedZoneId] = useState(null);

  const ZONES = [
    { id: "zone-1", name: "Sector 1 & 2 (North Riverbank)", keywords: ["ward 1", "ward 2", "north", "river", "bridge"], risk: "High Risk" },
    { id: "zone-2", name: "Sector 3 (City Center & Market)", keywords: ["ward 3", "market", "central", "main", "downtown"], risk: "Moderate Risk" },
    { id: "zone-3", name: "Sector 4 & 5 (East Lowlands)", keywords: ["ward 4", "ward 5", "east", "lowland", "slum"], risk: "Critical Risk" },
    { id: "zone-4", name: "Sector 6 & 7 (South Drainage Canal)", keywords: ["ward 6", "ward 7", "canal", "south", "drain"], risk: "High Risk" },
    { id: "zone-5", name: "Sector 8 (West Industrial Park)", keywords: ["ward 8", "west", "industrial", "highway", "factory"], risk: "Low Risk" },
    { id: "zone-6", name: "Peripheral & Other Areas", keywords: [], risk: "Monitoring" },
  ];

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await fetchPublicReports();
      setReports(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const getReportZone = (location) => {
    const locLower = (location || "").toLowerCase();
    for (const z of ZONES.slice(0, 5)) {
      if (z.keywords.some((kw) => locLower.includes(kw))) {
        return z.id;
      }
    }
    return "zone-6";
  };

  const getZoneReports = (zoneId) => {
    return reports.filter((r) => getReportZone(r.location) === zoneId);
  };

  const activeReports = selectedZoneId ? getZoneReports(selectedZoneId) : reports;

  return (
    <div>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h2 style={{ color: "#0369a1" }}>🗺️ Location-Based Incident Map</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
              Incident clustering across municipal flood risk sectors.
            </p>
          </div>
          <button className="btn-outline" onClick={loadReports}>🔄 Refresh Map</button>
        </div>

        {/* Prototype Disclaimer */}
        <div className="alert-box alert-info" style={{ marginBottom: "16px", fontSize: "0.85rem" }}>
          📍 <strong>Prototype Location Visualizer:</strong> Incidents are dynamically aggregated into municipal sectors based on citizen-reported landmark and ward strings. As a student prototype, this view does not claim GPS hardware tracking or satellite-based live dispatch.
        </div>

        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>Loading spatial incident data...</p>
        ) : (
          <div>
            {/* Visual Sector Map Grid */}
            <div className="map-canvas-container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#0369a1" }}>
                  MUNICIPAL SECTOR MAP (CLICK A SECTOR TO FILTER INCIDENTS)
                </span>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  Total Mapped: {reports.length} Incidents
                </span>
              </div>

              <div className="map-zones-grid">
                {ZONES.map((zone) => {
                  const zoneIncidents = getZoneReports(zone.id);
                  const isSelected = selectedZoneId === zone.id;
                  const criticalCount = zoneIncidents.filter((r) => r.severity === "Critical").length;

                  return (
                    <div
                      key={zone.id}
                      className={`zone-box ${isSelected ? "selected" : ""}`}
                      onClick={() => setSelectedZoneId(isSelected ? null : zone.id)}
                    >
                      <div className="zone-header">
                        <span className="zone-name">{zone.name}</span>
                        <span className={`zone-count-badge ${zoneIncidents.length === 0 ? "empty" : ""}`}>
                          {zoneIncidents.length} {zoneIncidents.length === 1 ? "Incident" : "Incidents"}
                        </span>
                      </div>
                      <div className="zone-details">
                        Risk Level: <strong>{zone.risk}</strong>
                        {criticalCount > 0 && (
                          <div style={{ color: "#dc2626", fontWeight: "700", marginTop: "4px" }}>
                            🚨 {criticalCount} Critical
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Filtered Incidents List */}
            <div style={{ marginTop: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <h3 style={{ color: "#334155" }}>
                  {selectedZoneId
                    ? `Incidents in ${ZONES.find((z) => z.id === selectedZoneId)?.name} (${activeReports.length})`
                    : `All Reported Incidents (${activeReports.length})`}
                </h3>
                {selectedZoneId && (
                  <button className="btn-outline" style={{ fontSize: "0.85rem", padding: "4px 10px" }} onClick={() => setSelectedZoneId(null)}>
                    Show All Sectors
                  </button>
                )}
              </div>

              {activeReports.length === 0 ? (
                <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "30px" }}>
                  No active incidents recorded for this sector.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Tracking ID</th>
                        <th>Citizen / Location</th>
                        <th>Situation</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Assigned Squad</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeReports.map((r) => (
                        <tr key={r.report_id}>
                          <td><strong>{r.report_id}</strong></td>
                          <td>
                            <div>{r.citizen_name}</div>
                            <small style={{ color: "var(--text-muted)" }}>{r.location}</small>
                          </td>
                          <td style={{ maxWidth: "260px" }}>{r.description}</td>
                          <td><span className={`badge sev-${r.severity}`}>{r.severity}</span></td>
                          <td><span className={`badge stat-${r.status.replace(/\s+/g, '')}`}>{r.status}</span></td>
                          <td>{r.assigned_team || "Awaiting Assignment"}</td>
                          <td>
                            <button
                              className="btn-outline"
                              style={{ padding: "4px 8px", fontSize: "0.8rem" }}
                              onClick={() => onTrackReport(r.report_id)}
                            >
                              Track
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

