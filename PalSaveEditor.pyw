# -*- coding: utf-8 -*-
"""Palworld - Editor de Save (versao Xbox/GDK).

Janela unica com menus: Inicio -> Itens / Personagem / Caixa de Pals / Breeding.
Le e grava o Level.sav de dentro dos containers WGS, com backup automatico.
"""
import os, sys, json, queue, random, shutil, threading, traceback, webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sv_ttk

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from palsave import wgs, palz, backup, meta, objetos, personagem, traducao, icones_rt, breeding
from palsave.level import LevelSave

WGS_DIR = os.path.expandvars(
    r"%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_ad4psfrxyesvt\SystemAppData\wgs")

# Dados do usuario (backups + config) ficam FORA da pasta do programa, para
# funcionar mesmo instalado e para nao sumir numa desinstalacao/atualizacao.
DADOS_USUARIO = os.path.join(os.environ.get("LOCALAPPDATA", BASE), "PalworldEditor")
os.makedirs(DADOS_USUARIO, exist_ok=True)
BACKUP_DIR = os.path.join(DADOS_USUARIO, "backups")
LIMITE = 99999
TODOS = "[ TODOS ]  ver tudo que existe no mundo"
GRUPOS = [("personagem", "Personagem"), ("guilda", "Guilda"),
          ("mundo", "Baus e estruturas"), ("pal", "Equipamento de Pal"),
          ("vazio", "Vazios")]

CONFIG = os.path.join(DADOS_USUARIO, "config.json")

# migra config/backup antigos (quando ficavam junto do programa) para a nova pasta
_CFG_ANTIGO = os.path.join(BASE, "config.json")
if not os.path.exists(CONFIG) and os.path.exists(_CFG_ANTIGO):
    try:
        shutil.copy2(_CFG_ANTIGO, CONFIG)
    except Exception:
        pass


def _ler_config():
    try:
        return json.load(open(CONFIG, encoding="utf-8"))
    except Exception:
        return {}


def _gravar_config(d):
    try:
        json.dump(d, open(CONFIG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


# ===========================================================================
class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Palworld - Editor de Save")
        self.geometry("1180x760")
        self.minsize(1000, 660)
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("disouz4dev.PalworldEditor")
        except Exception:
            pass
        try:
            self.iconbitmap(default=os.path.join(BASE, "assets", "logo.ico"))
        except Exception:
            pass

        # estado compartilhado
        self.root_wgs = None
        self.index = None
        self.bm = None
        self.level = None
        self.entry_atual = None
        self.meta_comp = None
        self.containers = []
        self.nomes = {}
        self.map_mundo = {}
        self.nome_mundo = {}
        self.pendentes = {}       # {guid: {sid: qtd}}  (itens, aplicados ao salvar)
        self.dirty = False        # edicoes de pal/personagem ja aplicadas ao level
        self.catalogo = self._carregar_catalogo()
        self.tela = None
        self.tela_nome = "inicio"
        self.fila = queue.Queue()
        self.cfg = _ler_config()
        self.tema = self.cfg.get("tema", "dark")

        self._estilo()
        self._shell()
        self.after(80, self._poll)
        self.after(200, self._iniciar)

    # ---------- infra ----------
    def _carregar_catalogo(self):
        try:
            return json.load(open(os.path.join(BASE, "items.json"), encoding="utf-8"))
        except Exception:
            return {"verificados": [], "derivados": []}

    def todos_ids(self):
        return self.catalogo["verificados"] + self.catalogo["derivados"]

    def _estilo(self):
        sv_ttk.set_theme(self.tema)
        st = ttk.Style(self)
        st.configure("Titulo.TLabel", font=("Segoe UI Variable Display", 22, "bold"))
        st.configure("Sub.TLabel", foreground="#8b93a7")
        st.configure("Menu.TButton", font=("Segoe UI", 13, "bold"), padding=14)
        st.configure("Treeview", rowheight=26)
        st.configure("Big.Treeview", rowheight=38)
        st.configure("Big.Treeview.Heading", font=("Segoe UI", 9, "bold"))
        st.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def cor_tag(self, qual):
        escuro = self.tema == "dark"
        if qual == "edit":
            return "#4d421e" if escuro else "#fff3cd"
        if qual == "todos":
            return "#33507a" if escuro else "#dbe8ff"
        return ""

    def paleta(self):
        if self.tema == "dark":
            return {"fundo": "#1c1c1c", "card": "#2b2b2b", "hover": "#383838",
                    "fg": "#e8e8e8", "sub": "#9aa0aa", "accent": "#57a6ff"}
        return {"fundo": "#fafafa", "card": "#ffffff", "hover": "#eef1f6",
                "fg": "#1a1a1a", "sub": "#5c6470", "accent": "#0d6efd"}

    def _toggle_tema(self):
        sv_ttk.toggle_theme()
        self.tema = sv_ttk.get_theme()
        self.cfg["tema"] = self.tema
        _gravar_config(self.cfg)
        self.btn_tema.configure(text=("Modo claro" if self.tema == "dark" else "Modo escuro"))
        if self.tela is not None and self.level is not None:
            self.mostrar(self.tela_nome)

    def _shell(self):
        topo = ttk.Frame(self, padding=(10, 8))
        topo.pack(fill="x")
        self.btn_inicio = ttk.Button(topo, text="‹ Inicio", command=lambda: self.mostrar("inicio"))
        self.btn_inicio.pack(side="left")
        ttk.Label(topo, text="   Mundo:").pack(side="left")
        self.cb_mundo = ttk.Combobox(topo, state="readonly", width=42)
        self.cb_mundo.pack(side="left", padx=6)
        self.cb_mundo.bind("<<ComboboxSelected>>", lambda e: self.carregar_mundo())
        ttk.Button(topo, text="Recarregar", command=self.carregar_mundo).pack(side="left")
        self.btn_salvar = ttk.Button(topo, text="SALVAR NO JOGO", style="Accent.TButton",
                                     command=self.salvar, state="disabled")
        self.btn_salvar.pack(side="right")
        self.pb = ttk.Progressbar(topo, mode="indeterminate", length=130)
        self.pb.pack(side="right", padx=8)
        self.btn_tema = ttk.Button(topo, text=("Modo claro" if self.tema == "dark" else "Modo escuro"),
                                   command=self._toggle_tema)
        self.btn_tema.pack(side="right", padx=8)

        self.conteudo = ttk.Frame(self)
        self.conteudo.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        rod = ttk.Frame(self, padding=(10, 4))
        rod.pack(fill="x")
        self.lbl_status = ttk.Label(rod, text="iniciando...")
        self.lbl_status.pack(side="left")

    def status(self, txt, cor=None):
        self.lbl_status.configure(text=txt, foreground=(cor or ""))
        self.update_idletasks()

    def _na_ui(self, fn, *a):
        self.fila.put((fn, a))

    def _poll(self):
        while True:
            try:
                fn, a = self.fila.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*a)
            except Exception:
                traceback.print_exc()
        self.after(80, self._poll)

    # ---------- navegacao ----------
    def mostrar(self, nome):
        if self.level is None and nome != "inicio":
            return
        if self.tela is not None:
            self.tela.destroy()
        classes = {"inicio": TelaInicio, "itens": TelaItens,
                   "personagem": TelaPersonagem, "pals": TelaPals, "breeding": TelaBreeding}
        self.tela_nome = nome
        self.tela = classes[nome](self.conteudo, self)
        self.tela.pack(fill="both", expand=True)
        self.btn_inicio.configure(state=("disabled" if nome == "inicio" else "normal"))

    # ---------- localizar a pasta do save ----------
    def _conta_salva(self):
        c = self.cfg.get("conta")
        if c and os.path.isfile(os.path.join(c, "containers.index")):
            return c
        return None

    def _descobrir_ou_perguntar(self):
        """Acha a pasta-conta do save (com containers.index). Ordem: escolha salva ->
        locais padrao (automatico) -> perguntar ao usuario e varrer subpastas.
        Retorna o caminho, ou None se o usuario desistir."""
        c = self._conta_salva()
        if c:
            return c
        self.status("procurando o save do Palworld...")
        c = wgs.descobrir_save()
        if c:
            self.cfg["conta"] = c; _gravar_config(self.cfg)
            return c
        while True:
            messagebox.showinfo(
                "Onde esta o save?",
                "Nao encontrei o save do Palworld automaticamente.\n\n"
                "Na proxima janela, aponte a PASTA DE INSTALACAO DO JOGO (ex.: "
                "E:\\Jogos\\Palworld) ou a pasta do save.\n\n"
                "Vou procurar nas subpastas ate achar o save (o arquivo containers.index).")
            d = filedialog.askdirectory(title="Selecione a pasta do Palworld ou do save")
            if not d:
                if messagebox.askretrycancel("Sem pasta", "Voce nao escolheu nenhuma pasta.\n\nTentar de novo?"):
                    continue
                return None
            self.status("procurando o save em %s ..." % d); self.update_idletasks()
            c = wgs.procurar_conta(d, max_prof=8) or wgs.descobrir_save()
            if c:
                self.cfg["conta"] = c; _gravar_config(self.cfg)
                return c
            if not messagebox.askretrycancel(
                    "Save nao encontrado",
                    "Nao achei o save (containers.index) dentro de:\n%s\n\n"
                    "A pasta do save geralmente fica em:\n"
                    "%%LOCALAPPDATA%%\\Packages\\PocketpairInc.Palworld_...\\SystemAppData\\wgs\n\n"
                    "Tentar outra pasta?" % d):
                return None

    def trocar_pasta_save(self):
        d = filedialog.askdirectory(title="Selecione a pasta do Palworld ou do save")
        if not d:
            return
        self.status("procurando o save em %s ..." % d); self.update_idletasks()
        c = wgs.procurar_conta(d, max_prof=8) or wgs.descobrir_save()
        if not c:
            messagebox.showerror("Save nao encontrado", "Nao achei containers.index nessa pasta.")
            return
        self.cfg["conta"] = c; _gravar_config(self.cfg)
        self.root_wgs = c; self.level = None
        self.status("save trocado, recarregando..."); self.pb.start(12)
        threading.Thread(target=self._iniciar_th, daemon=True).start()

    # ---------- carregar mundos (em segundo plano, sem travar a janela) ----------
    def _iniciar(self):
        conta = self._descobrir_ou_perguntar()
        if not conta:
            messagebox.showerror("Save nao encontrado",
                                 "Nao foi possivel localizar o save do Palworld.\n\nO editor sera fechado.")
            self.destroy(); return
        self.root_wgs = conta
        self.status("lendo os mundos do save...")
        self.pb.start(12)
        threading.Thread(target=self._iniciar_th, daemon=True).start()

    def _iniciar_th(self):
        try:
            self.bm = backup.BackupManager(self.root_wgs, BACKUP_DIR)
            self.index = wgs.parse_index(self.root_wgs)
            itens = list(wgs.worlds(self.index).items())
            opcoes, map_mundo, nome_mundo = [], {}, {}
            for i, (wid, partes) in enumerate(itens):
                lvl = partes.get("Level-01") or partes.get("Level")
                if not lvl:
                    continue
                self._na_ui(self.status, "verificando mundos (%d/%d)..." % (i + 1, len(itens)))
                try:
                    _, raw = wgs.read_blob(self.root_wgs, lvl); palz.decompress(raw)
                except Exception:
                    continue
                info = {"mundo": None, "jogador": None}
                lm = partes.get("LevelMeta")
                if lm:
                    try:
                        info = meta.ler_meta(wgs.read_blob(self.root_wgs, lm)[1])
                    except Exception:
                        pass
                nome = info["mundo"] or ("mundo " + wid[:8])
                rot = "%s  (%s%.1f MB)" % (nome, (info["jogador"] + " - ") if info["jogador"] else "",
                                           lvl["size"] / 1048576.0)
                if rot in map_mundo:
                    rot += "  [%s]" % wid[:8]
                opcoes.append(rot); map_mundo[rot] = lvl; nome_mundo[rot] = nome
            if not opcoes:
                self._na_ui(self._iniciar_falhou, "Nenhum mundo com Level.sav legivel.")
                return
            opcoes.sort(key=lambda r: -map_mundo[r]["size"])
            self._na_ui(self._iniciar_pronto, opcoes, map_mundo, nome_mundo)
        except Exception:
            self._na_ui(self._iniciar_falhou, traceback.format_exc()[-1500:])

    def _iniciar_falhou(self, msg):
        self.pb.stop(); self.status("falha ao abrir o save", "#ff8080")
        messagebox.showerror("Nada para editar", msg)
        self.destroy()

    def _iniciar_pronto(self, opcoes, map_mundo, nome_mundo):
        self.map_mundo = map_mundo; self.nome_mundo = nome_mundo
        self.cb_mundo["values"] = opcoes
        self.cb_mundo.current(0)
        self.status("fazendo backup do save original...")
        threading.Thread(target=self._bkp_ini, daemon=True).start()

    def _bkp_ini(self):
        try:
            self.bm.ensure_original()
        except Exception:
            pass
        self._na_ui(self.carregar_mundo)

    def carregar_mundo(self):
        rot = self.cb_mundo.get()
        if not rot:
            return
        self.entry_atual = self.map_mundo[rot]
        self.pendentes.clear(); self.dirty = False
        self.btn_salvar.configure(state="disabled")
        self.pb.start(12); self.status("lendo e descomprimindo o save...")
        threading.Thread(target=self._carregar_th, daemon=True).start()

    def _carregar_th(self):
        try:
            _, raw = wgs.read_blob(self.root_wgs, self.entry_atual)
            data, self.meta_comp = palz.decompress(raw)
            lv = LevelSave.from_bytes(data)
            nomes = objetos.mapear(lv)
            self._na_ui(self._carregado, lv, nomes)
        except Exception:
            self._na_ui(self._erro, "Falha ao ler o save", traceback.format_exc())

    def _carregado(self, lv, nomes):
        self.level = lv; self.nomes = nomes
        self.containers = sorted(lv.containers,
                                 key=lambda c: (objetos.ORDEM.get(nomes[c.guid][1], 9), -len(c.slots)))
        self.pb.stop()
        self.btn_salvar.configure(state="normal")
        nome = self.nome_mundo.get(self.cb_mundo.get(), "")
        self.title("Palworld - Editor de Save - %s" % nome)
        self.status('"%s" carregado.' % nome, "#7fe0a0")
        self.mostrar("inicio")

    def _erro(self, titulo, tb):
        self.pb.stop(); self.status(titulo, "#ff8080")
        messagebox.showerror(titulo, tb[-1500:])

    # ---------- salvar ----------
    def marcar_sujo(self):
        self.dirty = True

    def n_pendencias(self):
        return sum(len(v) for v in self.pendentes.values())

    def salvar(self):
        if not self.n_pendencias() and not self.dirty:
            messagebox.showinfo("Nada a fazer", "Nenhuma alteracao pendente.")
            return
        if not messagebox.askyesno("Salvar",
                                   "Gravar as alteracoes no save?\n\nO JOGO PRECISA ESTAR FECHADO.\n"
                                   "Um backup e feito automaticamente antes."):
            return
        self.btn_salvar.configure(state="disabled"); self.pb.start(12); self.status("salvando...")
        threading.Thread(target=self._salvar_th, daemon=True).start()

    def _salvar_th(self):
        try:
            self.bm.create("antes de editar")
            porg = {c.guid: c for c in self.level.containers}
            for guid, itens in self.pendentes.items():
                c = porg.get(guid)
                if not c:
                    continue
                cap = max(42, len(c.slots))
                for sid, q in itens.items():
                    self.level.set_quantity(c, sid, q, capacity=cap)
            blob = palz.compress(self.level.to_bytes(), self.meta_comp)
            wgs.write_blob(self.root_wgs, self.index, self.entry_atual, blob)
            self._na_ui(self._salvo)
        except Exception:
            self._na_ui(self._erro, "Falha ao salvar", traceback.format_exc())

    def _salvo(self):
        self.pb.stop(); self.btn_salvar.configure(state="normal")
        self.status("salvo com sucesso!", "#7fe0a0")
        messagebox.showinfo("Pronto", "Alteracoes gravadas.\n\nSe algo der errado no jogo, "
                                       "use Inicio > Backups > Restaurar.")
        self.carregar_mundo()

    # ---------- backups ----------
    def criar_backup(self):
        try:
            self.bm.create("manual"); messagebox.showinfo("Backup", "Backup criado.")
        except Exception as ex:
            messagebox.showerror("Erro", str(ex))

    def abrir_pasta_backup(self):
        os.makedirs(BACKUP_DIR, exist_ok=True); webbrowser.open(BACKUP_DIR)

    # ---------- atualizacao (GitHub) ----------
    def verificar_atualizacao(self):
        self.status("verificando atualizacoes no GitHub...")
        self.pb.start(12)
        threading.Thread(target=self._verificar_th, daemon=True).start()

    def _verificar_th(self):
        from palsave import atualizacao
        self._na_ui(self._verificado, atualizacao.verificar())

    def _verificado(self, res):
        self.pb.stop()
        if not res.get("ok"):
            self.status("nao foi possivel verificar", "#ff8080")
            messagebox.showwarning("Atualizacao",
                                   "Nao consegui verificar agora (sem internet?).\n\n%s"
                                   % res.get("erro", ""))
            return
        if not res["tem_update"]:
            self.status("voce ja esta na versao mais recente (%s)" % res["local"], "#7fe0a0")
            messagebox.showinfo("Atualizacao",
                                "Voce ja esta na versao mais recente.\n\nVersao instalada: %s"
                                % res["local"])
            return
        self.status("atualizacao disponivel: %s" % res["remota"], "#57a6ff")
        notas = ("\n\nNovidades: " + res["notas"]) if res.get("notas") else ""
        if messagebox.askyesno("Atualizacao disponivel",
                               "Ha uma versao nova!\n\nInstalada: %s\nNova: %s%s\n\n"
                               "Baixar e instalar agora?\n\n(Ao terminar o editor fecha; seus "
                               "backups e configuracoes sao mantidos.)"
                               % (res["local"], res["remota"], notas)):
            self._instalar_update()

    def _instalar_update(self):
        self.status("instalando atualizacao...")
        self.pb.start(12)
        threading.Thread(target=self._instalar_th, daemon=True).start()

    def _instalar_th(self):
        from palsave import atualizacao
        ok, msg = atualizacao.instalar(log=lambda m: self._na_ui(self.status, m))
        self._na_ui(self._instalado, ok, msg)

    def _instalado(self, ok, msg):
        self.pb.stop()
        if ok:
            self.status("atualizado! reabra o editor.", "#7fe0a0")
            messagebox.showinfo("Pronto",
                                "Atualizacao instalada.\n\n%s\n\nO editor vai fechar agora. "
                                "Abra de novo pelo atalho." % msg)
            self.destroy()
        else:
            self.status("falha na atualizacao", "#ff8080")
            messagebox.showerror("Atualizacao", msg)


# ===========================================================================
class Tela(ttk.Frame):
    """Base das telas."""
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app


# ---------------------------------------------------------------------------
class TelaInicio(Tela):
    MENUS = [
        ("\U0001F4E6", "Itens", "Inventario, baus, dinheiro e adicionar\no que voce nao tem", "itens"),
        ("\U0001F9CD", "Personagem", "Nivel, experiencia e pontos\nde atributo", "personagem"),
        ("\U0001F43E", "Caixa de Pals", "Nivel, sexo, IVs e passivas\ndos seus Pals", "pals"),
        ("\U0001F95A", "Breeding", "Descobrir e montar os pares\npara o filho que voce quer", "breeding"),
    ]

    def __init__(self, master, app):
        Tela.__init__(self, master, app)
        wrap = ttk.Frame(self); wrap.place(relx=0.5, rely=0.44, anchor="center")
        nome = app.nome_mundo.get(app.cb_mundo.get(), "")
        ttk.Label(wrap, text="O que voce quer editar?", style="Titulo.TLabel").pack()
        ttk.Label(wrap, text="Mundo: %s" % nome, style="Sub.TLabel").pack(pady=(2, 22))

        grade = ttk.Frame(wrap); grade.pack()
        for c in (0, 1):
            grade.columnconfigure(c, weight=1, uniform="col")
        for i, (icone, tit, sub, destino) in enumerate(self.MENUS):
            self._card(grade, i // 2, i % 2, icone, tit, sub, destino)

        bar = ttk.Frame(wrap); bar.pack(pady=(24, 0))
        ttk.Button(bar, text="Criar backup", command=app.criar_backup).pack(side="left", padx=4)
        ttk.Button(bar, text="Restaurar backup...",
                   command=lambda: JanelaRestaurar(app)).pack(side="left", padx=4)
        ttk.Button(bar, text="Pasta de backups", command=app.abrir_pasta_backup).pack(side="left", padx=4)
        ttk.Button(bar, text="Trocar pasta do save...",
                   command=app.trocar_pasta_save).pack(side="left", padx=4)

        from palsave import atualizacao
        bar2 = ttk.Frame(wrap); bar2.pack(pady=(12, 0))
        ttk.Label(bar2, text="Versao %s" % atualizacao.versao_local(),
                  style="Sub.TLabel").pack(side="left", padx=(0, 10))
        ttk.Button(bar2, text="Verificar atualizacao",
                   command=app.verificar_atualizacao).pack(side="left")

    def _card(self, grade, r, c, icone, tit, sub, destino):
        pal = self.app.paleta()
        card = tk.Frame(grade, bg=pal["card"], highlightbackground=pal["hover"],
                        highlightthickness=1, bd=0)
        card.grid(row=r, column=c, padx=12, pady=12, sticky="nsew", ipadx=28, ipady=20)
        ic = tk.Label(card, text=icone, font=("Segoe UI Emoji", 42), bg=pal["card"], fg=pal["fg"])
        ic.pack(pady=(4, 0))
        t = tk.Label(card, text=tit, font=("Segoe UI Variable Display", 16, "bold"),
                     bg=pal["card"], fg=pal["fg"])
        t.pack(pady=(6, 2))
        s = tk.Label(card, text=sub, justify="center", font=("Segoe UI", 9),
                     bg=pal["card"], fg=pal["sub"])
        s.pack()
        alvos = [card, ic, t, s]

        def entra(_e):
            for w in alvos:
                w.configure(bg=pal["hover"])
            card.configure(highlightbackground=pal["accent"])

        def sai(_e):
            for w in alvos:
                w.configure(bg=pal["card"])
            card.configure(highlightbackground=pal["hover"])

        for w in alvos:
            w.bind("<Button-1>", lambda e, d=destino: self.app.mostrar(d))
            w.bind("<Enter>", entra)
            w.bind("<Leave>", sai)
            try:
                w.configure(cursor="hand2")
            except tk.TclError:
                pass


# ---------------------------------------------------------------------------
class TelaItens(Tela):
    def __init__(self, master, app):
        Tela.__init__(self, master, app)
        self.container = None
        self.map_cont = {}
        self.map_item = {}

        cab = ttk.Frame(self); cab.pack(fill="x", pady=(0, 6))
        ttk.Label(cab, text="Itens", style="Titulo.TLabel").pack(side="left")

        corpo = ttk.Panedwindow(self, orient="horizontal"); corpo.pack(fill="both", expand=True)

        esq = ttk.Labelframe(corpo, text="Onde", padding=6); corpo.add(esq, weight=1)
        f1 = ttk.Frame(esq); f1.pack(fill="x")
        ttk.Label(f1, text="Filtrar:").pack(side="left")
        self.var_fc = tk.StringVar(); self.var_fc.trace_add("write", lambda *a: self.render_cont())
        ttk.Entry(f1, textvariable=self.var_fc).pack(side="left", fill="x", expand=True, padx=4)
        self.var_vazios = tk.BooleanVar(value=False)
        ttk.Checkbutton(esq, text="mostrar vazios", variable=self.var_vazios,
                        command=self.render_cont).pack(anchor="w", pady=2)
        self.lst = ttk.Treeview(esq, columns=("n",), show="tree headings", height=22)
        self.lst.heading("#0", text="Container"); self.lst.heading("n", text="Itens")
        self.lst.column("#0", width=330); self.lst.column("n", width=48, anchor="e", stretch=False)
        s1 = ttk.Scrollbar(esq, orient="vertical", command=self.lst.yview)
        self.lst.configure(yscrollcommand=s1.set); s1.pack(side="right", fill="y")
        self.lst.pack(fill="both", expand=True, pady=4)
        self.lst.bind("<<TreeviewSelect>>", self.sel_cont)
        self.lst.tag_configure("grupo", font=("Segoe UI", 9, "bold"))
        self.lst.tag_configure("todos", background=app.cor_tag("todos"))

        dir_ = ttk.Labelframe(corpo, text="Itens", padding=6); corpo.add(dir_, weight=2)
        f2 = ttk.Frame(dir_); f2.pack(fill="x")
        ttk.Label(f2, text="Buscar:").pack(side="left")
        self.var_b = tk.StringVar(); self.var_b.trace_add("write", lambda *a: self.render_item())
        e = ttk.Entry(f2, textvariable=self.var_b, font=("Segoe UI", 11))
        e.pack(side="left", fill="x", expand=True, padx=4); e.focus_set()

        self.tv = ttk.Treeview(dir_, columns=("qtd", "novo", "onde"), show="tree headings",
                               style="Big.Treeview")
        for c, t, w in [("#0", "Item", 300), ("qtd", "Tem", 80), ("novo", "Vai virar", 80), ("onde", "Onde", 220)]:
            self.tv.heading(c, text=t); self.tv.column(c, width=w, anchor=("e" if c in ("qtd", "novo") else "w"),
                                                       stretch=(c == "onde"))
        s2 = ttk.Scrollbar(dir_, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=s2.set); s2.pack(side="right", fill="y")
        self.tv.pack(fill="both", expand=True, pady=4)
        self.tv.tag_configure("edit", background=app.cor_tag("edit"))
        self.tv.bind("<Double-1>", lambda e: self.aplicar())

        f3 = ttk.Frame(dir_); f3.pack(fill="x", pady=4)
        ttk.Label(f3, text="Quantidade:").pack(side="left")
        self.var_q = tk.StringVar(value="")
        ttk.Entry(f3, textvariable=self.var_q, width=9).pack(side="left", padx=4)
        self.b_ap = ttk.Button(f3, text="Aplicar ao selecionado", command=self.aplicar); self.b_ap.pack(side="left")
        self.b_todos = ttk.Button(f3, text="Aplicar a todos da lista", command=self.aplicar_todos)
        self.b_todos.pack(side="left", padx=4)
        ttk.Button(f3, text="Desfazer", command=self.desfazer).pack(side="left")
        ttk.Button(f3, text="+ Adicionar item que nao tenho", command=self.adicionar).pack(side="left", padx=8)
        self.lbl_alvo = ttk.Label(dir_, text="", style="Sub.TLabel"); self.lbl_alvo.pack(anchor="w")

        self.render_cont(); self._sel_padrao(); self.render_item()

    def _sel_padrao(self):
        """Ja seleciona o inventario principal para dar pra editar sem entrar no modo TODOS."""
        alvo = next((c for c in self.app.containers
                     if self.app.nomes[c.guid][0].startswith("Personagem: INVENTARIO")), None)
        if alvo is None:
            alvo = next((c for c in self.app.containers if self.app.nomes[c.guid][1] == "guilda"), None)
        if alvo is None:
            return
        for iid, c in self.map_cont.items():
            if c is alvo:
                self.lst.selection_set(iid); self.lst.see(iid)
                self.container = alvo
                return

    def pend(self, c=None):
        c = c or self.container
        return self.app.pendentes.setdefault(c.guid, {}) if c else {}

    def render_cont(self):
        for i in self.lst.get_children():
            self.lst.delete(i)
        f = self.var_fc.get().strip().lower(); self.map_cont = {}
        iid = self.lst.insert("", "end", text=TODOS, values=("",), tags=("todos",)); self.map_cont[iid] = None
        porg = {}
        for c in self.app.containers:
            rot, cat = self.app.nomes[c.guid]
            if cat == "vazio" and not self.var_vazios.get():
                continue
            if f and f not in rot.lower() and not any(f in traducao.nome_item(i).lower() or f in i.lower() for i in c.items):
                continue
            porg.setdefault(cat, []).append((c, rot))
        for cat, tit in GRUPOS:
            grp = porg.get(cat)
            if not grp:
                continue
            pai = self.lst.insert("", "end", text="%s  (%d)" % (tit, len(grp)), values=("",),
                                  tags=("grupo",), open=cat in ("personagem", "guilda"))
            for c, rot in grp[:600]:
                self.map_cont[self.lst.insert(pai, "end", text=rot, values=(len(c.slots),))] = c

    def sel_cont(self, _e=None):
        s = self.lst.selection()
        if not s or s[0] not in self.map_cont:
            return
        self.container = self.map_cont[s[0]]; self.render_item()

    def render_item(self):
        for i in self.tv.get_children():
            self.tv.delete(i)
        b = self.var_b.get().strip().lower(); self.map_item = {}
        todos = self.container is None
        self.b_ap.configure(state="normal")
        self.b_todos.configure(state=("disabled" if todos else "normal"))
        verif = set(self.app.catalogo["verificados"])
        if todos:
            self.tv.heading("onde", text="Em quantos lugares")
            self.lbl_alvo.configure(text="Selecione um item e clique Aplicar: vai para o inventario principal do personagem.")
            tot, loc = {}, {}
            for c in self.app.level.containers:
                nc = self.app.nomes[c.guid][0]
                for sid, q in c.items.items():
                    tot[sid] = tot.get(sid, 0) + q; loc.setdefault(sid, []).append(nc)
            for sid in sorted(tot, key=lambda s: -tot[s]):
                nome = traducao.nome_item(sid)
                if b and b not in sid.lower() and b not in nome.lower():
                    continue
                rot = nome if nome == sid else "%s  (%s)" % (nome, sid)
                ico = icones_rt.item(sid)
                kw = {"image": ico} if ico else {}
                self.map_item[self.tv.insert("", "end", text=" " + rot,
                             values=(tot[sid], "", "%d lugar(es)" % len(loc[sid])), **kw)] = sid
            self.app.status("modo TODOS: %d itens diferentes no mundo" % len(tot))
            return
        self.tv.heading("onde", text="Origem")
        self.lbl_alvo.configure(text="Alvo: %s  -  busque para adicionar itens que voce nao tem"
                                     % self.app.nomes[self.container.guid][0])
        at = self.container.items; pd = self.pend()
        chaves = set(at) | set(pd)
        if b:                                   # buscando: mostra tambem itens do catalogo para adicionar
            for sid in self.app.todos_ids():
                nome = traducao.nome_item(sid)
                if b in sid.lower() or b in nome.lower():
                    chaves.add(sid)
        n = 0
        for sid in sorted(chaves, key=lambda s: (s not in at and s not in pd, traducao.nome_item(s).lower())):
            nome = traducao.nome_item(sid)
            if b and b not in sid.lower() and b not in nome.lower():
                continue
            rot = nome if nome == sid else "%s  (%s)" % (nome, sid)
            ico = icones_rt.item(sid)
            kw = {"image": ico} if ico else {}
            self.map_item[self.tv.insert("", "end", text=" " + rot,
                         values=(at.get(sid, 0), pd.get(sid, ""),
                                 "confirmado" if sid in verif else "arquivos"),
                         tags=("edit",) if sid in pd else (), **kw)] = sid
            n += 1
            if n >= 800:
                break

    def _q(self):
        try:
            v = int(self.var_q.get())
        except ValueError:
            messagebox.showwarning("Invalido", "Digite um numero."); return None
        v = max(0, min(v, LIMITE)); self.var_q.set(str(v)); return v

    def _inv_principal(self):
        return next((c for c in self.app.containers
                     if self.app.nomes[c.guid][0].startswith("Personagem: INVENTARIO")), None) \
            or next((c for c in self.app.containers if self.app.nomes[c.guid][1] == "guilda"), None)

    def aplicar(self):
        alvo = self.container or self._inv_principal()
        if alvo is None:
            messagebox.showinfo("Escolha", "Selecione um container para editar."); return
        s = self.tv.selection()
        if not s:
            messagebox.showinfo("Selecione", "Escolha um item na lista primeiro."); return
        v = self._q()
        if v is None:
            return
        d = self.app.pendentes.setdefault(alvo.guid, {})
        for i in s:
            d[self.map_item[i]] = v
        if self.container is None:            # estava no modo TODOS: passa a mostrar o inventario
            self.container = alvo
            self.render_cont()
        self.render_item(); self.app.status("%d alteracao(oes) pendente(s)" % self.app.n_pendencias(), "#e0c060")

    def aplicar_todos(self):
        if self.container is None:
            return
        its = list(self.map_item.values())
        if not its or self._q() is None:
            return
        if not messagebox.askyesno("Confirmar", "Definir %d itens para %d?" % (len(its), self._q())):
            return
        for sid in its:
            self.pend()[sid] = self._q()
        self.render_item()

    def desfazer(self):
        self.app.pendentes.clear(); self.render_item(); self.app.status("alteracoes de item descartadas")

    def adicionar(self):
        alvo = self.container
        if alvo is None:
            alvo = next((c for c in self.app.containers
                         if self.app.nomes[c.guid][0].startswith("Personagem: INVENTARIO")), None)
        if alvo is None:
            messagebox.showinfo("Escolha", "Selecione onde adicionar."); return
        JanelaAdicionar(self.app, self, alvo)


# ---------------------------------------------------------------------------
class TelaPersonagem(Tela):
    def __init__(self, master, app):
        Tela.__init__(self, master, app)
        ttk.Label(self, text="Personagem", style="Titulo.TLabel").pack(anchor="w", pady=(0, 8))
        try:
            js = personagem.jogadores(app.level)
        except Exception:
            js = []
        if not js:
            ttk.Label(self, text="Nao encontrei o personagem neste save.").pack(); return
        self.p = js[0]
        top = ttk.Frame(self); top.pack(fill="x", pady=6)
        ttk.Label(top, text=self.p.apelido or "(sem nome)", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w")
        self.v_nivel = tk.StringVar(value=str(self._n(self.p.nivel)))
        self.v_exp = tk.StringVar(value=str(self._n(self.p.exp)))
        self.v_livres = tk.StringVar(value=str(self._n(self.p.pontos_livres)))
        for c, (rot, var) in enumerate([("Nivel", self.v_nivel), ("Experiencia", self.v_exp),
                                        ("Pontos nao gastos", self.v_livres)]):
            ttk.Label(top, text=rot + ":").grid(row=1, column=c * 2, sticky="e", padx=(0, 4), pady=6)
            ttk.Entry(top, textvariable=var, width=12).grid(row=1, column=c * 2 + 1, sticky="w", padx=(0, 14))

        ttk.Label(self, text="Pontos por atributo (duplo clique aplica o valor abaixo):",
                  style="Sub.TLabel").pack(anchor="w", pady=(8, 2))
        self.tv = ttk.Treeview(self, columns=("pts",), show="tree headings", height=16)
        self.tv.heading("#0", text="Atributo"); self.tv.heading("pts", text="Pontos")
        self.tv.column("#0", width=340); self.tv.column("pts", width=90, anchor="e", stretch=False)
        self.tv.pack(fill="both", expand=True, pady=4)
        self.tv.bind("<Double-1>", self.editar)
        self.mapa = {}
        for lista, rot, pts, no in self.p.status():
            self.mapa[self.tv.insert("", "end", text=rot, values=(pts,))] = no

        f = ttk.Frame(self); f.pack(fill="x", pady=6)
        ttk.Label(f, text="Novo valor:").pack(side="left")
        self.v_val = tk.StringVar(value="50")
        ttk.Entry(f, textvariable=self.v_val, width=8).pack(side="left", padx=4)
        ttk.Button(f, text="Aplicar ao selecionado", command=self.editar).pack(side="left")
        ttk.Button(f, text="Guardar alteracoes do personagem", command=self.guardar).pack(side="right")

    @staticmethod
    def _n(v):
        return v.get("value", 0) if isinstance(v, dict) else (v or 0)

    def editar(self, _e=None):
        s = self.tv.selection()
        if not s:
            return
        try:
            v = int(self.v_val.get())
        except ValueError:
            messagebox.showwarning("Invalido", "Digite um numero."); return
        for i in s:
            personagem.Personagem.set_status(self.mapa[i], v); self.tv.set(i, "pts", v)

    def guardar(self):
        try:
            self.p.set_nivel(int(self.v_nivel.get())); self.p.set_exp(int(self.v_exp.get()))
            self.p.set_pontos_livres(int(self.v_livres.get())); self.p.gravar()
        except Exception as ex:
            messagebox.showerror("Erro", str(ex)); return
        self.app.marcar_sujo(); self.app.status("personagem alterado - clique em SALVAR NO JOGO", "#e0c060")
        messagebox.showinfo("Guardado", "Alteracoes preparadas. Clique em SALVAR NO JOGO.")


# ---------------------------------------------------------------------------
class TelaPals(Tela):
    PRESETS = {
        "Combate (dano)": (["Legend", "PAL_ALLAttack_up3", "Noukin", "MoveSpeed_up_2"],
                           "Foco em dano: Lendario (+ataque/defesa/vel.), Deus Inclemente (+20% ataque), "
                           "Brutamontes (+30% ataque, mas -50% trabalho) e Bom corredor (+vel.)."),
        "Tanque (defesa)": (["Legend", "Deffence_up2_2", "PAL_masochist", "MoveSpeed_up_2"],
                            "Foco em sobreviver: Lendario, Casca de aco (+defesa), Masoquista (+defesa) "
                            "e Bom corredor."),
        "Trabalho (base)": (["Legend", "CraftSpeed_up1", "PAL_ALLAttack_up3", "Deffence_up1"],
                            "Bom em tudo na base: Lendario, Mao de obra (+vel. de trabalho) e um pouco de "
                            "ataque/defesa para nao morrer."),
    }

    def __init__(self, master, app):
        Tela.__init__(self, master, app)
        self.pals = personagem.pals_do_mundo(app.level)
        self.atual = None
        self._passivas_opts()
        self._classificar_containers()
        try:
            js = personagem.jogadores(app.level)
            nv = js[0].nivel if js else 1
            self.nivel_jogador = nv.get("value", 1) if isinstance(nv, dict) else (nv or 1)
        except Exception:
            self.nivel_jogador = 1

        cab = ttk.Frame(self); cab.pack(fill="x", pady=(0, 6))
        ttk.Label(cab, text="Caixa de Pals  (%d)" % len(self.pals), style="Titulo.TLabel").pack(side="left")
        ttk.Button(cab, text="Igualar nivel de todos ao personagem (Nv %d)" % self.nivel_jogador,
                   command=self.igualar_niveis).pack(side="right")
        corpo = ttk.Panedwindow(self, orient="horizontal"); corpo.pack(fill="both", expand=True)

        esq = ttk.Labelframe(corpo, text="Seus Pals", padding=6); corpo.add(esq, weight=1)
        f = ttk.Frame(esq); f.pack(fill="x")
        ttk.Label(f, text="Buscar:").pack(side="left")
        self.v_b = tk.StringVar(); self.v_b.trace_add("write", lambda *a: self.render())
        ttk.Entry(f, textvariable=self.v_b).pack(side="left", fill="x", expand=True, padx=4)
        f2 = ttk.Frame(esq); f2.pack(fill="x", pady=(2, 0))
        ttk.Label(f2, text="Ordenar:").pack(side="left")
        self.v_ord = tk.StringVar(value="Nome")
        ttk.Combobox(f2, textvariable=self.v_ord, state="readonly", width=18,
                     values=["Nome", "Nivel (maior)", "Nivel (menor)", "Sexo"]).pack(side="left", padx=4)
        self.v_ord.trace_add("write", lambda *a: self.render())
        self.v_so_macho = tk.BooleanVar(value=False)
        self.v_so_femea = tk.BooleanVar(value=False)
        ttk.Checkbutton(f2, text="so M", variable=self.v_so_macho,
                        command=self.render).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(f2, text="so F", variable=self.v_so_femea,
                        command=self.render).pack(side="left")
        f3 = ttk.Frame(esq); f3.pack(fill="x", pady=(2, 0))
        ttk.Label(f3, text="Local:").pack(side="left")
        self.v_local = tk.StringVar(value="Todos")
        ttk.Combobox(f3, textvariable=self.v_local, state="readonly", width=22,
                     values=["Todos", "Com o personagem (equipe)", "Na caixa (Palbox)",
                             "Nas bases"]).pack(side="left", padx=4)
        self.v_local.trace_add("write", lambda *a: self.render())
        self.tv = ttk.Treeview(esq, columns=("lv", "g"), show="tree headings", height=22,
                               style="Big.Treeview")
        self.tv.heading("#0", text="Pal"); self.tv.heading("lv", text="Nv"); self.tv.heading("g", text="Sexo")
        self.tv.column("#0", width=240); self.tv.column("lv", width=40, anchor="e", stretch=False)
        self.tv.column("g", width=44, anchor="center", stretch=False)
        s = ttk.Scrollbar(esq, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=s.set); s.pack(side="right", fill="y")
        self.tv.pack(fill="both", expand=True, pady=4)
        self.tv.bind("<<TreeviewSelect>>", self.sel)

        self.ed = ttk.Labelframe(corpo, text="Editar", padding=10); corpo.add(self.ed, weight=1)
        self._painel_vazio()

        self.render()

    def _classificar_containers(self):
        """Descobre onde cada Pal esta: party (com o personagem), caixa (Palbox) ou base.
        Usa CharacterContainerSaveData: party tem 5 slots, a Palbox e a maior."""
        self.cat_cont = {}
        ccsd = self.app.level.ws.get("CharacterContainerSaveData")
        if not ccsd:
            return
        ents = ccsd["value"]

        def sn(ent):
            try:
                return ent["value"]["SlotNum"]["value"]
            except Exception:
                return 0
        maior = max(ents, key=sn) if ents else None
        gcaixa = str(maior["key"]["ID"]["value"]) if maior else None
        for ent in ents:
            g = str(ent["key"]["ID"]["value"])
            num = sn(ent)
            self.cat_cont[g] = "party" if num == 5 else ("caixa" if g == gcaixa else "base")

    @staticmethod
    def _cont_de(p):
        try:
            return str(p.sp["SlotId"]["value"]["ContainerId"]["value"]["ID"]["value"])
        except Exception:
            return None

    def _passivas_opts(self):
        d = traducao.carregar()["passivas"]
        pares = [(v, k) for k, v in d.items()
                 if v and v != "pt-BR_Text" and not k.startswith("Test") and "TEST" not in k]
        vistos = {}
        for nome, pid in pares:
            vistos.setdefault(nome, pid)
        self.pass_nome2id = dict(vistos)
        self.pass_id2nome = {pid: nome for nome, pid in vistos.items()}
        self.pass_lista = [""] + sorted(vistos.keys(), key=str.lower)

    def render(self):
        for i in self.tv.get_children():
            self.tv.delete(i)
        b = self.v_b.get().strip().lower(); self.map = {}
        ordem = self.v_ord.get()
        if ordem == "Nivel (maior)":
            dados = sorted(self.pals, key=lambda p: -p.nivel)
        elif ordem == "Nivel (menor)":
            dados = sorted(self.pals, key=lambda p: p.nivel)
        elif ordem == "Sexo":
            dados = sorted(self.pals, key=lambda p: (p.genero, traducao.nome_pal(p.especie).lower()))
        else:
            dados = sorted(self.pals, key=lambda p: traducao.nome_pal(p.especie).lower())
        for p in dados:
            nome = traducao.nome_pal(p.especie)
            if b and b not in nome.lower() and b not in p.especie.lower():
                continue
            if self.v_so_macho.get() and p.genero != "M":
                continue
            if self.v_so_femea.get() and p.genero != "F":
                continue
            loc = self.v_local.get()
            if loc != "Todos":
                cat = self.cat_cont.get(self._cont_de(p))
                if loc.startswith("Com o personagem") and cat != "party":
                    continue
                if loc.startswith("Na caixa") and cat != "caixa":
                    continue
                if loc.startswith("Nas bases") and cat != "base":
                    continue
            ico = icones_rt.pal(p.especie)
            kw = {"image": ico} if ico else {}
            self.map[self.tv.insert("", "end", text=" " + nome, values=(p.nivel, p.genero), **kw)] = p
            if len(self.map) >= 800:
                break

    def igualar_niveis(self):
        import copy
        n = self.nivel_jogador
        if not messagebox.askyesno("Confirmar",
                                   "Colocar TODOS os %d Pals no nivel %d (o do personagem)?\n\n"
                                   "So vale ao clicar em SALVAR NO JOGO depois." % (len(self.pals), n)):
            return
        maxiv = messagebox.askyesno("IVs", "Tambem deixar os IVs (Vida/Ataque/Defesa) de todos altos "
                                           "e variados (proximos de 100, sem cara de cheat)?")
        molde = next((p.sp["Level"] for p in self.pals if "Level" in p.sp), None)
        for p in self.pals:
            if "Level" not in p.sp and molde is not None:
                p.sp["Level"] = copy.deepcopy(molde)   # Pals nivel 1 nao guardam o campo
            p.set_nivel(n)
            if maxiv:
                p.set_talento("Talent_HP", random.randint(90, 100))
                p.set_talento("Talent_Shot", random.randint(90, 100))
                p.set_talento("Talent_Defense", random.randint(90, 100))
            p.gravar()
        self.app.marcar_sujo()
        self.render()
        self.app.status("todos os Pals no nivel %d - clique em SALVAR NO JOGO" % n, "#e0c060")
        messagebox.showinfo("Pronto", "Os %d Pals foram ajustados para o nivel %d.\n"
                                      "Clique em SALVAR NO JOGO." % (len(self.pals), n))

    def _painel_vazio(self):
        for w in self.ed.winfo_children():
            w.destroy()
        ttk.Label(self.ed, text="Selecione um Pal a esquerda.", style="Sub.TLabel").pack(pady=20)

    def sel(self, _e=None):
        s = self.tv.selection()
        if not s:
            return
        self.atual = self.map[s[0]]; self._painel()

    def _painel(self):
        p = self.atual
        for w in self.ed.winfo_children():
            w.destroy()
        ttk.Label(self.ed, text=traducao.nome_pal(p.especie), font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(self.ed, text=p.especie, style="Sub.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.v_nv = tk.StringVar(value=str(p.nivel))
        self.v_g = tk.StringVar(value=("Femea" if p.genero == "F" else "Macho"))
        self.v_hp = tk.StringVar(value=str(p.talento("Talent_HP")))
        self.v_at = tk.StringVar(value=str(p.talento("Talent_Shot")))
        self.v_df = tk.StringVar(value=str(p.talento("Talent_Defense")))
        self.v_rk = tk.StringVar(value=str(max(0, p.rank - 1)))   # mostra estrelas (0-4)
        lin = 2
        def campo(rot, var, larg=8, combo=None):
            nonlocal lin
            ttk.Label(self.ed, text=rot).grid(row=lin, column=0, sticky="e", padx=(0, 6), pady=3)
            if combo:
                w = ttk.Combobox(self.ed, textvariable=var, values=combo, state="readonly", width=larg)
            else:
                w = ttk.Entry(self.ed, textvariable=var, width=larg)
            w.grid(row=lin, column=1, sticky="w"); lin += 1; return w
        campo("Nivel", self.v_nv)
        campo("Sexo", self.v_g, 10, ["Macho", "Femea"])
        campo("IV Vida (0-100)", self.v_hp)
        campo("IV Ataque (0-100)", self.v_at)
        campo("IV Defesa (0-100)", self.v_df)
        campo("Estrelas de condensacao (0-4)", self.v_rk, 6)

        ttk.Label(self.ed, text="Passivas:", font=("Segoe UI", 10, "bold")).grid(
            row=lin, column=0, columnspan=3, sticky="w", pady=(10, 2)); lin += 1
        atuais = p.passivas
        self.v_pass = []
        for k in range(4):
            var = tk.StringVar(value=self.pass_id2nome.get(atuais[k], atuais[k]) if k < len(atuais) else "")
            ttk.Combobox(self.ed, textvariable=var, values=self.pass_lista, width=28).grid(
                row=lin, column=0, columnspan=2, sticky="w", pady=1); lin += 1
            self.v_pass.append(var)

        ttk.Label(self.ed, text="Sugerir melhores passivas:", style="Sub.TLabel").grid(
            row=lin, column=0, columnspan=3, sticky="w", pady=(10, 2)); lin += 1
        self.v_preset = tk.StringVar()
        ttk.Combobox(self.ed, textvariable=self.v_preset, values=list(self.PRESETS), state="readonly",
                     width=28).grid(row=lin, column=0, columnspan=2, sticky="w"); lin += 1
        bs = ttk.Frame(self.ed); bs.grid(row=lin, column=0, columnspan=2, sticky="w", pady=(4, 2)); lin += 1
        ttk.Button(bs, text="Ver sugestao", command=self._ver_sug).pack(side="left")
        self.b_aplicar_sug = ttk.Button(bs, text="Aplicar aos 4 espacos", command=self._aplicar_sug,
                                        state="disabled")
        self.b_aplicar_sug.pack(side="left", padx=4)
        self.lbl_sug = ttk.Label(self.ed, text="", style="Sub.TLabel", justify="left", wraplength=360)
        self.lbl_sug.grid(row=lin, column=0, columnspan=3, sticky="w", pady=(0, 8)); lin += 1

        ttk.Button(self.ed, text="Guardar alteracoes deste Pal", style="Accent.TButton",
                   command=self._guardar).grid(row=lin, column=0, columnspan=2, sticky="w", pady=8)

    def _ver_sug(self):
        nome = self.v_preset.get()
        if not nome:
            messagebox.showinfo("Sugestao", "Escolha um perfil na lista."); return
        ids, expl = self.PRESETS[nome]
        legiveis = [self.pass_id2nome.get(i, i) for i in ids]
        self._sug_ids = legiveis
        self.lbl_sug.configure(text="%s\n\nPassivas sugeridas:\n- %s" % (expl, "\n- ".join(legiveis)))
        self.b_aplicar_sug.configure(state="normal")

    def _aplicar_sug(self):
        for k in range(4):
            self.v_pass[k].set(self._sug_ids[k] if k < len(self._sug_ids) else "")
        # IVs proximos de 100, mas variados (parece bem criado, sem cara de cheat)
        self.v_hp.set(str(random.randint(90, 100)))
        self.v_at.set(str(random.randint(90, 100)))
        self.v_df.set(str(random.randint(90, 100)))
        self.v_rk.set("4")   # condensacao no maximo (4 estrelas)
        self.lbl_sug.configure(text=self.lbl_sug.cget("text") +
                               "\n\n(passivas + IVs altos (90-100) + condensacao 4 estrelas "
                               "aplicados - revise e Guardar)")
        self.b_aplicar_sug.configure(state="disabled")

    def _guardar(self):
        p = self.atual
        try:
            p.set_nivel(int(self.v_nv.get()))
            p.set_genero("F" if self.v_g.get().startswith("F") else "M")
            p.set_talento("Talent_HP", int(self.v_hp.get()))
            p.set_talento("Talent_Shot", int(self.v_at.get()))
            p.set_talento("Talent_Defense", int(self.v_df.get()))
            p.set_rank(max(0, min(int(self.v_rk.get()), 4)) + 1)   # estrelas 0-4 -> Rank 1-5
            ids = []
            for var in self.v_pass:
                nome = var.get().strip()
                if nome:
                    ids.append(self.pass_nome2id.get(nome, nome))
            p.set_passivas(ids)
            p.gravar()
        except Exception as ex:
            messagebox.showerror("Erro", str(ex)); return
        self.app.marcar_sujo()
        self.tv.item(self.tv.selection()[0], values=(p.nivel, p.genero))
        self.app.status("Pal alterado - clique em SALVAR NO JOGO", "#e0c060")
        messagebox.showinfo("Guardado", "Alteracoes deste Pal preparadas. Clique em SALVAR NO JOGO.")


# ---------------------------------------------------------------------------
class TelaBreeding(Tela):
    def __init__(self, master, app):
        Tela.__init__(self, master, app)
        self.eng = breeding.carregar()
        self.alvo_sel = None

        # sexos que voce tem de cada especie (normalizando alfas para a especie base)
        self.meus_gen = {}
        for p in personagem.pals_do_mundo(app.level):
            self.meus_gen.setdefault(self._norm(p.especie), set()).add(p.genero)

        ttk.Label(self, text="Breeding", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(self, style="Sub.TLabel", text=(
            "Escolha o Pal que voce quer criar. O editor mostra os pares que geram ele. "
            "A reproducao precisa de 1 macho + 1 femea: quando voce so tem do mesmo sexo, "
            "aparece um aviso -- e so trocar o sexo de um na Caixa de Pals.")
        ).pack(anchor="w", pady=(0, 6))

        corpo = ttk.Panedwindow(self, orient="horizontal"); corpo.pack(fill="both", expand=True)

        # ---- esquerda: escolher o alvo ----
        esq = ttk.Labelframe(corpo, text="O que voce quer criar?", padding=6); corpo.add(esq, weight=1)
        f = ttk.Frame(esq); f.pack(fill="x")
        ttk.Label(f, text="Buscar:").pack(side="left")
        self.v_busca = tk.StringVar(); self.v_busca.trace_add("write", lambda *a: self.render_alvos())
        ttk.Entry(f, textvariable=self.v_busca).pack(side="left", fill="x", expand=True, padx=4)
        f2 = ttk.Frame(esq); f2.pack(fill="x", pady=(2, 0))
        ttk.Label(f2, text="Elemento:").pack(side="left")
        elems = ["Todos"] + sorted({e for v in self.eng.pals.values() for e in v.get("elements", [])})
        self.v_elem = tk.StringVar(value="Todos")
        ttk.Combobox(f2, textvariable=self.v_elem, state="readonly", width=14,
                     values=elems).pack(side="left", padx=4)
        self.v_elem.trace_add("write", lambda *a: self.render_alvos())
        ttk.Label(f2, text="Ordenar:").pack(side="left", padx=(8, 0))
        self.v_ord = tk.StringVar(value="Numero")
        ttk.Combobox(f2, textvariable=self.v_ord, state="readonly", width=10,
                     values=["Numero", "Nome"]).pack(side="left", padx=4)
        self.v_ord.trace_add("write", lambda *a: self.render_alvos())

        self.tv_alvo = ttk.Treeview(esq, columns=("num",), show="tree headings", height=20,
                                    style="Big.Treeview")
        self.tv_alvo.heading("#0", text="Pal"); self.tv_alvo.heading("num", text="No")
        self.tv_alvo.column("#0", width=210); self.tv_alvo.column("num", width=44, anchor="e", stretch=False)
        sa = ttk.Scrollbar(esq, orient="vertical", command=self.tv_alvo.yview)
        self.tv_alvo.configure(yscrollcommand=sa.set); sa.pack(side="right", fill="y")
        self.tv_alvo.pack(fill="both", expand=True, pady=4)
        self.tv_alvo.bind("<<TreeviewSelect>>", self.sel_alvo)

        # ---- direita: pares ----
        dir_ = ttk.Labelframe(corpo, text="Pares que geram esse Pal", padding=6); corpo.add(dir_, weight=2)
        fm = ttk.Frame(dir_); fm.pack(fill="x")
        self.v_modo = tk.StringVar(value="meus")
        ttk.Radiobutton(fm, text="Usar so os meus Pals", variable=self.v_modo, value="meus",
                        command=self.render_pares).pack(side="left")
        ttk.Radiobutton(fm, text="Todos os Pals do jogo", variable=self.v_modo, value="todos",
                        command=self.render_pares).pack(side="left", padx=(8, 0))
        self.lbl_res = ttk.Label(dir_, style="Sub.TLabel", text="Escolha um Pal a esquerda.")
        self.lbl_res.pack(anchor="w", pady=(4, 2))

        self.tv_par = ttk.Treeview(dir_, columns=("tipo", "obs"), show="tree headings", height=20,
                                   style="Big.Treeview")
        self.tv_par.heading("#0", text="Par (Pai x Mae)")
        self.tv_par.heading("tipo", text="Tipo"); self.tv_par.heading("obs", text="Sexo")
        self.tv_par.column("#0", width=330)
        self.tv_par.column("tipo", width=64, anchor="center", stretch=False)
        self.tv_par.column("obs", width=150, anchor="w", stretch=False)
        self.tv_par.tag_configure("aviso", foreground="#e0a030")
        sp = ttk.Scrollbar(dir_, orient="vertical", command=self.tv_par.yview)
        self.tv_par.configure(yscrollcommand=sp.set); sp.pack(side="right", fill="y")
        self.tv_par.pack(fill="both", expand=True, pady=4)

        self.render_alvos()

    @staticmethod
    def _norm(esp):
        for pre in ("BOSS_", "Boss_"):
            if esp.startswith(pre):
                return esp[len(pre):]
        return esp

    def render_alvos(self):
        for i in self.tv_alvo.get_children():
            self.tv_alvo.delete(i)
        b = self.v_busca.get().strip().lower()
        elem = self.v_elem.get()
        if self.v_ord.get() == "Nome":
            itens = sorted(self.eng.pals.items(), key=lambda kv: traducao.nome_pal(kv[0]).lower())
        else:
            itens = sorted(self.eng.pals.items(), key=lambda kv: kv[1].get("index", 9999))
        self.map_alvo = {}
        for key, info in itens:
            nome = traducao.nome_pal(key)
            if b and b not in nome.lower() and b not in key.lower():
                continue
            if elem != "Todos" and elem not in info.get("elements", []):
                continue
            ico = icones_rt.pal(key)
            kw = {"image": ico} if ico else {}
            self.map_alvo[self.tv_alvo.insert("", "end", text=" " + nome,
                                              values=(info.get("index", ""),), **kw)] = key

    def sel_alvo(self, _e=None):
        s = self.tv_alvo.selection()
        self.alvo_sel = self.map_alvo.get(s[0]) if s else None
        self.render_pares()

    def _obs_genero(self, a, b):
        if self.v_modo.get() != "meus":
            return "precisa 1 M + 1 F"
        ga = self.meus_gen.get(a, set()); gb = self.meus_gen.get(b, set())
        if a == b:
            return "" if {"M", "F"} <= ga else "trocar sexo (precisa M+F)"
        if ("M" in ga and "F" in gb) or ("F" in ga and "M" in gb):
            return ""
        return "trocar o sexo de um"

    def render_pares(self, *a):
        for i in self.tv_par.get_children():
            self.tv_par.delete(i)
        if not self.alvo_sel:
            self.lbl_res.configure(text="Escolha um Pal a esquerda.")
            return
        disp = set(self.meus_gen.keys()) if self.v_modo.get() == "meus" else set(self.eng.pals.keys())
        pares = self.eng.pares_para(self.alvo_sel, disp)
        pares.sort(key=lambda t: (t[2] != "unico", traducao.nome_pal(t[0]).lower()))
        nome_alvo = traducao.nome_pal(self.alvo_sel)
        if not pares:
            self.lbl_res.configure(text=("Nenhum par entre os seus Pals gera %s. "
                                         "Tente 'Todos os Pals do jogo'." % nome_alvo)
                                   if self.v_modo.get() == "meus"
                                   else "Nenhuma combinacao conhecida gera %s." % nome_alvo)
            return
        self.lbl_res.configure(text="%d par(es) geram %s" % (len(pares), nome_alvo))
        for a2, b2, tipo in pares[:600]:
            obs = self._obs_genero(a2, b2)
            ico = icones_rt.pal(a2)
            kw = {"image": ico} if ico else {}
            self.tv_par.insert("", "end", text=" %s  x  %s" % (traducao.nome_pal(a2), traducao.nome_pal(b2)),
                               values=("Unico" if tipo == "unico" else "Normal", obs),
                               tags=("aviso",) if obs and "trocar" in obs else (), **kw)


# ===========================================================================
class JanelaAdicionar(tk.Toplevel):
    def __init__(self, app, tela, alvo):
        tk.Toplevel.__init__(self, app)
        self.app = app; self.tela = tela; self.alvo = alvo
        self.title("Adicionar item em: %s" % app.nomes[alvo.guid][0])
        self.geometry("640x560"); self.transient(app); self.grab_set()
        f = ttk.Frame(self, padding=8); f.pack(fill="x")
        ttk.Label(f, text="Buscar:").pack(side="left")
        self.v = tk.StringVar(); self.v.trace_add("write", lambda *a: self.render())
        e = ttk.Entry(f, textvariable=self.v); e.pack(side="left", fill="x", expand=True, padx=4); e.focus_set()
        self.tv = ttk.Treeview(self, columns=("tem",), show="tree headings")
        self.tv.heading("#0", text="Item"); self.tv.heading("tem", text="Ja tem")
        self.tv.column("#0", width=440); self.tv.column("tem", width=80, anchor="e", stretch=False)
        sc = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sc.set); sc.pack(side="right", fill="y")
        self.tv.pack(fill="both", expand=True, padx=8, pady=4)
        self.tv.bind("<Double-1>", lambda e: self.add())
        f2 = ttk.Frame(self, padding=8); f2.pack(fill="x")
        ttk.Label(f2, text="Qtd:").pack(side="left")
        self.vq = tk.StringVar(value=(tela.var_q.get() or "1"))
        ttk.Entry(f2, textvariable=self.vq, width=8).pack(side="left", padx=4)
        ttk.Button(f2, text="Adicionar", command=self.add).pack(side="left")
        ttk.Button(f2, text="Fechar", command=self.destroy).pack(side="right")
        self.render()

    def render(self):
        for i in self.tv.get_children():
            self.tv.delete(i)
        b = self.v.get().strip().lower(); self.map = {}; n = 0
        at = self.alvo.items
        for sid in self.app.todos_ids():
            nome = traducao.nome_item(sid)
            if b and b not in sid.lower() and b not in nome.lower():
                continue
            rot = nome if nome == sid else "%s  (%s)" % (nome, sid)
            self.map[self.tv.insert("", "end", text=rot, values=(at.get(sid, "") or "",))] = sid
            n += 1
            if n >= 900:
                break

    def add(self):
        s = self.tv.selection()
        if not s:
            return
        try:
            q = max(1, min(int(self.vq.get()), LIMITE))
        except ValueError:
            messagebox.showwarning("Invalido", "Digite um numero.", parent=self); return
        d = self.tela.pend(self.alvo)
        for i in s:
            d[self.map[i]] = q
        self.tela.container = self.alvo
        self.tela.render_cont(); self.tela.render_item()
        self.app.status("%d item(ns) marcados" % self.app.n_pendencias(), "#e0c060")


class JanelaRestaurar(tk.Toplevel):
    def __init__(self, app):
        tk.Toplevel.__init__(self, app)
        self.app = app; self.title("Restaurar backup"); self.geometry("720x420")
        self.transient(app); self.grab_set()
        ttk.Label(self, text="Escolha um ponto para voltar. O save atual sera substituido.",
                  padding=8).pack(anchor="w")
        self.tv = ttk.Treeview(self, columns=("quando", "tam", "obs"), show="tree headings")
        for c, t, w in [("#0", "Backup", 210), ("quando", "Quando", 140), ("tam", "Tam", 70), ("obs", "Obs", 250)]:
            self.tv.heading(c, text=t); self.tv.column(c, width=w)
        self.tv.pack(fill="both", expand=True, padx=8)
        self.mapa = {}
        for m in app.bm.list():
            nome = m["dir"] + ("   * ORIGINAL" if m["original"] else "")
            self.mapa[self.tv.insert("", "end", text=nome, values=(
                m.get("time", ""), "%.1f MB" % (m["size"] / 1048576.0), m.get("label", "")))] = m
        f = ttk.Frame(self, padding=8); f.pack(fill="x")
        ttk.Button(f, text="Restaurar o selecionado", command=self.restaurar).pack(side="left")
        ttk.Button(f, text="Fechar", command=self.destroy).pack(side="right")

    def restaurar(self):
        s = self.tv.selection()
        if not s:
            return
        m = self.mapa[s[0]]
        if not messagebox.askyesno("Confirmar", "Restaurar '%s'?\nO save atual sera substituido "
                                   "(com backup antes).\nO JOGO PRECISA ESTAR FECHADO." % m["dir"], parent=self):
            return
        try:
            self.app.bm.restore(m["path"])
        except Exception as ex:
            messagebox.showerror("Erro", str(ex), parent=self); return
        messagebox.showinfo("Ok", "Save restaurado.", parent=self); self.destroy()
        self.app.index = wgs.parse_index(self.app.root_wgs); self.app.carregar_mundo()


if __name__ == "__main__":
    App().mainloop()
