export default function NodeDetails({ nodeStates, selected }) {
  if (!selected) return <div className="node-details empty">点击左侧节点查看详情</div>;
  const state = nodeStates[selected];
  if (!state) return <div className="node-details empty">暂无该节点数据</div>;

  return (
    <div className="node-details">
      <h3>{selected}</h3>
      <p>
        状态：<b>{state.status}</b>
        {state.action ? ` · action: ${state.action}` : ""}
        {state.elapsed ? ` · ${state.elapsed}ms` : ""}
      </p>
      {state.error && <p className="error">错误：{state.error}</p>}
      {state.prepSummary !== undefined && (
        <details open>
          <summary>输入摘要</summary>
          <pre>{JSON.stringify(state.prepSummary, null, 2).slice(0, 2000)}</pre>
        </details>
      )}
      {state.outputSummary !== undefined && (
        <details open>
          <summary>输出摘要</summary>
          <pre>{JSON.stringify(state.outputSummary, null, 2).slice(0, 4000)}</pre>
        </details>
      )}
    </div>
  );
}
