import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const submitQuery = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResponse(null);

    try {
      const res = await axios.post("/api/v1/pipeline", {
        query: query,
      });
      console.log(res.data);
      setResponse(res.data);
    } catch (err) {
      setResponse({ error: "Request failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Query Form</h1>

      <form onSubmit={submitQuery}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type your query"
          style={{ width: "300px", padding: "0.5rem" }}
        />
        <br />
        <br />
        <button type="submit" disabled={loading}>
          {loading ? "Sending..." : "Send"}
        </button>
      </form>

      {response && (
        <pre style={{ marginTop: "2rem" }}>
          {/* {JSON.stringify(response, null, 2)} */}
        </pre>
      )}
    </div>
  );
}

export default App;
