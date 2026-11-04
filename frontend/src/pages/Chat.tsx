import { useState, useCallback } from "react";
import { Send, MessageCircle, RefreshCw, Bot, Copy } from "lucide-react";
import { api } from "@/lib/api";
import type { AnalysisResult, ChatMessage } from "@/types";

const SUGGESTIONS: Array<{ label: string; question: string }> = [
  { label: "Autoexamen", question: "¿Qué es el autoexamen y cómo se hace?" },
  {
    label: "Factores de riesgo",
    question: "¿Cuáles son los factores de riesgo del cáncer de mama?",
  },
  {
    label: "Resultado no concluyente",
    question: "¿Cómo interpreto un resultado no concluyente?",
  },
  {
    label: "Síntomas de alarma",
    question: "¿Qué cambios en la mama merecen una consulta?",
  },
];

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<AnalysisResult | null>(null);

  const sendMessage = useCallback(async () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history: ChatMessage[] = messages;
      const data = await api.chat({
        question: input,
        history,
        last_result: lastResult,
      });
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.text,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            err.message ||
            "No se pudo obtener una respuesta. Inténtalo de nuevo.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, messages, lastResult]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="container-page">
      <div className="panel mb-6 space-y-4">
        <div>
          <h2 className="font-serif h3 text-ink flex items-center gap-2">
            <MessageCircle size={20} strokeWidth={2} className="text-primary" />
            Asistente educativo
          </h2>
          <p className="text-small text-muted">
            Pregunta sobre prevención, síntomas o cómo interpretar un resultado.
            Las respuestas se basan en documentos locales y citan sus fuentes.
            No es un diagnóstico.
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-1 rounded border border-border text-muted">
            Modo extractivo con citas
          </span>
          <span className="text-muted/60">·</span>
          <span className="text-muted">Sin llamadas de red salvo que se configure Claude.</span>
        </div>
      </div>

      <div className="flex-1 min-h-[400px] flex flex-col">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-muted">
            <Bot size={48} strokeWidth={2} className="mb-3 opacity-50" />
            <p>Empieza la conversación con una pregunta.</p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => {
                    setInput(s.question);
                    sendMessage();
                  }}
                  className="btn-outline w-full text-xs text-left"
                >
                  <MessageCircle size={14} strokeWidth={2} className="mr-2" />
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex-1 overflow-y-auto pr-4 scrollbar-hide space-y-4 p-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex flex-col gap-2 ${
                m.role === "user" ? "items-end" : "items-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-primary text-white"
                    : "bg-surface border border-border text-ink/90"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-start gap-2">
              <div className="bg-surface border border-border rounded-lg p-3 text-sm animate-pulse">
                Escribiendo…
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-surface p-4">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta…"
            className="input-field resize-none min-h-[44px] md:min-h-[52px] flex-1"
            rows={1}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary px-4"
          >
            <Send size={18} strokeWidth={2} />
          </button>
        </form>
        {messages.length > 0 && (
          <div className="mt-3 flex items-center justify-between">
            <button
              type="button"
              onClick={clearChat}
              className="btn-ghost text-xs px-2 py-1.5"
            >
              <RefreshCw size={14} strokeWidth={2} /> Limpiar conversación
            </button>
            <p className="text-xs text-muted/70">
              Esta información es educativa y no sustituye a un profesional.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
