import { ArrowRight, Microscope, User, Calendar, ShieldCheck, Info } from "lucide-react";
import { useState } from "react";
import { DISCLAIMER } from "@/lib/constants";

export interface PatientFormData {
  nombres: string;
  apellidos: string;
  edad: number;
  genero: string;
  dui: string;
  consent: boolean;
}

interface PatientFormProps {
  demoMode: boolean;
  setDemoMode: (v: boolean) => void;
  onSubmit: (data: PatientFormData) => void;
  error: string | null;
  loading: boolean;
}

export default function PatientForm({
  demoMode,
  setDemoMode,
  onSubmit,
  error,
  loading,
}: PatientFormProps) {
  const [form, setForm] = useState<PatientFormData>({
    nombres: "",
    apellidos: "",
    edad: 30,
    genero: "Femenino",
    dui: "",
    consent: false,
  });

  const handleDemoChange = () => setDemoMode((prev) => {
    const next = !prev;
    setForm((f) => {
      if (next) {
        return {
          ...f,
          nombres: "Paciente",
          apellidos: "Demostración",
          edad: 42,
          genero: "Femenino",
          dui: "01234567-8",
        };
      }
      return { ...f, nombres: "", apellidos: "", edad: 30, dui: "" };
    });
    return next;
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <section className="panel space-y-5" data-entrance>
      <div>
        <h2 className="section-title">Paso 1 · Datos del paciente</h2>
        <p className="section-subtitle">
          Los datos se guardan en un archivo CSV local. En modo demostración se
          usan datos ficticios y no se escribe ningún registro.
        </p>
      </div>

      <label className="flex items-center gap-2 cursor-pointer select-none group">
        <input
          type="checkbox"
          checked={demoMode}
          onChange={handleDemoChange}
          className="rounded border-border text-primary focus:ring-primary bg-surface border"
        />
        <span className="text-sm font-medium text-ink group-hover:text-primary transition-colors">
          Modo demostración
        </span>
        <Microscope size={16} strokeWidth={2} className="text-muted/60 group-hover:text-primary" />
      </label>

      {demoMode && (
        <div className="rounded-md bg-attention/10 border border-attention/20 p-3">
          <div className="flex items-start gap-2">
            <Microscope size={14} strokeWidth={2} className="text-attention mt-0.5" />
            <p className="text-small text-attention">
              Datos ficticios de demostración. El resultado no se guardará.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="label">Nombres <span className="text-danger">*</span></label>
            <input
              type="text"
              placeholder="Ana"
              className="input-field"
              value={form.nombres}
              onChange={(e) => setForm({ ...form, nombres: e.target.value })}
              disabled={demoMode}
            />
          </div>
          <div className="space-y-1.5">
            <label className="label">Apellidos <span className="text-danger">*</span></label>
            <input
              type="text"
              placeholder="Pérez"
              className="input-field"
              value={form.apellidos}
              onChange={(e) => setForm({ ...form, apellidos: e.target.value })}
              disabled={demoMode}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="label">Edad (años) <span className="text-danger">*</span></label>
            <input
              type="number"
              min="0"
              max="120"
              className="input-field"
              value={form.edad}
              onChange={(e) => setForm({ ...form, edad: Number(e.target.value) || 0 })}
              disabled={demoMode}
            />
          </div>
          <div className="space-y-1.5">
            <label className="label">Género</label>
            <select
              className="input-field"
              value={form.genero}
              onChange={(e) => setForm({ ...form, genero: e.target.value })}
              disabled={demoMode}
            >
              <option>Femenino</option>
              <option>Masculino</option>
              <option>Otro</option>
              <option>Prefiero no decir</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="label">DUI</label>
          <p className="text-xs text-muted">
            Obligatorio para mayores de 18 años. No registres el DUI de una
            persona menor de edad.
          </p>
          <input
            type="text"
            placeholder="01234567-8"
            className="input-field"
            value={form.dui}
            onChange={(e) => setForm({ ...form, dui: e.target.value })}
            disabled={demoMode}
          />
        </div>

        <label className="flex items-start gap-3 cursor-pointer select-none group">
          <input
            type="checkbox"
            checked={form.consent}
            onChange={(e) => setForm({ ...form, consent: e.target.checked })}
            className="rounded border-border text-primary focus:ring-primary bg-surface border mt-0.5"
          />
          <div className="text-sm text-ink leading-relaxed group-hover:text-ink/90 transition-colors">
            Confirmo que tengo autorización para analizar esta imagen y que
            entiendo que <strong>HopeScan no emite un diagnóstico.</strong>
          </div>
          <ShieldCheck size={16} strokeWidth={2} className="text-muted/60 group-hover:text-primary mt-0.5" />
        </label>

      <button
        type="submit"
        className="btn-primary w-full"
        disabled={loading}
      >
        {loading ? "Guardando…" : "Guardar y continuar"}
        <ArrowRight size={16} strokeWidth={2} />
      </button>
      </form>

      {error && (
        <div className="rounded-md bg-danger/10 border border-danger/20 p-3">
          <div className="flex items-start gap-2">
            <Info size={14} strokeWidth={2} className="text-danger mt-0.5" />
            <p className="text-small text-danger">{error}</p>
          </div>
        </div>
      )}
    </section>
  );
}
