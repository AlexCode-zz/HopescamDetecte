import { Download, HelpCircle, History, RefreshCw, UserPlus } from "lucide-react";
import { CLASS_STYLES, STATUS_VARIANT, DISCLAIMER, reasonText } from "@/lib/constants";
import type { AnalysisResult } from "@/types";

interface AnalysisResultProps {
  result: AnalysisResult;
  onNewImage: () => void;
  onNewPatient: () => void;
  onDownloadReport: (url: string) => void;
}

export default function AnalysisResult({
  result,
  onNewImage,
  onNewPatient,
  onDownloadReport,
}: AnalysisResultProps) {
  const status = result.status;
  const variant = STATUS_VARIANT[status] ?? "neutral";
  const showClass = result.can_show_class && result.result;
  const style = showClass ? CLASS_STYLES[result.result!] : null;

  return (
    <section className="space-y-6" data-entrance>
      {/* Estado del análisis */}
      <div
        className={`panel p-6 rounded-lg border ${
          variant === "success"
            ? "border-success/30 bg-success/5"
            : variant === "danger"
            ? "border-danger/30 bg-danger/5"
            : variant === "attention"
            ? "border-attention/30 bg-attention/5"
            : "border-muted/30 bg-muted/5"
        }`}
      >
        <div className="flex items-start gap-3 mb-3">
          <div
            className={`rounded-lg p-2 ${
              variant === "success"
                ? "bg-success/10 text-success"
                : variant === "danger"
                ? "bg-danger/10 text-danger"
                : variant === "attention"
                ? "bg-attention/10 text-attention"
                : "bg-muted/10 text-muted"
            }`}
          >
            {variant === "success" ? (
              <HelpCircle size={20} strokeWidth={2} />
            ) : variant === "danger" ? (
              <HelpCircle size={20} strokeWidth={2} />
            ) : (
              <HelpCircle size={20} strokeWidth={2} />
            )}
          </div>
          <div>
            <h3
              className={`font-serif h2 text-ink ${
                variant === "success" ? "text-success" : variant === "danger" ? "text-danger" : "text-attention"
              }`}
            >
              {status === "valida_confiable"
                ? "Análisis completado — resultado confiable"
                : status === "valida_no_concluyente"
                ? "Análisis no concluyente"
                : "Imagen no válida"}
            </h3>
            <p className="text-small text-muted mt-1">
              {status === "valida_confiable"
                ? "El estado del análisis es válido y confiable. Se muestra la clase, la confianza calibrada y el Grad-CAM."
                : status === "valida_no_concluyente"
                ? "El modelo no tiene certeza suficiente. No se fuerza un resultado. Consulta a un especialista y, si es posible, repite la ecografía."
                : "Esta imagen no parece una ecografía mamaria. No se generó ninguna clase ni ningún porcentaje."}
            </p>
          </div>
        </div>

        {/* Resultado confiable */}
        {showClass && style && (
          <div className="mt-5 pt-5 border-t border-border">
            <div className="inline-flex items-center gap-2 mb-3">
              <span
                className={`result-chip ${
                  style.variant === "success" ? "result-chip-success" : "result-chip-danger"
                }`}
              >
                {style.badge}
              </span>
              {result.confidence_text && (
                <span className="text-small font-medium text-muted">
                  Confianza calibrada: {result.confidence_text}
                </span>
              )}
            </div>
            <h3 className="font-serif h3 text-ink">{style.title}</h3>
            <p className="text-body text-ink/90 leading-relaxed">{style.body}</p>

            {/* Métricas */}
            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="metric">
                <p className="metric-label">Clase mostrada</p>
                <p className="metric-value">{result.result_label}</p>
              </div>
              {result.margin != null && (
                <div className="metric">
                  <p className="metric-label">Margen entre clases</p>
                  <p className="metric-value">
                    {(result.margin * 100).toFixed(1)} pp
                  </p>
                </div>
              )}
            </div>

            {/* Distribución de probabilidades */}
            <div className="mt-6">
              <h3 className="font-serif h3 text-ink mb-3">Distribución de probabilidades</h3>
              <div className="space-y-2">
                {result.probabilities.map((p) => (
                  <div key={p.class} className="flex items-center gap-3">
                    <span className="w-16 text-small text-muted">{p.label}</span>
                    <div className="flex-1 h-3 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Math.max(p.probability, 0)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-small font-medium text-ink">
                      {p.probability.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted mt-3">
                La confianza es una medida técnica del modelo, no una probabilidad
                de tener o no cáncer.
              </p>
            </div>

            {/* Grad-CAM */}
            {result.gradcam_b64 && (
              <div className="mt-6">
                <h3 className="font-serif h3 text-ink mb-3">Explicación visual (Grad-CAM)</h3>
                <p className="text-small text-muted mb-3">
                  El mapa de calor muestra dónde se fijó el modelo. Las zonas
                  cálidas no señalan una lesión ni un diagnóstico.
                </p>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="image-frame min-h-[260px] bg-surface">
                    <img
                      src={`data:image/jpeg;base64,${result.image_b64}`}
                      alt="Ecografía original analizada"
                    />
                    <p className="absolute bottom-2 left-2 text-xs text-white/90 font-medium">Original</p>
                  </div>
                  <div className="image-frame min-h-[260px] bg-surface">
                    <img
                      src={`data:image/jpeg;base64,${result.gradcam_b64}`}
                      alt="Mapa de calor Grad-CAM"
                    />
                    <p className="absolute bottom-2 left-2 text-xs text-white/90 font-medium">Grad-CAM</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* No concluyente */}
        {status === "valida_no_concluyente" && (
          <div className="mt-5 pt-5 border-t border-border space-y-3">
            <p className="text-body text-ink/90 leading-relaxed">
              {result.message ||
                "No se muestra una clase ni un porcentaje porque hacerlo sería engañoso. Consulta a un especialista y, si es posible, repite la ecografía."}
            </p>
          </div>
        )}

        {/* Imagen no válida */}
        {status === "no_es_ecografia_mamaria" && (
          <div className="mt-5 pt-5 border-t border-border space-y-3">
            <p className="text-body text-ink/90 leading-relaxed">
              {result.message ||
                "No se generó ninguna clase ni ningún porcentaje. Sube una ecografía de mama en escala de grises."}
            </p>
            <ul className="list-disc list-inside text-small text-muted space-y-1">
              <li>Que sea una ecografía y no una foto, un dibujo o una captura de pantalla.</li>
              <li>Que esté en escala de grises y tenga textura de tejido.</li>
              <li>Que la resolución sea suficiente y la imagen no esté en blanco o negro.</li>
            </ul>
          </div>
        )}

        {/* Razones de la decisión */}
        {result.reasons && result.reasons.length > 0 && (
          <details className="mt-5 pt-5 border-t border-border">
            <summary className="cursor-pointer text-small font-medium text-primary flex items-center gap-1">
              <HelpCircle size={14} strokeWidth={2} />
              ¿Por qué se tomó esta decisión?
            </summary>
            <ul className="mt-3 list-disc list-inside text-small text-muted space-y-1">
              {[...new Set(result.reasons)].map((r) => (
                <li key={r}>{reasonText(r)}</li>
              ))}
            </ul>
          </details>
        )}

        {/* Detalles técnicos */}
        {(result.energy != null || result.temperature != null) && (
          <details className="mt-5 pt-5 border-t border-border">
            <summary className="cursor-pointer text-small font-medium text-primary flex items-center gap-1">
              <History size={14} strokeWidth={2} />
              Detalles técnicos del análisis
            </summary>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-small">
              <div>
                <p className="text-xs text-muted uppercase tracking-wider">Energy score</p>
                <p className="text-muted">{result.energy?.toFixed(3) ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-muted uppercase tracking-wider">Temperatura</p>
                <p className="text-muted">{result.temperature?.toFixed(2) ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-muted uppercase tracking-wider">Estado</p>
                <p className="text-muted">{status}</p>
              </div>
              <div>
                <p className="text-xs text-muted uppercase tracking-wider">Calibración</p>
                <p className="text-muted">
                  {(result.calibration as any)?.version ?? "desconocida"}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted/70 mt-3">
              Los umbrales son provisionales y provienen de fixtures sintéticos;
              no son calibración clínica.
            </p>
          </details>
        )}
      </div>

      {/* Aviso médico */}
      <div className="rounded-md bg-danger/10 border border-danger/20 p-4">
        <div className="flex items-start gap-2">
          <HelpCircle size={16} strokeWidth={2} className="text-danger mt-0.5" />
          <p className="text-sm text-danger leading-relaxed">
            <strong>Aviso médico importante:</strong> {DISCLAIMER}
          </p>
        </div>
      </div>

      {/* Descargar reporte y navegación */}
      <div className="flex flex-col md:flex-row gap-4 items-end">
        {result.image_b64 && (
          <button
            type="button"
            onClick={() => onDownloadReport(result.image_b64 || "")}
            className="btn-primary w-full md:w-auto"
          >
            <Download size={16} strokeWidth={2} /> Descargar reporte HTML
          </button>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onNewImage}
            className="btn-outline w-full md:w-auto"
          >
            <RefreshCw size={16} strokeWidth={2} /> Analizar otra imagen
          </button>
          <button
            type="button"
            onClick={onNewPatient}
            className="btn-outline w-full md:w-auto"
          >
            <UserPlus size={16} strokeWidth={2} /> Nuevo paciente
          </button>
        </div>
      </div>
    </section>
  );
}
