#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arkymedes — GUI v5.0 - Interface Modernizada com Sidebar

Melhorias visuais e de UX:
  - Layout com sidebar para fórmulas rápidas
  - Cards modernos com hierarquia visual clara
  - Resultado em destaque com fonte grande
  - Botões com efeito hover e feedback visual
  - Design responsivo que se adapta ao redimensionamento
  - Mantém 100% da funcionalidade da v3.0
"""

import csv
import json
import locale
import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent))

from arkymedes_calc import (
    calculate_expression,
    extract_text_from_pdf,
    ocr_text_from_image,
)

try:
    from knowledge_base import KnowledgeBase
    from knowledge_gui import KnowledgeManager
    HAS_KB = True
except ImportError:
    HAS_KB = False

try:
    import sv_ttk
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# ------------------------------------------------------------------
# Locale para formatação numérica
# ------------------------------------------------------------------
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

LOG_DIR = Path(__file__).parent / ".logs"
LOG_DIR.mkdir(exist_ok=True)

_log_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "arkymedes.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_FILE = Path(__file__).parent / "arkymedes_history.json"
PREFS_FILE   = Path(__file__).parent / ".arkymedes_prefs.json"
APP_VERSION  = "5.0"

# Placeholders rotativos
PLACEHOLDERS = (
    "ex: 23 * 17",
    "ex: sqrt(16)",
    "ex: área do círculo raio=5",
    "ex: 2 ** 10",
    "ex: sin(pi/2)",
    "ex: juros compostos p=1000 i=0.1 n=2",
    "ex: log10(1000)",
    "ex: volume da esfera r=3",
)

# Cores do tema moderno
COLORS = {
    'dark': {
        'bg': '#1a1a2e',
        'card': '#16213e',
        'card_border': '#0f3460',
        'accent': '#e94560',
        'accent_hover': '#ff6b6b',
        'text': '#eeeeee',
        'text_secondary': '#aaaaaa',
        'text_muted': '#666666',
        'success': '#00d9a5',
        'error': '#ff6b6b',
        'input_bg': '#0f3460',
    },
    'light': {
        'bg': '#f5f5f5',
        'card': '#ffffff',
        'card_border': '#e0e0e0',
        'accent': '#3498db',
        'accent_hover': '#5dade2',
        'text': '#2c3e50',
        'text_secondary': '#7f8c8d',
        'text_muted': '#95a5a6',
        'success': '#27ae60',
        'error': '#e74c3c',
        'input_bg': '#ffffff',
    }
}


# ------------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------------

def _format_number(value: float) -> str:
    """Formata número com separador de milhar e casas decimais limpas."""
    try:
        if value == int(value) and abs(value) < 1e15:
            return locale.format_string("%d", int(value), grouping=True)
        else:
            raw = f"{value:.10f}".rstrip("0").rstrip(".")
            parts = raw.split(".")
            int_part = locale.format_string("%d", int(float(parts[0])), grouping=True)
            return f"{int_part}.{parts[1]}" if len(parts) > 1 else int_part
    except Exception:
        return str(value)


# ------------------------------------------------------------------
# Worker thread
# ------------------------------------------------------------------

class WorkerThread(threading.Thread):
    def __init__(self, task_fn, result_queue, *args):
        super().__init__(daemon=True)
        self._task_fn = task_fn
        self._args = args
        self._result_queue = result_queue
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        if self._cancelled.is_set():
            self._result_queue.put(("cancelled", None))
            return
        try:
            result = self._task_fn(*self._args)
            self._result_queue.put(
                ("cancelled", None) if self._cancelled.is_set() else ("success", result)
            )
        except Exception as exc:
            logger.exception("Erro na thread: %s", exc)
            self._result_queue.put(("error", str(exc)))


# ------------------------------------------------------------------
# Modelo de histórico
# ------------------------------------------------------------------

class HistoryEntry:
    def __init__(self, entrada, resultado, fonte, timestamp=None):
        self.entrada = entrada
        self.resultado = resultado
        self.fonte = fonte
        self.timestamp = timestamp or datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def to_dict(self):
        return {"entrada": self.entrada, "resultado": self.resultado,
                "fonte": self.fonte, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("entrada", ""), data.get("resultado", ""),
                   data.get("fonte", ""), data.get("timestamp"))


# ------------------------------------------------------------------
# Tooltip helper
# ------------------------------------------------------------------

class ToolTip:
    """Cria tooltips simples para widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self._show_tip)
        widget.bind('<Leave>', self._hide_tip)

    def _show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack()

    def _hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ------------------------------------------------------------------
# Botão moderno com efeito hover
# ------------------------------------------------------------------

class ModernButton(tk.Button):
    """Botão com estilo moderno e efeito hover."""
    
    def __init__(self, parent, text, command=None, accent=False, **kwargs):
        self.colors = COLORS['dark']
        self.accent = accent
        self.default_bg = None
        
        super().__init__(
            parent,
            text=text,
            command=command,
            font=('Segoe UI', 10),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8,
            **kwargs
        )
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def update_colors(self, colors):
        """Atualiza cores do botão conforme o tema."""
        self.colors = colors
        if self.accent:
            self.default_bg = colors['accent']
            self.config(bg=colors['accent'], fg='white',
                       activebackground=colors['accent_hover'],
                       activeforeground='white')
        else:
            self.default_bg = colors['card_border']
            self.config(bg=colors['card_border'], fg=colors['text'],
                       activebackground=colors['accent'],
                       activeforeground='white')
    
    def _on_enter(self, e):
        if self.accent:
            self.config(bg=self.colors['accent_hover'])
        else:
            self.config(bg=self.colors['accent'], fg='white')
    
    def _on_leave(self, e):
        self.config(bg=self.default_bg, fg='white' if self.accent else self.colors['text'])


# ------------------------------------------------------------------
# Aplicação principal modernizada
# ------------------------------------------------------------------

class ArkymedesGUI:
    POLL_INTERVAL = 100

    def __init__(self, root):
        self.root = root
        self.root.title(f"Arkymedes v{APP_VERSION}")
        self.root.geometry("1300x800")
        self.root.resizable(True, True)
        self.root.minsize(1100, 700)

        try:
            self.root.iconbitmap("arkymedes.ico")
        except (FileNotFoundError, tk.TclError):
            pass

        # Estado
        self.history = []
        self._result_queue = Queue()
        self._active_worker = None
        self._kb = KnowledgeBase() if HAS_KB else None
        self._dark_mode = True
        self._placeholder_active = False
        self._placeholder_idx = 0
        self._last_result_value = None
        self._preview_timer = None
        self._current_colors = COLORS['dark']
        self._modern_buttons = []

        # Preferências persistentes
        self._prefs = self._load_prefs()
        self._dark_mode = self._prefs.get("dark_mode", True)

        # Aplicar tema
        self._apply_theme(self._dark_mode)

        self._build_ui()
        self._load_history()
        self._setup_keyboard_shortcuts()
        self._setup_live_preview()
        self._setup_auto_format()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        logger.info("Aplicação iniciada v%s", APP_VERSION)

        # Mostrar onboarding na primeira execução
        if not self._prefs.get("onboarding_done"):
            self.root.after(300, self._show_onboarding)

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def _apply_theme(self, dark=False):
        """Aplica tema dark/light moderno."""
        self._dark_mode = dark
        self._current_colors = COLORS['dark'] if dark else COLORS['light']
        
        if HAS_SV_TTK:
            sv_ttk.set_theme("dark" if dark else "light")
        
        # Configurar cores da janela principal
        self.root.configure(bg=self._current_colors['bg'])
        
        # Configurar estilo ttk
        style = ttk.Style()
        style.configure('TFrame', background=self._current_colors['bg'])
        style.configure('TLabel', background=self._current_colors['bg'], 
                       foreground=self._current_colors['text'])
        style.configure('TLabelframe', background=self._current_colors['card'],
                       foreground=self._current_colors['text'])
        style.configure('TLabelframe.Label', background=self._current_colors['card'],
                       foreground=self._current_colors['text'])
        style.configure('Card.TFrame', background=self._current_colors['card'],
                       relief='flat', borderwidth=1)
        
        # Atualizar cores dos botões modernos
        for btn in self._modern_buttons:
            btn.update_colors(self._current_colors)

    def _toggle_theme(self):
        self._apply_theme(not self._dark_mode)
        icon = "☀️ Claro" if self._dark_mode else "🌙 Escuro"
        if hasattr(self, '_btn_theme'):
            self._btn_theme.config(text=icon)
        self._prefs["dark_mode"] = self._dark_mode
        self._save_prefs()
        logger.info("Tema alterado: %s", "escuro" if self._dark_mode else "claro")

    # ------------------------------------------------------------------
    # Preferências
    # ------------------------------------------------------------------

    def _load_prefs(self) -> dict:
        try:
            if PREFS_FILE.exists():
                return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_prefs(self):
        try:
            PREFS_FILE.write_text(
                json.dumps(self._prefs, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError as exc:
            logger.warning("Não foi possível salvar preferências: %s", exc)

    # ------------------------------------------------------------------
    # Auto-formatação e pré-visualização
    # ------------------------------------------------------------------

    def _setup_auto_format(self):
        self._expr_var.trace_add("write", self._on_expr_change)

    def _on_expr_change(self, *args):
        if self._placeholder_active:
            return
        current = self._expr_var.get()
        translation = str.maketrans({
            "×": "*",
            "÷": "/",
            "^": "**",
            "−": "-",
            "—": "-",
        })
        formatted = current.translate(translation)
        if formatted != current:
            self._expr_var.set(formatted)

    def _setup_live_preview(self):
        def on_type(*args):
            if self._placeholder_active:
                return
            if self._preview_timer:
                self.root.after_cancel(self._preview_timer)
            self._preview_timer = self.root.after(600, self._update_live_preview)
        self._expr_var.trace_add("write", on_type)

    def _update_live_preview(self):
        text = self._expr_var.get().strip()
        if text and not self._placeholder_active:
            result, _ = calculate_expression(text)
            if result is not None:
                self._lbl_preview.config(text=f"🔍 = {_format_number(result)}", 
                                        foreground=self._current_colors['success'])
            else:
                self._lbl_preview.config(text="", foreground="gray")
        else:
            self._lbl_preview.config(text="", foreground="gray")

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    def _show_onboarding(self):
        win = tk.Toplevel(self.root)
        win.title("Bem-vindo ao Arkymedes v5.0")
        win.geometry("600x580")
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        self.root.update_idletasks()
        rx = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - 580) // 2
        win.geometry(f"600x580+{rx}+{ry}")

        outer = ttk.Frame(win, padding="28")
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="🧮", font=("Segoe UI", 48)).pack(pady=(0, 6))
        ttk.Label(outer, text="Arkymedes v5.0", font=("Segoe UI", 20, "bold")).pack()
        ttk.Label(outer, text="Calculadora Inteligente com Interface Modernizada",
                  foreground="gray", font=("Segoe UI", 10)).pack(pady=(2, 20))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(0, 18))

        features = [
            ("🎨", "Interface Moderna", "Layout com sidebar, cards e design clean"),
            ("🔢", "Cálculos Seguros", "Motor AST sem risco de injeção de código"),
            ("📷", "OCR de Imagens/PDFs", "Arraste arquivos para processar"),
            ("📚", "Fórmulas Inteligentes", "Escreva 'área do círculo raio=5'"),
            ("⚡", "Pré-visualização", "Veja o resultado enquanto digita"),
            ("🎯", "Resultado em Destaque", "Fonte grande e feedback visual"),
        ]

        feats_frame = ttk.Frame(outer)
        feats_frame.pack(fill="x", pady=(0, 20))

        for icon, title, desc in features:
            row = ttk.Frame(feats_frame)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=icon, font=("Segoe UI", 18), width=3).pack(side="left", padx=(0, 12))
            text_col = ttk.Frame(row)
            text_col.pack(side="left", fill="x", expand=True)
            ttk.Label(text_col, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            ttk.Label(text_col, text=desc, foreground="gray",
                      font=("Segoe UI", 9), wraplength=430, justify="left").pack(anchor="w")

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(0, 16))

        footer = ttk.Frame(outer)
        footer.pack(fill="x")

        var_show = tk.BooleanVar(value=True)
        ttk.Checkbutton(footer, text="Mostrar isso ao abrir",
                        variable=var_show).pack(side="left")

        def _close():
            if not var_show.get():
                self._prefs["onboarding_done"] = True
                self._save_prefs()
            win.destroy()
            self._expr_entry.focus_set()

        ttk.Button(footer, text="Começar →", command=_close).pack(side="right")
        win.bind("<Return>", lambda _: _close())
        win.bind("<Escape>", lambda _: _close())

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def _setup_drag_and_drop(self, widget):
        if not HAS_DND:
            return
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        raw = event.data.strip()
        if raw.startswith("{"):
            path = raw[1:raw.index("}")]
        else:
            path = raw.split()[0]

        path = Path(path)
        ext = path.suffix.lower()

        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"):
            self._run_worker(ocr_text_from_image, f"📷 OCR: {path.name}…", "OCR", str(path))
        elif ext == ".pdf":
            self._run_worker(extract_text_from_pdf, f"📄 PDF: {path.name}…", "PDF", str(path))
        else:
            messagebox.showwarning("Formato não suportado", f"Arquivo '{path.name}' não é suportado.")

    # ------------------------------------------------------------------
    # Atalhos de teclado
    # ------------------------------------------------------------------

    def _setup_keyboard_shortcuts(self):
        self.root.bind("<Control-l>", lambda _: self._clear_input())
        self.root.bind("<Control-L>", lambda _: self._clear_input())
        self.root.bind("<Control-h>", lambda _: self._show_history_tab())
        self.root.bind("<Control-H>", lambda _: self._show_history_tab())
        self.root.bind("<Escape>",    lambda _: self._cancel_worker())
        self.root.bind("<F1>",        lambda _: self._show_onboarding())
        self.root.bind("<Control-Return>", lambda _: self._calculate_text())

    def _show_history_tab(self):
        if hasattr(self, '_notebook'):
            self._notebook.select(1)

    def _clear_input(self):
        self._expr_var.set("")
        self._placeholder_active = False
        self._setup_placeholder()

    # ------------------------------------------------------------------
    # Interface principal modernizada
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Constrói a interface modernizada com sidebar."""
        # Container principal
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Layout em grid (sidebar + conteúdo)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Sidebar
        self._build_sidebar(main_container)
        
        # Área principal (notebook)
        self._notebook = ttk.Notebook(main_container)
        self._notebook.grid(row=0, column=1, sticky="nsew")
        
        # Abas
        self._build_calc_tab()
        self._build_history_tab()
        
        if HAS_KB and self._kb:
            km = KnowledgeManager(self.root, self._kb)
            km.create_knowledge_tab(self._notebook)
        else:
            self._build_kb_unavailable_tab()
    
    def _build_sidebar(self, parent):
        """Cria a sidebar com fórmulas rápidas e ações."""
        sidebar = ttk.Frame(parent, width=280)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        sidebar.pack_propagate(False)
        
        # Logo e título
        logo_frame = ttk.Frame(sidebar)
        logo_frame.pack(fill="x", pady=(0, 20))
        
        logo_label = ttk.Label(logo_frame, text="🧮", font=("Segoe UI", 44))
        logo_label.pack()
        
        title_label = ttk.Label(logo_frame, text="Arkymedes", 
                                font=("Segoe UI", 18, "bold"))
        title_label.pack()
        
        version_label = ttk.Label(logo_frame, text=f"v{APP_VERSION} • Cálculo Inteligente",
                                  font=("Segoe UI", 9),
                                  foreground=self._current_colors['text_muted'])
        version_label.pack()
        
        # Separador
        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', pady=15)
        
        # Seção de fórmulas rápidas
        formulas_label = ttk.Label(sidebar, text="⚡ Fórmulas Rápidas",
                                   font=("Segoe UI", 11, "bold"))
        formulas_label.pack(anchor='w', pady=(0, 10))
        
        formulas = [
            ("🔵 Área Círculo", "area do circulo raio=5"),
            ("🟢 Volume Esfera", "volume da esfera r=3"),
            ("💰 Juros Compostos", "juros compostos p=1000 i=0.1 n=2"),
            ("📈 Juros Simples", "juros simples p=500 i=0.05 t=3"),
            ("📐 Pitágoras", "sqrt(3**2 + 4**2)"),
            ("📊 log10(1000)", "log10(1000)"),
            ("🧪 Seno", "sin(pi/2)"),
            ("🔢 Potência", "2**10"),
        ]
        
        for text, expr in formulas:
            btn = ModernButton(sidebar, text=text, accent=False,
                              command=lambda e=expr: self._set_expression(e))
            btn.pack(fill='x', pady=3)
            self._modern_buttons.append(btn)
            btn.update_colors(self._current_colors)
        
        # Separador
        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', pady=15)
        
        # Ações
        actions_label = ttk.Label(sidebar, text="🛠️ Ações",
                                  font=("Segoe UI", 11, "bold"))
        actions_label.pack(anchor='w', pady=(0, 10))
        
        # Botão de tema
        self._btn_theme = ModernButton(sidebar, text="🌙 Escuro", accent=False,
                                       command=self._toggle_theme)
        self._btn_theme.pack(fill='x', pady=3)
        self._modern_buttons.append(self._btn_theme)
        
        help_btn = ModernButton(sidebar, text="❓ Ajuda (F1)", accent=False,
                                command=self._show_onboarding)
        help_btn.pack(fill='x', pady=3)
        self._modern_buttons.append(help_btn)
        
        # Status na sidebar
        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', pady=15)
        
        self._sidebar_status = ttk.Label(sidebar, text="✅ Pronto",
                                         font=("Segoe UI", 9),
                                         foreground=self._current_colors['success'])
        self._sidebar_status.pack(anchor='w', pady=(5, 0))
    
    def _set_expression(self, expr):
        """Define expressão no campo de entrada."""
        self._expr_var.set(expr)
        self._placeholder_active = False
        self._expr_entry.config(foreground="")
        self._expr_entry.focus_set()
    
    def _build_calc_tab(self):
        """Constrói a aba de calculadora com design moderno."""
        tab = ttk.Frame(self._notebook, padding="15")
        self._notebook.add(tab, text="🧮 Calculadora")
        tab.columnconfigure(0, weight=1)
        
        # Card de entrada
        input_card = ttk.Frame(tab, style='Card.TFrame')
        input_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        input_card.columnconfigure(1, weight=1)
        
        # Título do card
        ttk.Label(input_card, text="📝 Nova Expressão",
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3,
                                                       sticky="w", padx=20, pady=(15, 10))
        
        # Campo de entrada
        ttk.Label(input_card, text="Expressão Matemática:",
                  font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 5))
        
        entry_frame = ttk.Frame(input_card)
        entry_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 10))
        entry_frame.columnconfigure(0, weight=1)
        
        self._expr_var = tk.StringVar()
        self._expr_entry = ttk.Entry(entry_frame, textvariable=self._expr_var,
                                     font=("Consolas", 13))
        self._expr_entry.pack(fill="x", ipady=8)
        self._expr_entry.bind("<Return>", lambda _: self._calculate_text())
        
        # Pré-visualização
        self._lbl_preview = ttk.Label(input_card, text="", foreground=self._current_colors['success'],
                                      font=("Segoe UI", 9, "italic"))
        self._lbl_preview.grid(row=3, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 10))
        
        # Botão calcular (destaque)
        calc_btn = ModernButton(input_card, text="= CALCULAR", accent=True,
                                command=self._calculate_text)
        calc_btn.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        self._modern_buttons.append(calc_btn)
        
        # Barra de ações
        action_bar = ttk.Frame(input_card)
        action_bar.grid(row=5, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 15))
        
        image_btn = ModernButton(action_bar, text="📷 OCR Imagem", accent=False,
                                 command=self._load_image)
        image_btn.pack(side='left', padx=(0, 5))
        self._modern_buttons.append(image_btn)
        
        pdf_btn = ModernButton(action_bar, text="📄 OCR PDF", accent=False,
                               command=self._load_pdf)
        pdf_btn.pack(side='left', padx=(0, 5))
        self._modern_buttons.append(pdf_btn)
        
        self._btn_cancel = ModernButton(action_bar, text="⛔ Cancelar", accent=False,
                                        command=self._cancel_worker)
        self._btn_cancel.pack(side='left')
        self._modern_buttons.append(self._btn_cancel)
        self._btn_cancel.config(state="disabled")
        
        # Drop zone
        drop_frame = ttk.LabelFrame(input_card, text="📂 Arraste um arquivo aqui", padding="10")
        drop_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 15))
        
        drop_label = ttk.Label(drop_frame, text="Solte uma imagem ou PDF para processar automaticamente",
                               font=("Segoe UI", 9), anchor="center")
        drop_label.pack(fill="x")
        
        if HAS_DND:
            self._setup_drag_and_drop(drop_frame)
            self._setup_drag_and_drop(drop_label)
        
        # Card de resultado
        self._build_result_card(tab)
        
        # Progresso
        prog_row = ttk.Frame(tab)
        prog_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        prog_row.columnconfigure(0, weight=1)
        
        self._progress = ttk.Progressbar(prog_row, mode="indeterminate")
        self._progress.grid(row=0, column=0, sticky="ew")
        
        self._status_var = tk.StringVar(value="Pronto")
        status_label = ttk.Label(prog_row, textvariable=self._status_var,
                                 foreground=self._current_colors['text_muted'],
                                 font=("Segoe UI", 9))
        status_label.grid(row=0, column=1, padx=8)
        
        # Placeholder
        self.root.after(100, self._setup_placeholder)
    
    def _build_result_card(self, parent):
        """Constrói o card de resultado em destaque."""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(1, weight=1)
        
        # Cabeçalho
        header_frame = ttk.Frame(card)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 10))
        
        ttk.Label(header_frame, text="✨ Resultado",
                  font=("Segoe UI", 12, "bold")).pack(side='left')
        
        self._lbl_fonte = ttk.Label(header_frame, text="",
                                    font=("Segoe UI", 9),
                                    foreground=self._current_colors['text_muted'])
        self._lbl_fonte.pack(side='right')
        
        self._lbl_status_icon = ttk.Label(header_frame, text="✅",
                                          foreground=self._current_colors['success'])
        self._lbl_status_icon.pack(side='right', padx=(0, 10))
        self._lbl_status_icon.pack_forget()
        
        # Área do resultado principal
        result_display = ttk.Frame(card, relief='solid', borderwidth=1)
        result_display.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        result_display.columnconfigure(0, weight=1)
        
        # Valor do resultado (grande)
        self._lbl_resultado = ttk.Label(result_display, text="—",
                                        font=("Segoe UI", 42, "bold"),
                                        foreground=self._current_colors['success'])
        self._lbl_resultado.pack(fill='x', pady=25, padx=20)
        
        # Entrada original
        entrada_frame = ttk.Frame(card)
        entrada_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 8))
        
        ttk.Label(entrada_frame, text="📝 Entrada:",
                  font=("Segoe UI", 9, "bold")).pack(anchor='w')
        
        self._lbl_entrada = ttk.Label(entrada_frame, text="",
                                      font=("Consolas", 10),
                                      foreground=self._current_colors['text_secondary'],
                                      wraplength=800, justify="left")
        self._lbl_entrada.pack(anchor='w', pady=(2, 0))
        
        # Descrição
        desc_frame = ttk.Frame(card)
        desc_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 12))
        
        ttk.Label(desc_frame, text="💡", font=("Segoe UI", 11)).pack(side='left', padx=(0, 6))
        
        self._lbl_descricao = ttk.Label(desc_frame, text="",
                                        font=("Segoe UI", 10),
                                        foreground=self._current_colors['text_muted'],
                                        wraplength=800, justify="left")
        self._lbl_descricao.pack(side='left', fill='x', expand=True)
        
        # Botões de ação
        actions_frame = ttk.Frame(card)
        actions_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 15))
        
        self._btn_copy = ModernButton(actions_frame, text="📋 Copiar resultado", accent=False,
                                      command=self._copy_result_with_feedback)
        self._btn_copy.pack(side='left', padx=(0, 8))
        self._modern_buttons.append(self._btn_copy)
        
        history_btn = ModernButton(actions_frame, text="📜 Ver histórico", accent=False,
                                   command=lambda: self._notebook.select(1))
        history_btn.pack(side='left')
        self._modern_buttons.append(history_btn)
    
    def _build_history_tab(self):
        """Constrói a aba de histórico."""
        tab = ttk.Frame(self._notebook, padding="15")
        self._notebook.add(tab, text="📋 Histórico")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        
        # Barra de ferramentas
        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        save_btn = ModernButton(toolbar, text="💾 Salvar", command=self._save_history_manual)
        save_btn.pack(side="left", padx=(0, 5))
        self._modern_buttons.append(save_btn)
        
        export_btn = ModernButton(toolbar, text="📤 Exportar CSV", command=self._export_csv)
        export_btn.pack(side="left", padx=(0, 5))
        self._modern_buttons.append(export_btn)
        
        clear_btn = ModernButton(toolbar, text="🗑️ Limpar", command=self._clear_history)
        clear_btn.pack(side="left")
        self._modern_buttons.append(clear_btn)
        
        # Busca
        search_row = ttk.Frame(tab)
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search_row.columnconfigure(1, weight=1)
        
        ttk.Label(search_row, text="🔍 Buscar:").grid(row=0, column=0, sticky="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_history())
        
        search_entry = ttk.Entry(search_row, textvariable=self._search_var, font=("Segoe UI", 10))
        search_entry.grid(row=0, column=1, sticky="ew", padx=8)
        
        # Treeview
        hist_frame = ttk.Frame(tab)
        hist_frame.grid(row=2, column=0, sticky="nsew")
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)
        
        cols = ("Entrada", "Resultado", "Fonte", "Data/Hora")
        self._tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=18)
        self._tree.column("Entrada", anchor="w", width=450)
        self._tree.column("Resultado", anchor="w", width=150)
        self._tree.column("Fonte", anchor="w", width=100)
        self._tree.column("Data/Hora", anchor="w", width=150)
        
        for col in cols:
            self._tree.heading(col, text=col)
        
        sb = ttk.Scrollbar(hist_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<Double-1>", self._copy_selected)
        
        ttk.Label(tab, text="💡 Dica: Duplo-clique copia o resultado",
                  font=("Segoe UI", 9), foreground=self._current_colors['text_muted']).grid(row=3, column=0, sticky="w", pady=8)
    
    def _build_kb_unavailable_tab(self):
        tab = ttk.Frame(self._notebook, padding="30")
        self._notebook.add(tab, text="📚 Conhecimento")
        ttk.Label(tab, text="📚 Base de Conhecimento", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))
        ttk.Label(tab, text="Dependências não instaladas.\n\nExecute:\npip install scikit-learn numpy",
                  font=("Segoe UI", 11), justify="center").pack(expand=True)
    
    # ------------------------------------------------------------------
    # Placeholder dinâmico
    # ------------------------------------------------------------------

    def _setup_placeholder(self):
        self._placeholder_idx = 0
        self._placeholder_active = True
        self._show_placeholder()
        self._expr_entry.bind("<FocusIn>", self._clear_placeholder)
        self._expr_entry.bind("<FocusOut>", self._restore_placeholder)

    def _show_placeholder(self):
        text = PLACEHOLDERS[self._placeholder_idx % len(PLACEHOLDERS)]
        self._expr_var.set(text)
        self._expr_entry.config(foreground="gray")
        self._placeholder_active = True
        self._placeholder_idx += 1
        self.root.after(3000, self._rotate_placeholder)

    def _rotate_placeholder(self):
        if self._placeholder_active:
            self._show_placeholder()

    def _clear_placeholder(self, _event=None):
        if self._placeholder_active:
            self._expr_var.set("")
            self._expr_entry.config(foreground="")
            self._placeholder_active = False

    def _restore_placeholder(self, _event=None):
        if not self._expr_var.get().strip():
            self._setup_placeholder()

    # ------------------------------------------------------------------
    # Ações principais
    # ------------------------------------------------------------------

    def _calculate_text(self):
        if self._placeholder_active:
            return
        text = self._expr_var.get().strip()
        if not text:
            return
        result, message = calculate_expression(text)
        self._show_result(text, result, message, source="Cálculo")

    def _load_image(self):
        path = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos", "*.*")])
        if path:
            self._run_worker(ocr_text_from_image, f"📷 OCR: {Path(path).name}...", "OCR", path)

    def _load_pdf(self):
        path = filedialog.askopenfilename(title="Selecionar PDF", filetypes=[("PDFs", "*.pdf"), ("Todos", "*.*")])
        if path:
            self._run_worker(extract_text_from_pdf, f"📄 PDF: {Path(path).name}...", "PDF", path)

    def _cancel_worker(self):
        if self._active_worker and self._active_worker.is_alive():
            self._active_worker.cancel()
            self._set_status("⛔ Operação cancelada", idle=True)

    def _copy_result_with_feedback(self):
        if self._last_result_value is not None:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(self._last_result_value))
            
            original_text = self._btn_copy.cget("text")
            self._btn_copy.config(text="✅ Copiado!")
            self.root.after(1500, lambda: self._btn_copy.config(text=original_text))
            
            self._lbl_status_icon.config(text="✅", foreground=self._current_colors['success'])
            self._lbl_status_icon.pack(side='right', padx=(0, 10))
            self.root.after(2000, lambda: self._lbl_status_icon.pack_forget())
            
            self._set_status("✅ Resultado copiado!", idle=True)

    def _copy_selected(self, _event=None):
        sel = self._tree.selection()
        if sel:
            val = self._tree.item(sel[0])["values"][1]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(val))
            self._set_status(f"✅ Copiado: {val}", idle=True)

    # ------------------------------------------------------------------
    # Threading
    # ------------------------------------------------------------------

    def _run_worker(self, task_fn, status_msg, source, path):
        if self._active_worker and self._active_worker.is_alive():
            messagebox.showwarning("Aviso", "Já existe uma operação em andamento.")
            return
        self._set_status(status_msg, idle=False)
        self._progress.start(10)
        queue = Queue()
        self._result_queue = queue
        worker = WorkerThread(task_fn, queue, path)
        self._active_worker = worker
        worker.start()
        self.root.after(self.POLL_INTERVAL, lambda: self._poll_result(source))

    def _poll_result(self, source):
        try:
            status, payload = self._result_queue.get_nowait()
        except Empty:
            self.root.after(self.POLL_INTERVAL, lambda: self._poll_result(source))
            return
        self._progress.stop()
        self._set_status("✅ Pronto", idle=True)

        if status == "cancelled":
            self._show_result("", None, "Operação cancelada pelo usuário.", source, is_error=True)
        elif status == "error":
            self._show_result("", None, f"Erro: {payload}", source, is_error=True)
            messagebox.showerror("Erro", f"Erro durante processamento:\n{payload}")
        else:
            text = payload or ""
            result, message = calculate_expression(text)
            self._show_result(text, result, message, source=source)

    # ------------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------------

    def _show_result(self, text_input, result, message, source, is_error=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._lbl_fonte.config(text=f"{source}  ·  {timestamp}")

        entrada_display = text_input[:180] + ("…" if len(text_input) > 180 else "")
        self._lbl_entrada.config(text=entrada_display if entrada_display else "—")

        if result is not None:
            formatted = _format_number(result)
            self._last_result_value = result
            self._lbl_resultado.config(text=formatted, foreground=self._current_colors['success'])
            self._lbl_descricao.config(text=message or "Cálculo realizado com sucesso.", 
                                       foreground=self._current_colors['text_secondary'])
            self._lbl_status_icon.config(text="✅", foreground=self._current_colors['success'])
            self._lbl_status_icon.pack(side='right', padx=(0, 10))
            
            self._add_to_history(HistoryEntry(text_input, str(result), source))
        else:
            self._last_result_value = None
            self._lbl_resultado.config(text="❌", foreground=self._current_colors['error'])
            self._lbl_descricao.config(text=message or "Não foi possível calcular.", 
                                       foreground=self._current_colors['error'])
            self._lbl_status_icon.config(text="❌", foreground=self._current_colors['error'])
            self._lbl_status_icon.pack(side='right', padx=(0, 10))

        self.root.after(2500, lambda: self._lbl_status_icon.pack_forget())

    # ------------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------------

    def _add_to_history(self, entry):
        self.history.append(entry)
        query = self._search_var.get().lower()
        if not query or query in entry.entrada.lower() or query in entry.resultado.lower():
            self._tree.insert("", "end",
                              values=(entry.entrada[:120], entry.resultado,
                                      entry.fonte, entry.timestamp))
        self._save_history()

    def _filter_history(self):
        query = self._search_var.get().lower()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for entry in self.history:
            if not query or query in entry.entrada.lower() or query in entry.resultado.lower():
                self._tree.insert("", "end",
                                  values=(entry.entrada[:120], entry.resultado,
                                          entry.fonte, entry.timestamp))

    def _rebuild_tree(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for entry in self.history:
            self._tree.insert("", "end",
                              values=(entry.entrada[:120], entry.resultado,
                                      entry.fonte, entry.timestamp))

    def _clear_history(self):
        if messagebox.askyesno("Confirmar", "Deseja limpar todo o histórico?"):
            self.history.clear()
            self._rebuild_tree()
            self._save_history()

    def _save_history(self):
        try:
            HISTORY_FILE.write_text(
                json.dumps([e.to_dict() for e in self.history],
                           ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError as exc:
            logger.error("Erro ao salvar histórico: %s", exc)

    def _save_history_manual(self):
        self._save_history()
        self._set_status(f"💾 Histórico salvo ({len(self.history)} entradas)", idle=True)

    def _load_history(self):
        if not HISTORY_FILE.exists():
            return
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            self.history = [HistoryEntry.from_dict(d) for d in data]
            self._rebuild_tree()
            logger.info("Histórico carregado: %d entradas.", len(self.history))
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("Não foi possível carregar histórico: %s", exc)

    def _export_csv(self):
        if not self.history:
            messagebox.showinfo("Aviso", "Histórico está vazio.")
            return
        path = filedialog.asksaveasfilename(
            title="Exportar histórico", defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialfile="historico_arkymedes.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Entrada", "Resultado", "Fonte", "Data/Hora"])
                for e in self.history:
                    writer.writerow([e.entrada, e.resultado, e.fonte, e.timestamp])
            self._set_status(f"📤 CSV exportado: {Path(path).name}", idle=True)
            messagebox.showinfo("Exportação concluída", f"Salvo em:\n{path}")
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível exportar:\n{exc}")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, msg, idle):
        self._status_var.set(msg)
        self._sidebar_status.config(text=msg)
        
        if idle:
            self._progress.stop()
            self._btn_cancel.config(state="disabled")
        else:
            self._btn_cancel.config(state="normal")

    # ------------------------------------------------------------------
    # Fechamento
    # ------------------------------------------------------------------

    def _on_close(self):
        self._save_history()
        self._save_prefs()
        logger.info("Aplicação encerrada.")
        self.root.destroy()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    ArkymedesGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()