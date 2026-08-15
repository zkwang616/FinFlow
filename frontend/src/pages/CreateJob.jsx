import { useState } from "react";
import { createJob } from "../api.js";

export default function CreateJob({ onSubmit }) {
  const [ticker, setTicker] = useState("AAPL");
  const [mode, setMode] = useState("mock");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { job_id } = await createJob(ticker.trim().toUpperCase(), mode);
      onSubmit(job_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="create-page">
      <h1>FinFlow</h1>
      <p className="subtitle">可观测的 LLM 金融分析流水线</p>
      <form onSubmit={handleSubmit} className="create-form">
        <label>
          股票代码（Ticker）
          <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="AAPL" />
        </label>
        <label>
          数据模式
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="mock">mock（内置示例数据）</option>
            <option value="real">real（真实数据源，V2）</option>
          </select>
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "提交中…" : "生成分析报告"}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
