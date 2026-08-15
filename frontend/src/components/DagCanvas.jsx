import { useMemo } from "react";
import { ReactFlow, Background, Controls, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const NODE_LAYOUT = [
  { id: "InputNode", label: "输入校验", y: 20 },
  { id: "MockDataNode", label: "数据获取", y: 140 },
  { id: "DataProcessorNode", label: "数据处理", y: 260 },
  { id: "TextAgentBatchNode", label: "LLM 分析 ×4", y: 380 },
  { id: "HtmlReportNode", label: "报告生成", y: 500 },
  { id: "DoneNode", label: "完成", y: 620 },
];

const STATUS_COLOR = {
  idle: "#94a3b8",
  running: "#2563eb",
  success: "#16a34a",
  error: "#dc2626",
  warning: "#d97706",
};

export default function DagCanvas({ nodeStates }) {
  const nodes = useMemo(
    () =>
      NODE_LAYOUT.map(({ id, label, y }) => {
        const state = nodeStates[id];
        const status = state?.status ?? "idle";
        const color = STATUS_COLOR[status];
        return {
          id,
          position: { x: 260, y },
          data: { label: `${label}${state?.elapsed ? ` (${state.elapsed}ms)` : ""}` },
          style: {
            border: `2px solid ${color}`,
            borderRadius: 10,
            background: state?.status === "running" ? "#eff6ff" : "#ffffff",
            color: "#1e293b",
            padding: "10px 16px",
          },
        };
      }),
    [nodeStates]
  );

  const edges = useMemo(
    () =>
      NODE_LAYOUT.slice(0, -1).map(({ id }, i) => ({
        id: `e-${id}`,
        source: id,
        target: NODE_LAYOUT[i + 1].id,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "#94a3b8" },
      })),
    []
  );

  return (
    <div className="dag-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
