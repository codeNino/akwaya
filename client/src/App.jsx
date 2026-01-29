import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API = "/api/v1";

const SECTIONS = {
  overview: "Overview",
  pipeline: "Lead search",
  prospects: "Prospects (callable)",
  leads: "Qualified leads",
  campaign: "Cold call campaign",
};

function App() {
  const [section, setSection] = useState("overview");
  const [prospects, setProspects] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState({ prospects: false, leads: false });
  const [message, setMessage] = useState(null);
  const [query, setQuery] = useState("");
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [campaignLimit, setCampaignLimit] = useState("");
  const [campaignRunning, setCampaignRunning] = useState(false);
  const [callingId, setCallingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [selectedProspectIds, setSelectedProspectIds] = useState([]);
  const [selectedLeadIds, setSelectedLeadIds] = useState([]);
  const [bulkActionRunning, setBulkActionRunning] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const pollingRef = useRef(null);

  const showMessage = (text, type = "info") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const fetchProspects = async () => {
    setLoading((l) => ({ ...l, prospects: true }));
    try {
      const res = await axios.get(`${API}/prospects`);
      setProspects(res.data.prospects || []);
    } catch (err) {
      console.error(err);
      showMessage("Failed to load prospects", "error");
      setProspects([]);
    } finally {
      setLoading((l) => ({ ...l, prospects: false }));
    }
  };

  const fetchLeads = async () => {
    setLoading((l) => ({ ...l, leads: true }));
    try {
      const res = await axios.get(`${API}/leads`);
      setLeads(res.data.leads || []);
    } catch (err) {
      console.error(err);
      showMessage("Failed to load leads", "error");
      setLeads([]);
    } finally {
      setLoading((l) => ({ ...l, leads: false }));
    }
  };

  useEffect(() => {
    if (section === "prospects") fetchProspects();
    if (section === "leads") fetchLeads();
  }, [section]);

  useEffect(() => {
    fetchProspects();
    fetchLeads();
  }, []);

  const startPipeline = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      showMessage("Enter a search query", "error");
      return;
    }
    setPipelineRunning(true);
    setMessage(null);
    try {
      await axios.post(`${API}/leads/pipeline`, { query: query.trim() });
      showMessage("Pipeline started. New leads will appear as they are processed.", "success");
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(() => {
        fetchLeads();
        fetchProspects();
      }, 5000);
      setIsPolling(true);
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to start pipeline", "error");
    } finally {
      setPipelineRunning(false);
    }
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setIsPolling(false);
  };

  useEffect(() => () => stopPolling(), []);

  const makeCall = async (prospectId) => {
    setCallingId(prospectId);
    try {
      await axios.post(`${API}/call`, { prospect_id: prospectId });
      showMessage("Call triggered successfully.", "success");
      fetchProspects();
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to trigger call", "error");
    } finally {
      setCallingId(null);
    }
  };

  const deleteProspect = async (prospectId) => {
    if (!window.confirm("Delete this prospect? This cannot be undone.")) return;
    setDeletingId(prospectId);
    try {
      const res = await axios.delete(`${API}/prospects/${encodeURIComponent(prospectId)}`);
      showMessage(res.data?.message || "Prospect deleted.", "success");
      setSelectedProspectIds((prev) => prev.filter((id) => id !== prospectId));
      setSelectedLeadIds((prev) => prev.filter((id) => id !== prospectId));
      fetchProspects();
      fetchLeads();
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to delete prospect", "error");
    } finally {
      setDeletingId(null);
    }
  };

  const toggleProspectSelection = (id) => {
    setSelectedProspectIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleLeadSelection = (id) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectAllProspects = (checked) => {
    setSelectedProspectIds(checked ? prospects.map((p) => p.prospect_id) : []);
  };

  const selectAllLeads = (checked) => {
    setSelectedLeadIds(checked ? leads.map((p) => p.prospect_id) : []);
  };

  const callSelected = async (ids) => {
    if (!ids || !ids.length) {
      showMessage("Select one or more prospects first.", "error");
      return;
    }
    setBulkActionRunning(true);
    try {
      for (const id of ids) {
        await axios.post(`${API}/call`, { prospect_id: id });
      }
      showMessage(`Call triggered for ${ids.length} prospect(s).`, "success");
      setSelectedProspectIds([]);
      setSelectedLeadIds([]);
      fetchProspects();
      fetchLeads();
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to trigger call(s)", "error");
    } finally {
      setBulkActionRunning(false);
    }
  };

  const deleteSelected = async (ids) => {
    if (!ids || !ids.length) {
      showMessage("Select one or more prospects first.", "error");
      return;
    }
    if (!window.confirm(`Delete ${ids.length} selected prospect(s)? This cannot be undone.`)) return;
    setBulkActionRunning(true);
    try {
      for (const id of ids) {
        await axios.delete(`${API}/prospects/${encodeURIComponent(id)}`);
      }
      showMessage(`${ids.length} prospect(s) deleted.`, "success");
      setSelectedProspectIds([]);
      setSelectedLeadIds([]);
      fetchProspects();
      fetchLeads();
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to delete prospect(s)", "error");
    } finally {
      setBulkActionRunning(false);
    }
  };

  const startCampaign = async (e) => {
    e.preventDefault();
    setCampaignRunning(true);
    setMessage(null);
    try {
      const body = campaignLimit.trim() ? { limit: parseInt(campaignLimit, 10) } : {};
      await axios.post(`${API}/cold_call/campaign`, body);
      showMessage("Cold call campaign started. Calls will be placed in the background.", "success");
      setTimeout(fetchProspects, 2000);
    } catch (err) {
      showMessage(err.response?.data?.message || "Failed to start campaign", "error");
    } finally {
      setCampaignRunning(false);
    }
  };

  const formatDate = (d) => {
    if (!d) return "—";
    const s = typeof d === "string" ? d : d?.toISO?.() ?? "";
    return s ? new Date(s).toLocaleString() : "—";
  };

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-title">Lead qualification</div>
        <nav className="sidebar-nav">
          {Object.entries(SECTIONS).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={section === key ? "active" : ""}
              onClick={() => setSection(key)}
            >
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        {message && (
          <div className={`alert alert-${message.type === "error" ? "error" : message.type === "success" ? "success" : "info"}`}>
            {message.text}
          </div>
        )}

        {section === "overview" && (
          <>
            <div className="page-header">
              <h1>Overview</h1>
              <p>Summary of prospects and qualified leads.</p>
            </div>
            <div className="stats-row">
              <div className="stat-card">
                <div className="value">{prospects.length}</div>
                <div className="label">Prospects (callable, not yet called)</div>
              </div>
              <div className="stat-card">
                <div className="value">{leads.length}</div>
                <div className="label">Qualified leads</div>
              </div>
            </div>
            <div className="card">
              <div className="card-title">Quick actions</div>
              <div className="form-row" style={{ gap: "1rem", flexWrap: "wrap" }}>
                <button type="button" className="btn btn-primary" onClick={() => setSection("pipeline")}>
                  Start lead search
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setSection("prospects")}>
                  View prospects
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setSection("leads")}>
                  View qualified leads
                </button>
                <button type="button" className="btn btn-success" onClick={() => setSection("campaign")}>
                  Run cold call campaign
                </button>
              </div>
            </div>
          </>
        )}

        {section === "pipeline" && (
          <>
            <div className="page-header">
              <h1>Lead search</h1>
              <p>Run the acquisition pipeline with a search query to source and enrich leads.</p>
            </div>
            <div className="card">
              <form onSubmit={startPipeline} className="form-row">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. forex bureaus Lagos"
                  disabled={pipelineRunning}
                />
                <button type="submit" className="btn btn-primary" disabled={pipelineRunning}>
                  {pipelineRunning ? "Running…" : "Start pipeline"}
                </button>
                {isPolling && (
                  <button type="button" className="btn btn-danger btn-sm" onClick={stopPolling}>
                    Stop watching
                  </button>
                )}
              </form>
            </div>
          </>
        )}

        {section === "prospects" && (
          <>
            <div className="page-header">
              <h1>Prospects (callable)</h1>
              <p>Leads with phone numbers that have not been called yet.</p>
            </div>
            <div className="card">
              <div className="form-row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchProspects} disabled={loading.prospects}>
                  {loading.prospects ? "Loading…" : "Refresh"}
                </button>
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={() => callSelected(selectedProspectIds)}
                  disabled={!selectedProspectIds.length || bulkActionRunning}
                >
                  {bulkActionRunning ? "Calling…" : `Call selected (${selectedProspectIds.length})`}
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => deleteSelected(selectedProspectIds)}
                  disabled={!selectedProspectIds.length || bulkActionRunning}
                >
                  {bulkActionRunning ? "Deleting…" : `Delete selected (${selectedProspectIds.length})`}
                </button>
              </div>
              <div className="table-wrap">
                {loading.prospects && prospects.length === 0 ? (
                  <div className="empty-state">Loading prospects…</div>
                ) : prospects.length === 0 ? (
                  <div className="empty-state">No callable prospects. Run the pipeline or check the database.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th style={{ width: "2.5rem" }}>
                          <input
                            type="checkbox"
                            checked={prospects.length > 0 && selectedProspectIds.length === prospects.length}
                            onChange={(e) => selectAllProspects(e.target.checked)}
                            title="Select all"
                          />
                        </th>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Email</th>
                        <th>Country</th>
                        <th>Business</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prospects.map((p) => (
                        <tr key={p.prospect_id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selectedProspectIds.includes(p.prospect_id)}
                              onChange={() => toggleProspectSelection(p.prospect_id)}
                            />
                          </td>
                          <td>{p.name || "—"}</td>
                          <td>{p.phones || "—"}</td>
                          <td>{p.emails || "—"}</td>
                          <td>{p.country_acronym || p.country || "—"}</td>
                          <td>{p.business_context || "—"}</td>
                          <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                            <button
                              type="button"
                              className="btn btn-success btn-sm"
                              onClick={() => makeCall(p.prospect_id)}
                              disabled={callingId === p.prospect_id}
                            >
                              {callingId === p.prospect_id ? "Calling…" : "Call"}
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => deleteProspect(p.prospect_id)}
                              disabled={deletingId === p.prospect_id}
                            >
                              {deletingId === p.prospect_id ? "Deleting…" : "Delete"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        )}

        {section === "leads" && (
          <>
            <div className="page-header">
              <h1>Qualified leads</h1>
              <p>Leads marked as qualified after verification calls.</p>
            </div>
            <div className="card">
              <div className="form-row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchLeads} disabled={loading.leads}>
                  {loading.leads ? "Loading…" : "Refresh"}
                </button>
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={() => callSelected(selectedLeadIds)}
                  disabled={!selectedLeadIds.length || bulkActionRunning}
                >
                  {bulkActionRunning ? "Calling…" : `Call selected (${selectedLeadIds.length})`}
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => deleteSelected(selectedLeadIds)}
                  disabled={!selectedLeadIds.length || bulkActionRunning}
                >
                  {bulkActionRunning ? "Deleting…" : `Delete selected (${selectedLeadIds.length})`}
                </button>
              </div>
              <div className="table-wrap">
                {loading.leads && leads.length === 0 ? (
                  <div className="empty-state">Loading leads…</div>
                ) : leads.length === 0 ? (
                  <div className="empty-state">No qualified leads yet.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th style={{ width: "2.5rem" }}>
                          <input
                            type="checkbox"
                            checked={leads.length > 0 && selectedLeadIds.length === leads.length}
                            onChange={(e) => selectAllLeads(e.target.checked)}
                            title="Select all"
                          />
                        </th>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Email</th>
                        <th>Country</th>
                        <th>Qualified</th>
                        <th>Relevant industry</th>
                        <th>Called at</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((p) => (
                        <tr key={p.prospect_id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selectedLeadIds.includes(p.prospect_id)}
                              onChange={() => toggleLeadSelection(p.prospect_id)}
                            />
                          </td>
                          <td>{p.name || "—"}</td>
                          <td>{p.phones || "—"}</td>
                          <td>{p.emails || "—"}</td>
                          <td>{p.country_acronym || p.country || "—"}</td>
                          <td>
                            <span className={`badge ${p.is_qualified ? "badge-success" : "badge-muted"}`}>
                              {p.is_qualified ? "Yes" : "No"}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${p.is_relevant_industry ? "badge-success" : "badge-muted"}`}>
                              {p.is_relevant_industry ? "Yes" : "No"}
                            </span>
                          </td>
                          <td>{formatDate(p.updated_at)}</td>
                          <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                            <button
                              type="button"
                              className="btn btn-success btn-sm"
                              onClick={() => makeCall(p.prospect_id)}
                              disabled={callingId === p.prospect_id}
                            >
                              {callingId === p.prospect_id ? "Calling…" : "Call"}
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => deleteProspect(p.prospect_id)}
                              disabled={deletingId === p.prospect_id}
                            >
                              {deletingId === p.prospect_id ? "Deleting…" : "Delete"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        )}

        {section === "campaign" && (
          <>
            <div className="page-header">
              <h1>Cold call campaign</h1>
              <p>Trigger Retell calls for all prospects that have a phone and have not been called yet.</p>
            </div>
            <div className="card">
              <form onSubmit={startCampaign} className="form-row">
                <label htmlFor="campaign-limit" style={{ fontSize: "0.9375rem", color: "var(--text-muted)" }}>
                  Limit (optional):
                </label>
                <input
                  id="campaign-limit"
                  type="number"
                  min="1"
                  placeholder="No limit"
                  value={campaignLimit}
                  onChange={(e) => setCampaignLimit(e.target.value)}
                  className="campaign-limit"
                  disabled={campaignRunning}
                />
                <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Leave empty to call all uncalled prospects.</span>
                <button type="submit" className="btn btn-success" disabled={campaignRunning}>
                  {campaignRunning ? "Starting…" : "Start campaign"}
                </button>
              </form>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
