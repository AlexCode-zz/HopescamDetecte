import { Microscope, Trash2, Upload, AlertCircle, Contrast } from "lucide-react";
import { useState } from "react";

interface ImageUploadProps {
  onImageReady: (file: File, previewUrl: string) => void;
  onClear: () => void;
  error: string | null;
  loading: boolean;
  demoImageB64: string | null;
  demoLabel: string;
  onLoadDemo: () => void;
}

export default function ImageUpload({
  onImageReady,
  onClear,
  error,
  loading,
  demoImageB64,
  demoLabel,
  onLoadDemo,
}: ImageUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    onImageReady(selected, URL.createObjectURL(selected));
  };

  const handleLoadDemo = () => {
    if (!demoImageB64) return;
    const blob = fetch(`data:image/jpeg;base64,${demoImageB64}`)
      .then((r) => r.blob())
      .then((b) => new File([b], "ecografia_demo.jpg", { type: "image/jpeg" }));
    blob.then((f) => {
      setFile(f);
      setPreview(URL.createObjectURL(f));
      onImageReady(f, URL.createObjectURL(f));
    });
    onLoadDemo();
  };

  const handleRemove = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    onClear();
  };

  return (
    <section className="panel space-y-5" data-entrance>
      <div>
        <h2 className="section-title">Paso 2 · Imagen de ecografía</h2>
        <p className="section-subtitle">
          Sube una ecografía mamaria en escala de grises. Formatos: PNG, JPG,
          WEBP, BMP o TIFF (máximo 15 MB). La imagen se procesa en memoria y no
          se guarda en el servidor.
        </p>
      </div>

      <div className="space-y-3">
        <label className="block">
          <span className="label">Selecciona la imagen</span>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
            onChange={handleFileChange}
            disabled={loading}
            className="block w-full text-sm text-muted file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary file:text-white hover:file:bg-primary-hover cursor-pointer"
          />
          <p className="text-xs text-muted mt-1">
            Evita capturas de pantalla, imágenes en color y fotos de baja
            resolución.
          </p>
        </label>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleLoadDemo}
            disabled={loading || !demoImageB64}
            className="btn-outline w-full md:w-auto"
          >
            <Microscope size={16} strokeWidth={2} /> Usar imagen de demostración
          </button>
          {preview && (
            <button
              type="button"
              onClick={handleRemove}
              disabled={loading}
              className="btn-outline w-full md:w-auto"
            >
              <Trash2 size={16} strokeWidth={2} /> Quitar imagen
            </button>
          )}
        </div>
      </div>

      {!preview && !loading && (
        <div className="rounded-md bg-muted/5 border border-border/50 p-8 text-center">
          <Upload size={32} strokeWidth={2} className="mx-auto text-muted/40 mb-3" />
          <p className="text-sm text-muted">Sube una imagen para continuar.</p>
          <p className="text-xs text-muted/60 mt-1">
            O usa la ecografía sintética de demostración.
          </p>
        </div>
      )}

      {preview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <div className="image-frame min-h-[320px]">
            <img src={preview} alt="Ecografía mamaria cargada para el análisis" />
            <div className="absolute inset-0 flex items-center justify-center bg-black/10 opacity-0 hover:opacity-100 transition-opacity group-hover:opacity-100">
              <span className="text-xs text-muted/80 font-medium">
                {file?.size ? (file.size / 1024).toFixed(0) + " KB" : ""}
              </span>
            </div>
          </div>
          <div className="panel-sm space-y-3">
            <h3 className="font-serif h3 text-ink">Archivo validado</h3>
            <div className="flex items-center gap-2 text-small">
              <Contrast size={16} strokeWidth={2} className="text-muted" />
              <span className="text-muted">{file?.type || "—"}</span>
            </div>
            <div className="flex items-center gap-2 text-small">
              <span className="font-medium text-ink">{file?.name}</span>
            </div>
            <p className="text-xs text-muted">
              La comprobación definitiva de que sea una ecografía mamaria se
              ejecuta al analizar. Si no lo es, no se mostrará ninguna clase.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-danger/10 border border-danger/20 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle size={14} strokeWidth={2} className="text-danger mt-0.5" />
            <p className="text-small text-danger">{error}</p>
          </div>
        </div>
      )}
    </section>
  );
}
