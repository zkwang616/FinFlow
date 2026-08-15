import { useEffect, useRef } from "react";

const TYPE_LABEL = {
  job_created: "任务创建",
  job_started: "任务开始",
  job_finished: "任务完成",
  job_failed: "任务失败",
  flow_started: "流水线开始",
  flow_finished: "流水线完成",
  flow_failed: "流水线失败",
  node_started: "节点开始",
  node_prepared: "节点就绪",
  node_output: "节点输出",
  node_finished: "节点完成",
  node_failed: "节点失败",
};

export default function EventLog({ events }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [events.length]);

  return (
    <div className="event-log" ref={ref}>
      {events.length === 0 && <div className="empty">等待事件流…</div>}
      {events.map((e, i) => (
        <div key={i} className={`event event-${e.type}`}>
          <span className="event-time">{e.ts.slice(11, 19)}</span>
          <span className="event-node">{e.payload?.node_name ?? ""}</span>
          <span className="event-type">{TYPE_LABEL[e.type] ?? e.type}</span>
        </div>
      ))}
    </div>
  );
}
