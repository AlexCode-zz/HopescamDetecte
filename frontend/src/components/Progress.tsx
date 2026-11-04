import { CheckCircle, Clock, Upload } from "lucide-react";

const STEPS = [
  { number: 1, label: "Paciente", icon: <CheckCircle size={16} strokeWidth={2} /> },
  { number: 2, label: "Imagen", icon: <Upload size={16} strokeWidth={2} /> },
  { number: 3, label: "Resultado", icon: <Clock size={16} strokeWidth={2} /> },
];

interface ProgressProps {
  step: number;
}

export default function Progress({ step }: ProgressProps) {
  return (
    <div className="flex w-full items-center gap-2 mb-2">
      {STEPS.map((s, i) => {
        const isDone = i + 1 < step;
        const isActive = i + 1 === step;
        const isLast = i === STEPS.length - 1;
        return (
          <React.Fragment key={s.number}>
            <div className="flex items-center gap-2.5">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border transition-colors ${
                  isDone
                    ? "bg-success text-white border-success"
                    : isActive
                    ? "bg-primary text-white border-primary"
                    : "bg-surface text-muted border-border"
                }`}
              >
                {isDone ? <CheckCircle size={12} strokeWidth={2.5} /> : s.number}
              </div>
              <span
                className={`text-xs font-medium transition-colors ${
                  isDone ? "text-success" : isActive ? "text-primary" : "text-muted"
                }`}
              >
                {s.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={`h-px flex-1 ${
                  isDone ? "bg-success/40" : isActive ? "bg-primary/40" : "bg-border"
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
