import { Outlet, useLocation, Link } from "react-router-dom";
import { Layers, Activity, Lock, Info } from "lucide-react";
import { DISCLAIMER } from "@/lib/constants";

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-surface sticky top-0 z-20">
        <div className="container-page flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center text-xs font-semibold text-white">
              HS
            </div>
            <div>
              <h1 className="font-serif text-lg font-bold text-ink tracking-tight">HopeScan</h1>
              <p className="text-xs text-muted">Apoyo a la detección temprana · El Salvador</p>
            </div>
          </div>
          <nav className="flex items-center gap-4 text-xs font-medium text-muted">
            <Link
              to="/"
              className={`flex items-center gap-1.5 px-3 py-2 rounded-md transition-colors ${
                location.pathname === "/" ? "bg-primary/10 text-primary border border-primary/20" : "hover:bg-muted/10 hover:text-ink"
              }`}
            >
              <Activity size={14} strokeWidth={2} /> Nuevo análisis
            </Link>
            <Link
              to="/buscar"
              className={`flex items-center gap-1.5 px-3 py-2 rounded-md transition-colors ${
                location.pathname === "/buscar"
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "hover:bg-muted/10 hover:text-ink"
              }`}
            >
              <Layers size={14} strokeWidth={2} /> Buscar paciente
            </Link>
            <Link
              to="/chat"
              className={`flex items-center gap-1.5 px-3 py-2 rounded-md transition-colors ${
                location.pathname === "/chat"
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "hover:bg-muted/10 hover:text-ink"
              }`}
            >
              <Info size={14} strokeWidth={2} /> Asistente educativo
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">{<Outlet />}</main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface py-6 mt-auto">
        <div className="container-page flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-muted">
          <p>
            {DISCLAIMER.split(".")[0]}.
          </p>
          <p className="text-muted/70">HopeScan · El Salvador · Herramienta de apoyo educativo</p>
        </div>
      </footer>
    </div>
  );
}
