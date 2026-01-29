import { useState, useEffect, useRef } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [leads, setLeads] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const pollingInterval = useRef(null);

  // 1. Fetch function (Logic used by both initial load and polling)
  const fetchLeads = async () => {
    try {
      const res = await axios.get("/api/v1/leads");
      setLeads(res.data.leads || []);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  // 2. Initial Load: Get what's already there when the app starts
  useEffect(() => {
    fetchLeads();
  }, []);

  // 3. Start Pipeline & Begin Polling
  const startPipeline = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    
    try {
      await axios.post("/api/v1/leads/pipeline", { query });
      
      // Clear any existing interval before starting a new one
      if (pollingInterval.current) clearInterval(pollingInterval.current);

      // Start polling every 5 seconds to catch new leads
      pollingInterval.current = setInterval(() => {
        fetchLeads();
      }, 5000);

    } catch (err) {
      alert("Failed to start pipeline");
      setIsProcessing(false);
    }
  };

  // 4. Cleanup: Stop polling when the user leaves the page
  useEffect(() => {
    return () => {
      if (pollingInterval.current) clearInterval(pollingInterval.current);
    };
  }, []);

  const stopPolling = () => {
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
      pollingInterval.current = null;
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Lead Pipeline</h1>
      
      <form onSubmit={startPipeline}>
        <input 
          value={query} 
          onChange={(e) => setQuery(e.target.value)} 
          placeholder="Search query..."
        />
        <button type="submit" disabled={isProcessing}>
          {isProcessing ? "Pipeline Running..." : "Start Pipeline"}
        </button>
        
        {isProcessing && (
          <button onClick={stopPolling} style={{ marginLeft: "10px", background: "red", color: "white" }}>
            Stop Watching
          </button>
        )}
      </form>

      {/*  */}
      
      <table style={{ width: "100%", marginTop: "20px", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid black" }}>
            <th>Name</th>
            <th>Website</th>
            <th>Qualified?</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.prospect_id} style={{ borderBottom: "1px solid #ccc" }}>
              <td>{lead.name}</td>
              <td>{lead.websites}</td>
              <td>{lead.is_qualified ? "✅" : "⏳"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;