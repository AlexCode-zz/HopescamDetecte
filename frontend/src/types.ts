export interface AnalysisResult {
  status: string;
  can_show_class: boolean;
  result: string | null;
  result_label: string | null;
  confidence: number | null;
  confidence_text: string | null;
  probabilities: {
    class: string;
    label: string;
    probability: number;
  }[];
  margin: number | null;
  energy: number | null;
  temperature: number | null;
  reasons: string[];
  features: Record<string, unknown>;
  message: string | null;
  image_b64: string | null;
  gradcam_b64: string | null;
  calibration: Record<string, unknown>;
  analysis_id: string | null;
  saved: boolean;
  save_error: string | null;
}

export interface PatientRecord {
  nombres: string;
  apellidos: string;
  edad: string | number;
  genero: string;
  dui: string;
  fecha_registro: string;
  resultado_ia: string;
  confianza_ia: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface PatientFormData {
  nombres: string;
  apellidos: string;
  edad: number;
  genero: string;
  dui: string;
  consent: boolean;
}

export interface ReasonLabel {
  key: string;
  label: string;
}
