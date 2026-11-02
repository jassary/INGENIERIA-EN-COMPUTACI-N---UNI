
import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


BG_MAIN = "#1e1e2f"      
BG_PANEL = "#2a2a40"     
BG_CARD = "#3b3b58"      
BORDER = "#4c4c70"      
FG_MAIN = "#ffffff"
FG_DIM = "#a9acc9"
COLOR_A = "#ff7a59"      
COLOR_B = "#4cc9f0"      
COLOR_EQ = "#ffd166"    

FONT = "Segoe UI"

SUBSTANCES = {
    "Agua":     (4186, "#3a8dde"),
    "Cobre":    (385,  "#c8742f"),
    "Aluminio": (900,  "#aab4c4"),
    "Hierro":   (449,  "#7d7f8c"),
    "Plata":    (235,  "#d9dde6"),
    "Vidrio":   (840,  "#6fd6c5"),
    "Etanol":   (2440, "#b48cf2"),
    "Aceite":   (2000, "#e0b341"),
}

K_COUPLING = 5.0        
MAX_MASS = 1000.0      
REAL_SECONDS = 12.0     
FRAME_MS = 40           
EQ_TOL = 0.1            


class ThermalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulación de equilibrio térmico")
        self.configure(bg=BG_MAIN)
        self.geometry("1180x820")
        self.minsize(1000, 740)

        
        self.t = 0.0            
        self.running = True
        self.tmax = 1.0
        self.tau = 1.0
        self.Tf = 0.0

        self._setup_styles()
        self._build_ui()
        self.recompute()        
        self._tick()            
    
    def _setup_styles(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("Dark.TCombobox", fieldbackground=BG_CARD,
                     background=BG_CARD, foreground=FG_MAIN,
                     arrowcolor=FG_MAIN, bordercolor=BORDER,
                     lightcolor=BG_CARD, darkcolor=BG_CARD,
                     selectbackground=BG_CARD, selectforeground=FG_MAIN)
        st.map("Dark.TCombobox",
               fieldbackground=[("readonly", BG_CARD)],
               foreground=[("readonly", FG_MAIN)],
               background=[("active", BORDER)])
       
        self.option_add("*TCombobox*Listbox.background", BG_CARD)
        self.option_add("*TCombobox*Listbox.foreground", FG_MAIN)
        self.option_add("*TCombobox*Listbox.selectBackground", COLOR_B)
        self.option_add("*TCombobox*Listbox.selectForeground", "#101020")

   
    def _panel(self, parent, **grid):
        """Contenedor con fondo de panel y borde sutil."""
        f = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER,
                     highlightthickness=1)
        f.grid(**grid)
        return f

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=5)   
        self.rowconfigure(1, weight=0)   
        self.rowconfigure(2, weight=0)   

       
        top = tk.Frame(self, bg=BG_MAIN)
        top.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 8))
        top.columnconfigure(0, weight=4, uniform="top")
        top.columnconfigure(1, weight=6, uniform="top")
        top.rowconfigure(0, weight=1)

        left = self._panel(top, row=0, column=0, sticky="nsew", padx=(0, 7))
        right = self._panel(top, row=0, column=1, sticky="nsew", padx=(7, 0))

    
        self.canvas = tk.Canvas(left, bg=BG_PANEL, highlightthickness=0,
                                width=440, height=360)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda e: self.draw_beakers())

        
        self.fig = Figure(figsize=(6, 3.6), dpi=100, facecolor=BG_PANEL)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.line_a, = self.ax.plot([], [], color=COLOR_A, lw=2.4, label="Sustancia A")
        self.line_b, = self.ax.plot([], [], color=COLOR_B, lw=2.4, label="Sustancia B")
        self.line_eq = self.ax.axhline(0, color=COLOR_EQ, ls="--", lw=1.6)
        self.eq_text = self.ax.text(0.98, 0.5, "", color=COLOR_EQ, fontsize=10,
                                    ha="right", va="bottom",
                                    transform=self.ax.get_yaxis_transform())
        self.cursor = self.ax.axvline(0, color="#ffffff", lw=0.8, alpha=0.35)
        self.dot_a, = self.ax.plot([], [], "o", color=COLOR_A, ms=7)
        self.dot_b, = self.ax.plot([], [], "o", color=COLOR_B, ms=7)
        leg = self.ax.legend(facecolor=BG_CARD, edgecolor=BORDER, labelcolor=FG_MAIN,
                             loc="center right", fontsize=9)
        leg.get_frame().set_alpha(0.9)
        self.fig.tight_layout(pad=1.5)
        self.mpl_canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.mpl_canvas.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
        self.mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        
        cards = tk.Frame(self, bg=BG_MAIN)
        cards.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        for i in range(3):
            cards.columnconfigure(i, weight=1, uniform="cards")
        self.card_tf = self._make_card(cards, 0, "TEMP. FINAL")
        self.card_dt = self._make_card(cards, 1, "DIFERENCIA ΔT")
        self.card_st = self._make_card(cards, 2, "TRANSCURRIDO / ESTADO")

      
        ctrl = self._panel(self, row=2, column=0, sticky="ew", padx=14, pady=(8, 14))
        ctrl.columnconfigure(0, weight=1, uniform="c")
        ctrl.columnconfigure(1, weight=1, uniform="c")

        self.var_sub_a = tk.StringVar(value="Agua")
        self.var_sub_b = tk.StringVar(value="Cobre")
        self.sc_ta = self._build_column(ctrl, 0, "SUSTANCIA A", COLOR_A, self.var_sub_a, 80.0, 400)
        self.sc_tb = self._build_column(ctrl, 1, "SUSTANCIA B", COLOR_B, self.var_sub_b, 25.0, 250)

       
        btns = tk.Frame(ctrl, bg=BG_PANEL)
        btns.grid(row=2, column=0, columnspan=2, pady=(2, 10))
        self.btn_pause = self._button(btns, "⏸  Pausa", self.toggle_run)
        self.btn_pause.pack(side="left", padx=6)
        self._button(btns, "↻  Reiniciar", self.restart).pack(side="left", padx=6)

    def _button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=BG_CARD, fg=FG_MAIN,
                         activebackground=BORDER, activeforeground=FG_MAIN,
                         relief="flat", bd=0, padx=16, pady=5,
                         font=(FONT, 10, "bold"), cursor="hand2")

    def _make_card(self, parent, col, title):
        """Tarjeta con título, valor grande y subtítulo."""
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="ew", padx=6)
        tk.Label(card, text=title, bg=BG_CARD, fg=FG_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 0))
        val = tk.Label(card, text="--", bg=BG_CARD, fg=FG_MAIN,
                       font=(FONT, 22, "bold"))
        val.pack(anchor="w", padx=14)
        sub = tk.Label(card, text="", bg=BG_CARD, fg=FG_DIM, font=(FONT, 9))
        sub.pack(anchor="w", padx=14, pady=(0, 10))
        return {"val": val, "sub": sub}

    def _build_column(self, parent, col, title, color, var_sub, t0, m0):
        """Columna de controles de una sustancia: combobox + 2 sliders."""
        box = tk.Frame(parent, bg=BG_PANEL)
        box.grid(row=0, column=col, sticky="nsew", padx=14, pady=10)
        box.columnconfigure(1, weight=1)

        tk.Label(box, text="●", bg=BG_PANEL, fg=color, font=(FONT, 14)
                 ).grid(row=0, column=0, sticky="w")
        tk.Label(box, text=title, bg=BG_PANEL, fg=FG_MAIN,
                 font=(FONT, 11, "bold")).grid(row=0, column=1, sticky="w")
        cb = ttk.Combobox(box, textvariable=var_sub, values=list(SUBSTANCES),
                          state="readonly", style="Dark.TCombobox", width=12)
        cb.grid(row=0, column=2, sticky="e")
        cb.bind("<<ComboboxSelected>>", lambda e: self.recompute())

        temp = self._slider(box, 1, "Temperatura inicial (°C)", 0, 100, 0.1, t0, color)
        mass = self._slider(box, 2, "Masa (g)", 50, MAX_MASS, 10, m0, color)
       
        if col == 0:
            self.sc_mass_a = mass
        else:
            self.sc_mass_b = mass
        return temp

    def _slider(self, parent, row, label, lo, hi, step, init, color):
        tk.Label(parent, text=label, bg=BG_PANEL, fg=FG_DIM, font=(FONT, 9)
                 ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        sc = tk.Scale(parent, from_=lo, to=hi, resolution=step, orient="horizontal",
                      bg=BG_PANEL, fg=FG_MAIN, troughcolor=BG_CARD,
                      activebackground=color, highlightthickness=0, bd=0,
                      sliderrelief="flat", length=200, font=(FONT, 9),
                      command=lambda v: self.recompute())
        sc.set(init)
        sc.grid(row=row, column=2, sticky="ew", pady=(2, 0))
        return sc

    def _style_axes(self):
        ax = self.ax
        ax.set_facecolor(BG_PANEL)
        for sp in ax.spines.values():
            sp.set_color(FG_MAIN)
        ax.tick_params(colors=FG_MAIN, labelsize=9)
        ax.set_xlabel("Tiempo (s)", color=FG_MAIN)
        ax.set_ylabel("Temperatura (°C)", color=FG_MAIN)
        ax.set_title("Evolución de la temperatura", color=FG_MAIN, fontsize=11)
        ax.grid(True, color=FG_MAIN, alpha=0.12, lw=0.6)

    
    def params(self):
        """Lee los controles y devuelve (TA0, TB0, CA, CB) con C en J/K."""
        ca = SUBSTANCES[self.var_sub_a.get()][0]
        cb = SUBSTANCES[self.var_sub_b.get()][0]
        ma = self.sc_mass_a.get() / 1000.0   # kg
        mb = self.sc_mass_b.get() / 1000.0
        return self.sc_ta.get(), self.sc_tb.get(), ma * ca, mb * cb

    def temps_at(self, t):
        """Temperaturas de A y B en el instante t (solución analítica)."""
        decay = np.exp(-np.asarray(t) / self.tau)
        return (self.Tf + (self.TA0 - self.Tf) * decay,
                self.Tf + (self.TB0 - self.Tf) * decay)

    def recompute(self):
        """Se llama al mover cualquier control: recalcula todo y reinicia t."""
        self.TA0, self.TB0, CA, CB = self.params()
        # Conservación de la energía: Q_perdido = Q_ganado
        self.Tf = (CA * self.TA0 + CB * self.TB0) / (CA + CB)
        self.tau = 1.0 / (K_COUPLING * (1.0 / CA + 1.0 / CB))
        self.tmax = 5.0 * self.tau          # ~99.3 % del equilibrio
        self.t = 0.0

        # Curvas completas
        ts = np.linspace(0, self.tmax, 300)
        ya, yb = self.temps_at(ts)
        self.line_a.set_data(ts, ya)
        self.line_b.set_data(ts, yb)
        self.line_eq.set_ydata([self.Tf, self.Tf])
        self.ax.set_xlim(0, self.tmax)
        lo, hi = min(self.TA0, self.TB0), max(self.TA0, self.TB0)
        pad = max(2.0, (hi - lo) * 0.12)
        self.ax.set_ylim(lo - pad, hi + pad)
        self.eq_text.set_text(f"Equilibrio: {self.Tf:.1f} °C")
        self.eq_text.set_y(self.Tf)
        self.line_a.set_label(f"A · {self.var_sub_a.get()}")
        self.line_b.set_label(f"B · {self.var_sub_b.get()}")
        self.ax.legend(facecolor=BG_CARD, edgecolor=BORDER, labelcolor=FG_MAIN,
                       loc="center right", fontsize=9)
        self.running = True
        self.btn_pause.config(text="⏸  Pausa")
        self.refresh_dynamic()

    
    def refresh_dynamic(self):
        """Actualiza todo lo que depende del tiempo actual."""
        ta, tb = self.temps_at(self.t)
        ta, tb = float(ta), float(tb)
        self.cur_a, self.cur_b = ta, tb

        self.card_tf["val"].config(text=f"{self.Tf:.1f} °C", fg=COLOR_EQ)
        self.card_tf["sub"].config(text="Q ganado = Q perdido")
        self.card_dt["val"].config(text=f"{abs(self.TA0 - self.TB0):.1f} °C")
        self.card_dt["sub"].config(text=f"Ahora: {abs(ta - tb):.1f} °C")
        in_eq = abs(ta - tb) < EQ_TOL
        if in_eq:
            self.card_st["val"].config(text="Equilibrio", fg="#6ee7a8")
        else:
            self.card_st["val"].config(text=f"{self.t:.0f} s", fg=FG_MAIN)
        self.card_st["sub"].config(
            text="Equilibrio térmico alcanzado" if in_eq else
            ("En curso…" if self.running else "En pausa"))

        self.cursor.set_xdata([self.t, self.t])
        self.dot_a.set_data([self.t], [ta])
        self.dot_b.set_data([self.t], [tb])
        self.mpl_canvas.draw_idle()

        self.draw_beakers()

    def draw_beakers(self):
        """Dibuja los dos vasos con nivel proporcional a la masa."""
        if not hasattr(self, "cur_a"):
            return
        c = self.canvas
        c.delete("all")
        W = max(c.winfo_width(), 300)
        H = max(c.winfo_height(), 260)

        bw = min(W * 0.30, 150)           
        top, bottom = H * 0.14, H * 0.82  
        bh = bottom - top

        data = [
            (W * 0.27, "A", self.var_sub_a.get(), self.sc_mass_a.get(), self.cur_a),
            (W * 0.73, "B", self.var_sub_b.get(), self.sc_mass_b.get(), self.cur_b),
        ]
        for cx, tag, name, mass, temp in data:
            x0, x1 = cx - bw / 2, cx + bw / 2
            color = SUBSTANCES[name][1]
            lvl = bh * (mass / MAX_MASS)          
            ytop = bottom - lvl

            
            c.create_rectangle(x0 + 3, ytop, x1 - 3, bottom - 2, fill=color,
                               outline="")
           
            c.create_line(x0 + 3, ytop, x1 - 3, ytop, fill="#ffffff", width=2)

            glass = "#c9cdea"
            c.create_line(x0, top, x0, bottom, x1 - 0, bottom, x1, top,
                          fill=glass, width=3, joinstyle="round")
            c.create_line(x0 - 8, top, x0 + 6, top, fill=glass, width=3)
            c.create_line(x1 - 6, top, x1 + 8, top, fill=glass, width=3)
        
            for k in range(1, 5):
                y = bottom - bh * k / 5
                c.create_line(x0, y, x0 + (14 if k % 2 else 9), y,
                              fill=glass, width=1)

            
            ty = min(bottom - lvl / 2, bottom - 20)
            ty = max(ty, top + 15)
            txt = f"{temp:.1f} °C"
            c.create_text(cx + 1, ty + 1, text=txt, fill="#000000",
                          font=(FONT, 15, "bold"))
            c.create_text(cx, ty, text=txt, fill=FG_MAIN, font=(FONT, 15, "bold"))

            # Etiquetas bajo el vaso
            c.create_text(cx, bottom + 22, text=f"Sustancia {tag}",
                          fill=FG_MAIN, font=(FONT, 11, "bold"))
            c.create_text(cx, bottom + 40, text=f"{name} · {mass:.0f} g",
                          fill=FG_DIM, font=(FONT, 9))

        mid = W / 2
        ay = top + bh * 0.45
        c.create_text(mid, ay - 14, text="calor", fill=FG_DIM, font=(FONT, 9, "italic"))
        c.create_line(mid - 24, ay, mid + 24, ay, fill=COLOR_EQ, width=2,
                      arrow="both", arrowshape=(10, 12, 4))


    def _tick(self):
        """Avanza el tiempo simulado de forma que todo dure REAL_SECONDS."""
        if self.running and self.t < self.tmax:
            self.t = min(self.tmax, self.t + self.tmax * FRAME_MS / 1000.0 / REAL_SECONDS)
            self.refresh_dynamic()
        self.after(FRAME_MS, self._tick)

    def toggle_run(self):
        self.running = not self.running
        self.btn_pause.config(text="⏸  Pausa" if self.running else "▶  Reanudar")
        self.refresh_dynamic()

    def restart(self):
        self.t = 0.0
        self.running = True
        self.btn_pause.config(text="⏸  Pausa")
        self.refresh_dynamic()


if __name__ == "__main__":
    ThermalApp().mainloop()
