export const REASON_LABELS: Record<string, string> = {
  resolucion_minima: "La resolución es demasiado baja para una ecografía.",
  razon_aspecto_fuera_rango: "La proporción de la imagen no es compatible con una ecografía.",
  imagen_en_color: "La imagen contiene color; una ecografía B-mode suele ser en escala de grises.",
  imagen_plana: "La imagen es casi uniforme, sin textura de tejido.",
  pocos_tonos: "La imagen tiene muy pocos tonos de gris.",
  contraste_extremo: "El contraste es extremo para una ecografía.",
  entropia_baja: "La distribución de tonos es demasiado simple.",
  entropia_alta_ruido: "La imagen parece ruido, no tejido.",
  sin_textura: "No se detecta textura de tejido.",
  ruido_excesivo: "Hay demasiado ruido o bordes artificiales.",
  entropia_limite: "La textura está en el límite de lo esperado.",
  textura_limite: "La textura está en el límite de lo esperado.",
  speckle_bajo: "No se observa el moteado típico del ultrasonido.",
  gama_limitada: "La gama de grises es limitada.",
  sobreexpuesta: "La imagen está sobreexpuesta.",
  subexpuesta: "La imagen está subexpuesta.",
  confianza_calibrada_baja: "La confianza calibrada del modelo es baja.",
  clases_compitiendo: "Dos clases tienen probabilidades muy parecidas.",
  energy_score_fuera_de_rango: "El modelo detectó un patrón atípico (energy score alto).",
  archivo_invalido: "El archivo no se pudo leer como una imagen válida.",
  error_inferencia: "Ocurrió un error durante la inferencia.",
};

export function reasonText(key: string): string {
  return REASON_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export const CLASS_STYLES: Record<string, { badge: string; title: string; body: string; variant: "success" | "danger" | "neutral" }> = {
  Maligno: {
    badge: "Hallazgo sospechoso",
    title: "Hallazgo sospechoso",
    body: "El modelo encontró un patrón compatible con malignidad. Esto no es un diagnóstico. Acude a un profesional de la salud para una valoración prioritaria.",
    variant: "danger",
  },
  Benigno: {
    badge: "Patrón de bajo riesgo",
    title: "Patrón de bajo riesgo",
    body: "El modelo encontró un patrón compatible con benignidad. Esto no descarta una enfermedad. Lleva el resultado a una revisión profesional.",
    variant: "success",
  },
  Normal: {
    badge: "Sin hallazgos evidentes",
    title: "Sin hallazgos evidentes",
    body: "El modelo no detectó patrones de riesgo relevantes. Esto no es una garantía de salud. Mantén los controles preventivos y consulta ante cualquier cambio.",
    variant: "success",
  },
};

export const STATUS_VARIANT: Record<string, "success" | "danger" | "attention" | "neutral"> = {
  valida_confiable: "success",
  valida_no_concluyente: "attention",
  no_es_ecografia_mamaria: "danger",
};

export const DISCLAIMER =
  "HopeScan es una herramienta educativa de apoyo. NO es un dispositivo médico y NO sustituye el diagnóstico de un profesional de la salud. La interpretación final debe realizarla un oncólogo, radiólogo o profesional calificado.";

export const CONTACTOS_MEDICOS: Array<{ nombre: string; datos: string[] }> = [
  {
    nombre: "Hospital Oncológico del ISSS",
    datos: [
      "Teléfono: 2591-5000",
      "Dirección: San Salvador, entre la 25 Avenida Norte y la 1.ª Calle Poniente.",
      "Horario: lunes a viernes, 7:00 a. m. – 4:00 p. m.",
      "Web: https://www.isss.gob.sv/centros-de-atencion/",
    ],
  },
  {
    nombre: "Centro Internacional de Cáncer (CIC)",
    datos: [
      "Teléfono: +503 2506-2001",
      "Dirección: 3.ª Calle Poniente, Block 122, Colonia Escalón, San Salvador.",
      "Horario: lunes a viernes, 8:00 a. m. – 5:00 p. m.",
      "Web: https://www.centrodecancer.com.sv",
    ],
  },
  {
    nombre: "Instituto del Cáncer de El Salvador (ICES)",
    datos: [
      "Dirección: Dr. Narciso Díaz Bazán, 1.ª Calle Poniente y 33 Avenida Norte, Colonia Escalón, San Salvador.",
      "Horario: lunes a viernes, 6:30 a. m. – 3:30 p. m.",
      "Teléfono: +503 2521-8282 / 2521-8200",
    ],
  },
];
