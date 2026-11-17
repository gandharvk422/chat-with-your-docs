import { useEffect, useRef, useState } from "react";
import {
  AlertCircle, Bot, CheckCircle2, FileText, FolderOpen, Home, Info,
  MessageCircle, Moon, Paperclip, Send, Settings, Sun, UploadCloud, User, X, Zap,
} from "lucide-react";

// ---- Config -------------------------------------------------------------
// USE_MOCK = true  -> the UI works on its own with fake answers (no backend).
// USE_MOCK = false -> it calls your FastAPI backend at API_URL.
const USE_MOCK = false;
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const ALLOWED = ["pdf", "docx", "pptx", "txt", "md", "csv"];
const MAX_MB = 20;

const extOf = (name) => name.split(".").pop().toLowerCase();
const sizeLabel = (b) => (b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- API calls (the only place that talks to the backend) ---------------

// Read the backend's error message ({"detail": "..."}) or use a fallback.
async function errorMessage(res, fallback) {
  const data = await res.json().catch(() => ({}));
  return typeof data.detail === "string" ? data.detail : fallback;
}

// fetch() that turns "server unreachable" into a readable message.
async function request(path, options) {
  try {
    return await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error("Can't reach the server. Make sure the backend is running.");
  }
}

async function uploadFile(file) {
  if (USE_MOCK) return wait(1200);
  const body = new FormData();
  body.append("file", file);
  const res = await request("/upload", { method: "POST", body });
  if (!res.ok) throw new Error(await errorMessage(res, "Upload failed. Try again."));
}

async function askQuestion(question, fileName) {
  if (USE_MOCK) {
    await wait(1200);
    return {
      answer: `This is a sample answer to "${question}". Connect your backend and set USE_MOCK to false to get real answers from your document.`,
      sources: [{ file: fileName, page: 1 }],
    };
  }
  const res = await request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await errorMessage(res, "The server could not answer. Try again."));
  return res.json(); // { answer: string, sources: [{ file, page? }] }
}

// ---- Components ---------------------------------------------------------
function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <details className="sources">
      <summary>Sources ({sources.length})</summary>
      {sources.map((s, i) => (
        <div className="source" key={i}>
          <FileText size={16} />
          <span>{s.file}</span>
          {s.page != null && <em>page {s.page}</em>}
        </div>
      ))}
    </details>
  );
}

function Message({ m }) {
  const isUser = m.role === "user";
  return (
    <div className={`msg ${isUser ? "user" : "bot"}`}>
      <div className="avatar">{isUser ? <User size={20} /> : <Bot size={22} />}</div>
      <div className="msg-body">
        <div className="bubble">{m.text}</div>
        {!isUser && <Sources sources={m.sources} />}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("home");
  const [theme, setTheme] = useState("light");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | ready | error
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, thinking]);

  async function handleFile(f) {
    if (!f) return;
    if (!ALLOWED.includes(extOf(f.name))) {
      setStatus("error");
      setError(`.${extOf(f.name)} files aren't supported. Supported: ${ALLOWED.map((e) => e.toUpperCase()).join(", ")}.`);
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setStatus("error");
      setError(`That file is larger than ${MAX_MB} MB. Choose a smaller one.`);
      return;
    }
    setFile(f); setStatus("uploading"); setError(""); setMessages([]);
    try {
      await uploadFile(f);
      setStatus("ready");
    } catch (e) {
      setStatus("error"); setError(e.message); setFile(null);
    }
  }

  function removeFile() {
    setFile(null); setStatus("idle"); setError(""); setMessages([]);
  }

  async function send() {
    const q = input.trim();
    if (!q || thinking) return;
    if (status !== "ready") {
      setStatus("error"); setError("Upload a document before asking a question.");
      return;
    }
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setThinking(true);
    try {
      const { answer, sources } = await askQuestion(q, file.name);
      setMessages((m) => [...m, { role: "bot", text: answer, sources }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: e.message }]);
    } finally {
      setThinking(false);
    }
  }

  const nav = [
    { id: "home", label: "Home", icon: Home },
    { id: "about", label: "About", icon: Info },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <FileText size={44} strokeWidth={1.6} />
          <h1>Chat with<br />Your Docs</h1>
          <p>Upload. Ask. Get answers.</p>
        </div>
        <nav>
          {nav.map(({ id, label, icon: Icon }) => (
            <button key={id} className={page === id ? "active" : ""} onClick={() => setPage(id)}>
              <Icon size={20} /> {label}
            </button>
          ))}
        </nav>
        <div className="powered"><Zap size={20} /><div>Powered by<br /><strong>RAG + FastAPI + React</strong></div></div>
      </aside>

      <main className="main">
        <div className="topbar">
          <button className="theme" onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}>
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            {theme === "light" ? "Dark" : "Light"} theme
          </button>
        </div>

        {page === "about" && (
          <section className="card">
            <h2>About</h2>
            <p>Chat with Your Docs answers questions using only the content of the file you upload, and shows which file each answer came from. It uses retrieval-augmented generation (RAG): your document is split into chunks, the most relevant chunks are found for each question, and a language model writes the answer from them.</p>
          </section>
        )}

        {page === "settings" && (
          <section className="card">
            <h2>Settings</h2>
            <p>Backend: <strong>{USE_MOCK ? "Demo mode (no server)" : API_URL}</strong></p>
            <p className="muted">To use your real backend, set <code>USE_MOCK</code> to <code>false</code> at the top of <code>src/App.jsx</code>.</p>
            <p>Allowed files: {ALLOWED.map((e) => e.toUpperCase()).join(", ")} (up to {MAX_MB} MB)</p>
          </section>
        )}

        {page === "home" && (
          <>
            <section className="hero">
              <div className="hero-art"><UploadCloud size={72} strokeWidth={1.5} /></div>
              <div>
                <h2>Chat with Your Documents</h2>
                <p>Upload a document, and ask questions about its content using the power of RAG.</p>
              </div>
            </section>

            <section className="card upload">
              <div className="up-left">
                <h3><UploadCloud size={22} /> 1. Upload your file</h3>
                <p className="muted">Supported formats: PDF, DOCX, PPTX, TXT, MD, CSV</p>
                <div
                  className={`drop ${dragging ? "over" : ""}`}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
                >
                  <UploadCloud size={30} />
                  <span>Drag and drop your file here</span>
                  <span className="muted">or</span>
                  <label className="btn">
                    <FolderOpen size={18} /> Choose file
                    <input type="file" hidden accept={ALLOWED.map((e) => `.${e}`).join(",")}
                      onChange={(e) => { handleFile(e.target.files[0]); e.target.value = ""; }} />
                  </label>
                </div>
              </div>

              <div className="up-right">
                <h3><CheckCircle2 size={22} className="ok" /> Uploaded file</h3>
                {file ? (
                  <div className="file">
                    <FileText size={28} className="pdf" />
                    <div><strong>{file.name}</strong><div className="muted">{sizeLabel(file.size)}</div></div>
                    <button className="icon" onClick={removeFile} aria-label="Remove file"><X size={20} /></button>
                  </div>
                ) : (
                  <p className="muted">No file yet. Upload one to start asking questions.</p>
                )}
                {status === "uploading" && <div className="note info">Reading your document…</div>}
                {status === "ready" && <div className="note good"><CheckCircle2 size={20} /> File ready! You can now ask questions.</div>}
                {status === "error" && <div className="note bad" role="alert"><AlertCircle size={20} /> {error}</div>}
              </div>
            </section>

            <section className="card chat">
              <h3><MessageCircle size={22} /> 2. Ask your question</h3>
              <div className="thread" aria-live="polite">
                {messages.length === 0 && !thinking && (
                  <p className="muted empty">Your conversation will appear here. Try asking for a summary of the document.</p>
                )}
                {messages.map((m, i) => <Message key={i} m={m} />)}
                {thinking && (
                  <div className="msg bot">
                    <div className="avatar"><Bot size={22} /></div>
                    <div className="bubble typing"><span /><span /><span /></div>
                  </div>
                )}
                <div ref={endRef} />
              </div>
              <div className="composer">
                <button className="icon" onClick={() => document.querySelector('input[type="file"]').click()} aria-label="Attach a file">
                  <Paperclip size={20} />
                </button>
                <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask anything about your document…" />
                <button className="send" onClick={send} disabled={!input.trim() || thinking} aria-label="Send question">
                  <Send size={22} />
                </button>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}