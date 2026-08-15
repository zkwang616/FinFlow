import { useEffect, useMemo, useState } from "react";
import DagCanvas from "../components/DagCanvas.jsx";
import EventLog from "../components/EventLog.jsx";
import NodeDetails from "../components/NodeDetails.jsx";
import { wsUrl } from "../api.js";

export default function Dashboard({ jobId, onBack, onReport }) {
  const [nodeStates, setNodeStates] = useState({});
  const [events, setEvents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [done, setDone] = useState(false);
  const [reportPath, setReportPath] = useState(null);
  const [connState, setConnState] = useState("connecting");
  const [failedError, setFailedError] = useState(null);

  useEffect(() => {
    let ws;
    let closed = false;

    function connect() {
      setConnState("connecting");
      ws = new WebSocket(wsUrl(jobId));

      ws.onopen = () => setConnState("connected");
      ws.onmessage = (msg) => {
        const event = JSON.parse(msg.data);
        setEvents((prev) => [...prev, event]);
        const p = event.payload ?? {};
        if (event.type.startsWith("node_")) {
          const key = p.node_name;
          setNodeStates((prev) => {
            const base = prev[key] ?? { status: "running" };
            let next = { ...base };
            if (event.type === "node_started") next = { ...base, status: "running" };
            if (event.type === "node_prepared") next = { ...next, prepSummary: p.prep_summary };
            if (event.type === "node_output") next = { ...next, outputSummary: p.output_summary, elapsed: Math.round(p.elapsed_ms ?? 0) };
            if (event.type === "node_finished") next = { ...next, status: "success", action: p.action, elapsed: Math.round(p.elapsed_ms ?? 0) };
            if (event.type === "node_failed") next = { ...next, status: "error", error: p.error };
            return { ...prev, [key]: next };
          });
        }
        if (event.type === "job_finished") {
          setDone(true);
          setReportPath(p.report_path);
        }
        if (event.type === "job_failed") {
          setDone(true);
          setFailedError(p.error ?? "unknown error");
        }
      };
      ws.onclose = () => {
        setConnState("closed");
        if (!closed && !doneRef.current) setTimeout(connect, 1000);
      };
    }

    const doneRef = { current: false };
    const origSetDone = setDone;
    connect();
    return () => {
      closed = true;
      doneRef.current = true;
      ws?.close();
    };
  }, [jobId]);

  const statusText = useMemo(() => {
    if (done) return "已完成";
    if (connState === "connected") return "运行中";
    if (connState === "connecting") return "连接中";
    return "已断开（重连中）";
  }, [done, connState]);

  return (
    <div className="dashboard">
      <header className="topbar">
        <button onClick={onBack}>← 新建任务</button>
        <span className="job-title">任务 {jobId}</span>
        <span className={`badge badge-${connState}`}>{statusText}</span>
        {failedError && <span className="error">任务失败：{failedError}</span>}
        {done && reportPath && <button onClick={onReport}>查看报告 →</button>}
      </header>
      <main className="workspace">
        <section className="panel-left">
          <DagCanvas nodeStates={nodeStates} selected={selected} onSelect={setSelected} />
        </section>
        <aside className="panel-right">
          <h3>事件日志</h3>
          <EventLog events={events} />
          <h3>节点详情</h3>
          <NodeDetails nodeStates={nodeStates} selected={selected} />
        </aside>
      </main>
    </div>
  );
}
