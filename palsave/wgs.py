# -*- coding: utf-8 -*-
"""Camada WGS: os saves do Palworld versao Xbox/GDK ficam em 'containers'.

Estrutura:
  wgs/<conta>/containers.index      indice: nome do save -> GUID da pasta + tamanho
  wgs/<conta>/<GUID>/container.N    aponta para o arquivo de dados
  wgs/<conta>/<GUID>/<GUID2>        o arquivo de dados em si (o save comprimido)
"""
import os, struct, io, uuid, time, glob

# --------------------------------------------------------------------------
# Descoberta do save: acha sozinho a pasta-conta (a que tem containers.index),
# mesmo que o sufixo do pacote mude ou o save esteja em outro lugar.
# --------------------------------------------------------------------------
def candidatos_padrao():
    """Locais tipicos do save da versao Xbox/Microsoft Store."""
    la = os.environ.get("LOCALAPPDATA", "")
    pats = [
        os.path.join(la, "Packages", "PocketpairInc.Palworld_*", "SystemAppData", "wgs"),
        os.path.join(la, "Packages", "*Palworld*", "SystemAppData", "wgs"),
        os.path.join(la, "Packages", "*Palworld*"),
    ]
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return out

def procurar_conta(raiz, max_prof=6):
    """Varre 'raiz' e suas subpastas ate achar uma que contenha containers.index.
    Retorna o caminho dessa pasta (a 'conta' WGS) ou None."""
    if not raiz or not os.path.isdir(raiz):
        return None
    raiz = os.path.abspath(raiz)
    base = raiz.rstrip("\\/").count(os.sep)
    for dirpath, dirnames, filenames in os.walk(raiz):
        if "containers.index" in filenames:
            return dirpath
        if dirpath.count(os.sep) - base >= max_prof:
            dirnames[:] = []          # nao desce mais fundo
    return None

def localizar_conta(dirs, max_prof=4):
    """Primeira pasta-conta valida encontrada a partir de uma lista de candidatos."""
    for d in dirs:
        c = procurar_conta(d, max_prof)
        if c:
            return c
    return None

def descobrir_save():
    """Tenta achar o save automaticamente nos locais padrao. None se nao achar."""
    return localizar_conta(candidatos_padrao())

def _now_filetime():
    """FILETIME do Windows: intervalos de 100ns desde 1601-01-01 UTC."""
    return int((time.time() + 11644473600) * 10_000_000)

def jogo_rodando():
    """True se o Palworld estiver aberto AGORA. Editar o save com o jogo aberto e a
    principal causa de corrupcao (o jogo reescreve o containers.index em paralelo)."""
    alvos = ("Palworld-Win64-Shipping.exe", "Palworld.exe")
    try:
        import subprocess
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=8,
                             creationflags=0x08000000).stdout  # CREATE_NO_WINDOW
        low = out.lower()
        return any(a.lower() in low for a in alvos)
    except Exception:
        return False

def find_wgs_root(wgs_dir):
    """Retorna a pasta da conta (a que contem containers.index)."""
    for d in sorted(os.listdir(wgs_dir)):
        p = os.path.join(wgs_dir, d)
        if os.path.isfile(os.path.join(p, "containers.index")):
            return p
    raise FileNotFoundError("containers.index nao encontrado em %s" % wgs_dir)

def _guid_str(b):
    return "%08X%04X%04X%s" % (struct.unpack("<I", b[0:4])[0],
                               struct.unpack("<H", b[4:6])[0],
                               struct.unpack("<H", b[6:8])[0], b[8:].hex().upper())

def parse_index(root):
    """Le containers.index. Guarda o offset do campo 'tamanho' pra poder corrigir depois."""
    path = os.path.join(root, "containers.index")
    data = open(path, "rb").read()
    f = io.BytesIO(data)
    rd = lambda fmt: struct.unpack(fmt, f.read(struct.calcsize(fmt)))
    def rstr():
        (n,) = rd("<i")
        return f.read(n * 2).decode("utf-16-le") if n > 0 else ""

    ver, = rd("<i"); cnt, = rd("<i"); rd("<i")
    pkg = rstr()
    gfiletime_off = f.tell(); rd("<q")   # FILETIME global do indice (libNOM: =agora ao salvar)
    gstate_off = f.tell(); rd("<i")      # estado global do indice (libNOM: =2 Modified ao salvar)
    rstr(); rd("<q")

    entries = []
    for _ in range(cnt):
        name = rstr(); rstr(); rstr()
        seq_off = f.tell()
        seq, = rd("<B")
        state_off = f.tell()
        state, = rd("<i")
        cguid = f.read(16)
        ft_off = f.tell()
        ft, = rd("<q")
        rd("<q")
        size_off = f.tell()          # offset do int64 de tamanho — usado pra corrigir
        size, = rd("<q")
        entries.append(dict(name=name, seq=seq, state=state, folder=_guid_str(cguid),
                            filetime=ft, size=size, size_off=size_off,
                            seq_off=seq_off, state_off=state_off, filetime_off=ft_off))
    if f.tell() != len(data):
        raise ValueError("containers.index nao foi lido ate o fim (%d de %d)" % (f.tell(), len(data)))
    return dict(version=ver, pkg=pkg, entries=entries, raw=data, path=path,
                gfiletime_off=gfiletime_off, gstate_off=gstate_off)

def set_entry_size(index, entry, new_size):
    """Corrige o tamanho de uma entrada dentro dos bytes do indice (em memoria)."""
    b = bytearray(index["raw"])
    struct.pack_into("<q", b, entry["size_off"], new_size)
    index["raw"] = bytes(b)
    entry["size"] = new_size

def save_index(index):
    _atomic_write(index["path"], index["raw"])

def blob_files(root, entry):
    """[(nome_logico, caminho_do_arquivo_de_dados)] de uma entrada."""
    d = os.path.join(root, entry["folder"])
    cf = os.path.join(d, "container.%d" % entry["seq"])
    if not os.path.isfile(cf):
        cands = sorted(x for x in os.listdir(d) if x.startswith("container."))
        if not cands:
            return []
        cf = os.path.join(d, cands[0])
    raw = open(cf, "rb").read()
    _, n = struct.unpack_from("<ii", raw, 0)
    out, off = [], 8
    for _ in range(n):
        nm = raw[off:off + 128].decode("utf-16-le").rstrip("\x00"); off += 128
        for _i in range(2):
            g = raw[off:off + 16]; off += 16
            fp = os.path.join(d, _guid_str(g))
            if os.path.isfile(fp) and not any(fp == o[1] for o in out):
                out.append((nm, fp))
    return out

def read_blob(root, entry):
    fs = blob_files(root, entry)
    if not fs:
        raise FileNotFoundError("sem arquivo de dados para " + entry["name"])
    return fs[0][1], open(fs[0][1], "rb").read()

def _guid_bytes():
    """16 bytes aleatorios para um novo GUID de blob."""
    return uuid.uuid4().bytes

def _ler_container_file(path):
    raw = open(path, "rb").read()
    ver, n = struct.unpack_from("<ii", raw, 0)
    blobs, off = [], 8
    for _ in range(n):
        nome = raw[off:off + 128]; off += 128
        g1 = raw[off:off + 16]; off += 16
        g2 = raw[off:off + 16]; off += 16
        blobs.append([nome, g1, g2])
    return ver, blobs

def _escrever_container_file(path, ver, blobs):
    out = struct.pack("<ii", ver, len(blobs))
    for nome, g1, g2 in blobs:
        out += nome + g1 + g2
    _atomic_write(path, out)

SYNC_MODIFIED = 2      # estado "modificado/pendente de upload" (libNOM MicrosoftBlobSyncStateEnum)


def _tam_total_blobs(folder, blobs):
    """Soma o tamanho de TODOS os blobs que o container referencia (data+meta...),
    como o libNOM grava no campo 'size' do indice -- nao so o blob principal."""
    vistos, total = set(), 0
    for _nome, g1, g2 in blobs:
        for g in (g1, g2):
            fp = os.path.join(folder, _guid_str(g))
            if fp not in vistos and os.path.isfile(fp):
                vistos.add(fp); total += os.path.getsize(fp)
    return total


def write_blob(root, index, entry, data):
    """Grava o save do jeito que o Xbox/GDK espera: copy-on-write, SEM sobrescrever
    a versao antiga da nuvem/servico.

    IMPORTANTE (correcao de corrupcao): o servico GamingServices do Xbox reescreve o
    containers.index em segundo plano (sincronizacao). Se a gente gravar por cima de
    uma copia VELHA do indice que carregamos na memoria, apagamos as mudancas do
    servico e o indice passa a apontar para blobs que ja foram rotacionados -> o jogo
    le como save quebrado. Por isso aqui RELEMOS o indice do disco na hora, mesclamos
    nossa alteracao na versao mais nova, marcamos o estado como 'Modified' (pra nossa
    versao vencer o sync, em vez da nuvem sobrescrever) e VERIFICAMOS no final.
    """
    nome_entrada = entry["name"]
    # (a) RELE o indice do disco AGORA -- nao confia na copia da memoria
    fresh = parse_index(root)
    fe = next((e for e in fresh["entries"] if e["name"] == nome_entrada), None)
    if fe is None:
        raise RuntimeError("A entrada '%s' sumiu do containers.index (o jogo/servico "
                           "Xbox reescreveu o save). Feche o Palworld, espere a "
                           "sincronizacao e recarregue o save antes de editar." % nome_entrada)

    folder = os.path.join(root, fe["folder"])
    seq = fe["seq"]
    cont_atual = os.path.join(folder, "container.%d" % seq)
    if not os.path.isfile(cont_atual):
        cands = sorted(x for x in os.listdir(folder) if x.startswith("container."))
        if not cands:
            raise FileNotFoundError("sem container.N em " + folder)
        cont_atual = os.path.join(folder, cands[0])
        seq = int(cont_atual.rsplit(".", 1)[1])

    ver, blobs = _ler_container_file(cont_atual)
    if not blobs:
        # container.N com 0 blobs = versao PENDENTE do servico (sync em andamento).
        raise RuntimeError("O save esta em sincronizacao pelo servico do Xbox agora "
                           "(container pendente). Feche o Palworld, espere ~1-2 min e "
                           "tente de novo -- gravar durante o sync corrompe.")

    # 1) novo blob com GUID novo
    novo_guid = _guid_bytes()
    novo_arq = os.path.join(folder, _guid_str(novo_guid))
    _atomic_write(novo_arq, data)

    # 2) novo container.N+1 (o primeiro blob -- "Data" -- passa a apontar pro novo GUID)
    guids_antigos = []
    for i, (nome, g1, g2) in enumerate(blobs):
        if i == 0:
            guids_antigos.extend([g1, g2])
            blobs[i] = [nome, novo_guid, novo_guid]   # slot2 = blob vivo (o que o jogo carrega)
    novo_seq = 1 if seq >= 255 else seq + 1
    novo_cont = os.path.join(folder, "container.%d" % novo_seq)
    _escrever_container_file(novo_cont, ver, blobs)

    # 3) atualiza o indice FRESCO: seq, filetime, tamanho(soma dos blobs), estado=Modified
    b = bytearray(fresh["raw"])
    b[fe["seq_off"]] = novo_seq & 0xFF
    struct.pack_into("<q", b, fe["filetime_off"], _now_filetime())
    struct.pack_into("<q", b, fe["size_off"], _tam_total_blobs(folder, blobs))
    struct.pack_into("<i", b, fe["state_off"], SYNC_MODIFIED)       # entrada = modificada
    # cabecalho global do indice: filetime=agora e estado=Modified (como o libNOM faz)
    struct.pack_into("<q", b, fresh["gfiletime_off"], _now_filetime())
    struct.pack_into("<i", b, fresh["gstate_off"], SYNC_MODIFIED)
    fresh["raw"] = bytes(b)
    _atomic_write(fresh["path"], fresh["raw"])

    # (b) VERIFICA: relê o indice e confirma que aponta pro nosso container/blob novos
    conf = parse_index(root)
    ce = next((e for e in conf["entries"] if e["name"] == nome_entrada), None)
    if ce is None or ce["seq"] != novo_seq:
        raise RuntimeError("Verificacao falhou: o indice nao ficou na versao nova (o "
                           "servico do Xbox pode ter reescrito no meio). Recarregue o "
                           "save e tente com o Palworld fechado.")
    if not blob_files(root, ce):
        raise RuntimeError("Verificacao falhou: o indice novo nao aponta para um blob "
                           "valido. Restaure um backup pelo editor.")

    # sincroniza a copia em memoria do chamador com o que ficou no disco
    index["raw"] = conf["raw"]; index["entries"] = conf["entries"]
    index["gfiletime_off"] = conf["gfiletime_off"]; index["gstate_off"] = conf["gstate_off"]
    for campo in ("seq", "size", "folder", "state", "filetime",
                  "seq_off", "state_off", "filetime_off", "size_off"):
        entry[campo] = ce[campo]

    # 4) limpeza: remove o container.N antigo e os blobs antigos
    try:
        if os.path.abspath(cont_atual) != os.path.abspath(novo_cont):
            os.remove(cont_atual)
    except OSError:
        pass
    for g in guids_antigos:
        antigo = os.path.join(folder, _guid_str(g))
        if os.path.isfile(antigo) and os.path.abspath(antigo) != os.path.abspath(novo_arq):
            try:
                os.remove(antigo)
            except OSError:
                pass

def _atomic_write(path, data):
    tmp = path + ".tmp_editor"
    with open(tmp, "wb") as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)

def worlds(index):
    """Agrupa entradas por mundo. Retorna {id_do_mundo: {sufixo: entrada}}."""
    out = {}
    for e in index["entries"]:
        if "-" not in e["name"]:
            continue
        wid, _, rest = e["name"].partition("-")
        if len(wid) != 32:
            continue
        out.setdefault(wid, {})[rest] = e
    return out
