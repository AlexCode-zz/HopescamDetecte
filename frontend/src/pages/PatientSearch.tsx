import { useState, useEffect } from "react";
import { Search, Lock, Database, LogOut, RefreshCw, UserCircle } from "lucide-react";
import { api } from "@/lib/api";

export default function PatientSearch() {
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [searchEnabled, setSearchEnabled] = useState<boolean | null>(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Array<any>>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then((health) => setSearchEnabled(health.search_enabled))
      .catch(() => setSearchEnabled(false));
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    api.patientLogin(password)
      .then((data) => {
        if (data.authenticated) {
          setToken(data.token);
          setAuthenticated(true);
          setPassword("");
        }
      })
      .catch((err) => {
        setError(err.message || "Contraseña incorrecta.");
      })
      .finally(() => setLoading(false));
  };

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.patientSearch(token!, q);
      setResults(data.results);
      setCount(data.count);
    } catch (err: any) {
      setError(err.message || "No se pudo buscar.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setAuthenticated(false);
    setToken(null);
    setQ("");
    setResults([]);
    setCount(0);
    api.patientLogout(token!).catch(() => {});
  };

  return (
    <div className="container-page">
      <h1 className="font-serif text-2xl font-bold text-ink mb-2">
        Búsqueda de pacientes
      </h1>
      <p className="text-small text-muted mb-8">
        Acceso restringido a la base de datos de registros locales.
      </p>

      {/* Estado de configuración */}
      {searchEnabled === null && (
        <div className="rounded-md bg-muted/10 border border-border p-4 mb-6 flex items-center gap-3">
          <Database size={18} strokeWidth={2} className="text-muted" />
          <p className="text-small text-muted">Comprobando configuración…</p>
        </div>
      )}

      {!searchEnabled && searchEnabled !== null && (
        <div className="rounded-md bg-attention/10 border border-attention/20 p-4 mb-6">
          <div className="flex items-start gap-3">
            <Lock size={18} strokeWidth={2} className="text-attention mt-0.5" />
            <div>
              <h3 className="font-medium text-attention">
                Búsqueda deshabilitada
              </h3>
              <p className="text-small text-attention/90 mt-1">
                No hay una contraseña de búsqueda configurada. Por seguridad,
                no existe una contraseña por defecto.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Formulario de login */}
      {searchEnabled && !authenticated && (
        <div className="panel max-w-md space-y-4">
          <div>
            <h2 className="font-serif h3 text-ink">Acceso restringido</h2>
            <p className="text-small text-muted">
              La base contiene datos personales. Ingresa la contraseña para
              consultar los registros.
            </p>
          </div>
          <form onSubmit={handleLogin} className="space-y-3">
            <div className="space-y-1.5">
              <label className="label">Contraseña de acceso</label>
              <input
                type="password"
                placeholder="Ingresa la contraseña"
                className="input-field"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn-primary w-full"
              disabled={loading}
            >
              {loading ? "Ingresando…" : "Ingresar"}
              <Logout size={16} strokeWidth={2} />
            </button>
          </form>
          {error && (
            <div className="rounded-md bg-danger/10 border border-danger/20 p-3">
              <p className="text-small text-danger">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Resultados de búsqueda */}
      {authenticated && token && (
        <>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-serif h3 text-ink">
                Base de datos de pacientes registrados
              </h2>
              <p className="text-small text-muted">
                {count} registro{count !== 1 ? "s" : ""} en la base local.
              </p>
            </div>
            <button type="button" onClick={handleLogout} className="btn-outline text-xs px-3 py-2">
              <Logout size={14} strokeWidth={2} /> Cerrar sesión
            </button>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="label">Buscar por nombre, apellido o DUI</label>
              <div className="relative">
                <Search
                  size={16}
                  strokeWidth={2}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                />
                <input
                  type="text"
                  placeholder="Ej: Pérez o 01234567-8"
                  className="input-field pl-9"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
              </div>
                <button
                type="button"
                onClick={handleSearch}
                className="mt-2 btn-primary w-full md:w-auto"
              >
                <RefreshCw size={16} strokeWidth={2} /> Buscar
              </button>
              <p className="text-xs text-muted">
                El DUI se muestra enmascarado; la búsqueda por DUI completo
                sigue funcionando.
              </p>
            </div>

            <div className="overflow-hidden rounded-md border border-border">
              {results.length === 0 && (
                <div className="p-6 text-center">
                  <p className="text-small text-muted">
                    No se encontraron pacientes que coincidan con el término de
                    búsqueda.
                  </p>
                </div>
              )}
              {results.length > 0 && (
                <table className="w-full text-left text-small">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="pb-3 text-muted font-medium">
                        Paciente
                      </th>
                      <th className="pb-3 text-muted font-medium">
                        Edad · Género
                      </th>
                      <th className="pb-3 text-muted font-medium">DUI</th>
                      <th className="pb-3 text-muted font-medium">Registro</th>
                      <th className="pb-3 text-muted font-medium">Resultado IA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr
                        key={i}
                        className="border-b border-border/50 hover:bg-muted/5"
                      >
                        <td className="py-3 text-ink/90 font-medium">
                          {r.nombres} {r.apellidos}
                        </td>
                        <td className="py-3 text-muted">
                          {r.edad} · {r.genero}
                        </td>
                        <td className="py-3 text-muted font-mono">
                          {r.dui}
                        </td>
                        <td className="py-3 text-muted">
                          {r.fecha_registro}
                        </td>
                        <td className="py-3 text-muted">
                          {r.resultado_ia || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <p className="text-xs text-muted/70">
              El DUI se muestra enmascarado. No compartas esta pantalla ni
              exportes los datos sin autorización.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
