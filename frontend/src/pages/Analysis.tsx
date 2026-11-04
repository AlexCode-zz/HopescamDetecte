import { useState, useCallback } from "react";
import { PlayCircle, Microscope, RefreshCw, UserPlus, Download } from "lucide-react";
import { api } from "@/lib/api";
import { DISCLAIMER } from "@/lib/constants";
import type { PatientFormData, AnalysisResult as AnalysisResultType } from "@/types";
import Progress from "@/components/Progress";
import PatientForm from "@/components/PatientForm";
import ImageUpload from "@/components/ImageUpload";
import AnalysisResult from "@/components/AnalysisResult";

export default function Analysis() {
  const [step, setStep] = useState(1);
  const [patientData, setPatientData] = useState<PatientFormData>({
    nombres: "",
    apellidos: "",
    edad: 30,
    genero: "Femenino",
    dui: "",
    consent: false,
  });
  const [demoMode, setDemoMode] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResultType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [demoImageB64, setDemoImageB64] = useState<string | null>(null);
  const [demoLabel, setDemoLabel] = useState("Ecografía sintética de demostración");

  const loadDemo = useCallback(async () => {
    try {
      const data = await api.demoImage();
      setDemoImageB64(data.image_b64);
      setDemoLabel(data.label);
    } catch {
      setDemoImageB64(null);
    }
  }, []);

  const handlePatientSubmit = (data: PatientFormData) => {
    setPatientData(data);
    setStep(2);
    setResult(null);
    setError(null);
  };

  const handleImageReady = (file: File, previewUrl: string) => {
    setImageFile(file);
    setImagePreview(previewUrl);
  };

  const handleClearImage = () => {
    setImageFile(null);
    setImagePreview(null);
  };

  const handleRunAnalysis = async () => {
    if (!imageFile) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("image", imageFile);
      form.append("patient_data", JSON.stringify(patientData));
      form.append("demo_mode", String(demoMode));
      form.append("with_gradcam", "true");

      const data = await api.analyze(form);
      setResult(data);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "No se pudo completar el análisis.");
    } finally {
      setLoading(false);
    }
  };

  const handleNewImage = () => {
    setStep(2);
    setResult(null);
    setImageFile(null);
    setImagePreview(null);
    setError(null);
  };

  const handleNewPatient = () => {
    setStep(1);
    setResult(null);
    setImageFile(null);
    setImagePreview(null);
    setPatientData({
      nombres: "",
      apellidos: "",
      edad: 30,
      genero: "Femenino",
      dui: "",
      consent: false,
    });
    setDemoMode(false);
    setError(null);
  };

  const handleDownloadReport = () => {
    if (!result || !imagePreview) return;
    const content = buildReportHTML(result, imagePreview);
    const blob = new Blob([content], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Reporte_HopeScan_${(patientData.apellidos || "paciente").replace(/[^A-Za-z0-9_-]+/g, "_") || "paciente"}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-serif text-2xl font-bold text-ink">Nuevo análisis</h1>
          <p className="text-small text-muted">
            Registra al paciente, sube la ecografía y recibe un resultado
            seguro. Nada se muestra sin certeza suficiente.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {demoImageB64 ? null : (
            <button
              type="button"
              onClick={loadDemo}
              disabled={loading}
              className="btn-outline text-xs px-3 py-2"
            >
              <Microscope size={14} strokeWidth={2} /> Cargar demostración
            </button>
          )}
        </div>
      </div>

      {step === 1 && (
        <>
          <Progress step={1} />
          <PatientForm
            demoMode={demoMode}
            setDemoMode={setDemoMode}
            onSubmit={handlePatientSubmit}
            error={error}
            loading={loading}
          />
        </>
      )}

      {step === 2 && (
        <>
          <Progress step={2} />
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Resumen del paciente (solo lectura) */}
            <div className="lg:col-span-4">
              <div className="panel space-y-4">
                <h3 className="font-serif h3 text-ink">Paciente</h3>
                <p className="text-body text-ink/90">
                  <strong>{patientData.nombres} {patientData.apellidos}</strong>
                </p>
                <p className="text-small text-muted">
                  {patientData.edad} años · {patientData.genero} ·
                  DUI: {patientData.dui || "No registrado"}
                </p>
                {demoMode && (
                  <div className="rounded-md bg-attention/10 border border-attention/20 p-3">
                    <p className="text-small text-attention flex items-center gap-2">
                      <Microscope size={14} strokeWidth={2} /> Modo demostración:
                      datos ficticios, no se guarda.
                    </p>
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="btn-outline w-full text-xs"
                >
                  Editar datos
                </button>
              </div>
            </div>
            {/* Imagen y análisis */}
            <div className="lg:col-span-8">
              <ImageUpload
                onImageReady={handleImageReady}
                onClear={handleClearImage}
                error={error}
                loading={loading}
                demoImageB64={demoImageB64}
                demoLabel={demoLabel}
                onLoadDemo={loadDemo}
              />
              {imagePreview && (
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={loading}
                    className="btn-primary w-full"
                  >
                    <PlayCircle size={18} strokeWidth={2} /> Analizar con IA
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {step === 3 && result && (
        <>
          <Progress step={3} />
          <h2 className="font-serif h2 text-ink mb-4">Paso 3 · Resultado del análisis</h2>
          <AnalysisResult
            result={result}
            onNewImage={handleNewImage}
            onNewPatient={handleNewPatient}
            onDownloadReport={handleDownloadReport}
          />
        </>
      )}

      {error && step !== 1 && (
        <div className="mt-4 rounded-md bg-danger/10 border border-danger/20 p-3">
          <p className="text-small text-danger">{error}</p>
        </div>
      )}
    </div>
  );
}

function buildReportHTML(result: AnalysisResultType, imagePreview: string): string {
  const now = new Date().toLocaleString("es-ES");
  const status = result.status;
  const showClass = result.can_show_class && result.result;
  const style = showClass
    ? {
        badge: "Resultado",
        title: "Resultado",
        body: "Resultado del análisis por IA.",
        variant: "neutral" as const,
      }
    : { badge: "Resultado", title: "Resultado", body: "", variant: "neutral" as const };

  const labelMap: Record<string, string> = {
    Maligno: "Hallazgo sospechoso",
    Benigno: "Patrón de bajo riesgo",
    Normal: "Sin hallazgos evidentes",
  };
  if (showClass && result.result) {
    style.badge = labelMap[result.result] ?? "Resultado";
    style.title = style.badge;
  }

  let statusText = "";
  let statusDetail = "";
  if (status === "valida_confiable") {
    statusText = "Análisis válido y confiable";
    statusDetail =
      "Se muestra la clase, la confianza calibrada y el Grad-CAM. Esto no es un diagnóstico.";
  } else if (status === "valida_no_concluyente") {
    statusText = "Análisis no concluyente";
    statusDetail =
      "El modelo no tiene certeza suficiente. No se fuerza un resultado.";
  } else {
    statusText = "Imagen no válida";
    statusDetail =
      "No se generó ninguna clase ni ningún porcentaje.";
  }

  const probsHtml = result.probabilities
    .map(
      (p) =>
        `<li><strong>${p.label}:</strong> ${p.probability.toFixed(1)}%</li>`,
    )
    .join("");

  const gradcamHtml = result.gradcam_b64
    ? `<div style="margin-top:1rem;"><h3 style="font-family:'Source Serif 4',serif;font-size:1.125rem;margin-bottom:0.5rem;">Grad-CAM</h3><img src="data:image/jpeg;base64,${result.gradcam_b64}" alt="Grad-CAM" style="max-width:100%;border:1px solid #E7E4E0;border-radius:0.5rem;"/><p style="font-size:0.875rem;color:#6E6670;margin-top:0.5rem;">El mapa de calor muestra dónde se fijó el modelo. No es una lesión ni un diagnóstico.</p></div>`
    : "";

  return `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Reporte HopeScan</title><style>body{font-family:Inter,sans-serif;background:#FDF9F5;color:#1A181A;padding:2rem;line-height:1.6;}h1,h2,h3{font-family:'Source Serif 4',serif;color:#1A181A;}h1{font-size:1.75rem;color:#7C3AED;margin-bottom:0.5rem;}h2{font-size:1.25rem;margin-top:1.5rem;margin-bottom:0.5rem;border-bottom:1px solid #E7E4E0;padding-bottom:0.25rem;} .box{border:1px solid #E7E4E0;border-radius:0.75rem;padding:1.25rem;background:#fff;margin:1rem 0;} img{max-width:100%;border:1px solid #E7E4E0;border-radius:0.5rem;} .chip{display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.875rem;font-weight:600;border:1px solid;margin-right:0.5rem;} .chip-success{background:#ecfdf5;color:#047857;border-color:#a7f3d0;} .chip-danger{background:#fef2f2;color:#b91c1c;border-color:#fecaca;} .chip-attention{background:#fffbeb;color:#d97706;border-color:#fde68a;} .disclaimer{font-size:0.85rem;color:#6E6670;border-top:1px dashed #E7E4E0;margin-top:1.5rem;padding-top:1rem;} .muted{color:#6E6670;font-size:0.875rem;}</style></head><body><h1>HopeScan — Reporte de análisis</h1><p class="muted">${now}</p><div class="box"><h2>Datos del paciente</h2><p><strong>Nombres:</strong> ${patientData?.nombres ?? "—"}</p><p><strong>Apellidos:</strong> ${patientData?.apellidos ?? "—"}</p><p><strong>Edad:</strong> ${patientData?.edad ?? "—"} años</p><p><strong>Género:</strong> ${patientData?.genero ?? "—"}</p><p><strong>DUI:</strong> ${patientData?.dui || "No registrado"}</p></div><div class="box"><h2>Imagen analizada</h2><img src="${imagePreview}" alt="Ecografía analizada"/></div><div class="box"><h2>Resultado del análisis</h2><p><strong>Estado:</strong> ${statusText}</p><p class="muted">${statusDetail}</p>${showClass ? `<p><span class="chip chip-${style.variant}">${style.badge}</span><br/><strong>Clase:</strong> ${result.result_label}<br/><strong>Confianza calibrada:</strong> ${result.confidence_text ?? "—"}</p>` : ""}<h3>Distribución de probabilidades</h3><ul>${probsHtml || "<li>No disponible.</li>"}</ul>${gradcamHtml}</div><p class="disclaimer"><strong>Aviso médico importante:</strong> ${DISCLAIMER}</p></body></html>`;
}
