export default function Report({ jobId, onBack }) {
  return (
    <div className="report-page">
      <header className="topbar">
        <button onClick={onBack}>← 返回看板</button>
        <span className="job-title">报告 · 任务 {jobId}</span>
      </header>
      <iframe
        title="report"
        src={`/api/jobs/${jobId}/report`}
        className="report-frame"
      />
    </div>
  );
}
