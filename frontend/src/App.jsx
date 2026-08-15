import { useState } from "react";
import CreateJob from "./pages/CreateJob.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Report from "./pages/Report.jsx";

export default function App() {
  const [jobId, setJobId] = useState(null);
  const [page, setPage] = useState("create");

  if (page === "report") {
    return <Report jobId={jobId} onBack={() => setPage("dashboard")} />;
  }
  if (page === "dashboard") {
    return (
      <Dashboard
        jobId={jobId}
        onBack={() => setPage("create")}
        onReport={() => setPage("report")}
      />
    );
  }
  return <CreateJob onSubmit={(id) => { setJobId(id); setPage("dashboard"); }} />;
}
