import { Card, TableWrap, td, th } from "./Card";
import { AGENT_LABEL, pct } from "./format";
import type { RoutingReport } from "./types";

export default function RoutingMatrix({ routing, routerAccuracy }: { routing: RoutingReport; routerAccuracy: number | null }) {
  const cols = [...routing.labels, "none"] as const;
  return (
    <Card
      title={`Agente final correcto: ${routing.correct}/${routing.n} (${pct(routing.accuracy)})`}
      subtitle={`Decisión inicial del router: ${pct(routerAccuracy)}. Filas = agente esperado, columnas = agente que respondió.`}
    >
      <TableWrap label="Matriz de confusión del supervisor">
        <thead>
          <tr>
            <th className={th} scope="col">Esperado \ Obtenido</th>
            {cols.map((c) => (
              <th key={c} className={th} scope="col">{c === "none" ? "Ninguno" : AGENT_LABEL[c]}</th>
            ))}
            <th className={th} scope="col">Precision</th>
            <th className={th} scope="col">Recall</th>
          </tr>
        </thead>
        <tbody>
          {routing.labels.map((e) => (
            <tr key={e}>
              <th scope="row" className={`${td} font-medium`}>{AGENT_LABEL[e]}</th>
              {cols.map((c) => {
                const v = routing.confusion[e][c];
                const diag = c === e;
                return (
                  <td key={c} className={`${td} ${diag ? "bg-primary-soft font-semibold text-primary-strong" : v > 0 ? "bg-danger-soft text-danger" : "text-ink-muted"}`}>
                    {v}
                  </td>
                );
              })}
              <td className={td}>{pct(routing.per_class[e].precision)}</td>
              <td className={td}>{pct(routing.per_class[e].recall)}</td>
            </tr>
          ))}
        </tbody>
      </TableWrap>
    </Card>
  );
}
