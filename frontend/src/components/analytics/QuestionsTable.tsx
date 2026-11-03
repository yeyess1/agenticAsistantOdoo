import { Card, TableWrap, td, th } from "./Card";
import { AGENT_LABEL, CATEGORY_LABEL, pct, score, secs } from "./format";
import type { QuestionRow, QuestionRun } from "./types";

function quality(r?: QuestionRun): string {
  if (!r || r.error) return "error";
  if (r.correctness_f1 !== undefined && r.correctness_f1 !== null) return score(r.correctness_f1);
  if (r.behaviour_passed !== undefined && r.behaviour_passed !== null) return r.behaviour_passed ? "cumple" : "no cumple";
  return "—";
}

export default function QuestionsTable({ rows }: { rows: QuestionRow[] }) {
  return (
    <Card title="Detalle por pregunta" subtitle="Calidad = F1 de corrección (preguntas con documentación) o veredicto de comportamiento (no cubiertas / fuera de alcance).">
      <TableWrap label="Resultados por pregunta">
        <thead>
          <tr>
            <th className={th} scope="col">Id</th>
            <th className={th} scope="col">Categoría</th>
            <th className={th} scope="col">Esperado</th>
            <th className={th} scope="col">Respondió (agéntico)</th>
            <th className={th} scope="col">Calidad agéntico</th>
            <th className={th} scope="col">Calidad lineal</th>
            <th className={th} scope="col">Latencia ag. / lin.</th>
            <th className={th} scope="col">Recall@10 ES / EN</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((q) => {
            const a = q.runs.agentic;
            const l = q.runs.linear;
            const wrong = a?.answered_by && a.answered_by !== q.expected_agent;
            return (
              <tr key={q.id}>
                <th scope="row" className={`${td} font-mono text-xs`} title={q.question}>{q.id}</th>
                <td className={td}>{CATEGORY_LABEL[q.category]}</td>
                <td className={td}>{AGENT_LABEL[q.expected_agent]}</td>
                <td className={`${td} ${wrong ? "text-danger font-medium" : ""}`}>
                  {a?.answered_by ? AGENT_LABEL[a.answered_by] : "—"}
                  {a?.delegated ? " (delegada)" : ""}
                  {a?.n_rewrites ? ` · ${a.n_rewrites} reescr.` : ""}
                </td>
                <td className={td}>{quality(a)}</td>
                <td className={td}>{quality(l)}</td>
                <td className={td}>{secs(a?.latency_ms)} / {secs(l?.latency_ms)}</td>
                <td className={td}>
                  {q.retrieval ? `${pct(q.retrieval.es["recall@10"])} / ${pct(q.retrieval.en["recall@10"])}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </TableWrap>
    </Card>
  );
}
