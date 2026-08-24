# -*- coding: utf-8 -*-
"""Verificacao e instalacao de atualizacoes a partir do GitHub.

Compara a versao local (arquivo VERSION) com a do repositorio. Se houver versao
nova, instala: via 'git pull' quando a pasta e um clone git, ou baixando o ZIP
e sobrescrevendo os arquivos quando nao e (preservando backups e config).
"""
import os, json, ssl, shutil, subprocess, tempfile, zipfile, urllib.request

REPO = "disouz4-dev/Palworld-Edit"
RAMO = "main"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(BASE, "VERSION")
URL_RAW = "https://raw.githubusercontent.com/%s/%s/VERSION" % (REPO, RAMO)
URL_COMMIT = "https://api.github.com/repos/%s/commits/%s" % (REPO, RAMO)
URL_ZIP = "https://github.com/%s/archive/refs/heads/%s.zip" % (REPO, RAMO)

# nunca sobrescrever/apagar isto ao atualizar via ZIP
PRESERVAR = {"backups", "config.json", "extracao_local.json", ".git", "__pycache__"}


def versao_local():
    try:
        return open(VERSION_FILE, encoding="utf-8").read().strip() or "0.0.0"
    except Exception:
        return "0.0.0"


def _tupla(v):
    out = []
    for p in v.split("."):
        d = "".join(ch for ch in p if ch.isdigit())
        out.append(int(d) if d else 0)
    return tuple(out)


def _baixar(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "PalworldEditor"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def verificar(timeout=15):
    """Retorna dict {ok, tem_update, local, remota, notas, erro}."""
    local = versao_local()
    try:
        remota = _baixar(URL_RAW, timeout).decode("utf-8").strip()
    except Exception as ex:
        return {"ok": False, "erro": str(ex), "local": local, "tem_update": False}
    notas = ""
    try:
        info = json.loads(_baixar(URL_COMMIT, timeout).decode("utf-8"))
        notas = (info.get("commit", {}).get("message", "") or "").split("\n")[0]
    except Exception:
        pass
    return {"ok": True, "tem_update": _tupla(remota) > _tupla(local),
            "local": local, "remota": remota, "notas": notas, "erro": None}


def _eh_git():
    return os.path.isdir(os.path.join(BASE, ".git")) and bool(shutil.which("git"))


def instalar(log=None):
    """Instala a versao nova. Retorna (ok, mensagem)."""
    def _log(m):
        if log:
            log(m)

    if _eh_git():
        _log("atualizando via git...")
        try:
            p = subprocess.run(["git", "-C", BASE, "pull", "--ff-only"],
                               capture_output=True, text=True, timeout=180)
            saida = (p.stdout + p.stderr).strip()
            if p.returncode == 0:
                return True, "Atualizado via git.\n\n" + saida
            return False, ("git pull falhou (talvez haja arquivos modificados "
                           "localmente):\n\n" + saida)
        except Exception as ex:
            return False, "Erro ao rodar o git: %s" % ex

    _log("baixando o pacote do GitHub...")
    try:
        dados = _baixar(URL_ZIP, timeout=180)
    except Exception as ex:
        return False, "Falha ao baixar: %s" % ex
    tmp = tempfile.mkdtemp(prefix="paledit_upd_")
    try:
        zp = os.path.join(tmp, "u.zip")
        with open(zp, "wb") as fh:
            fh.write(dados)
        with zipfile.ZipFile(zp) as z:
            z.extractall(tmp)
        raiz = next((os.path.join(tmp, d) for d in os.listdir(tmp)
                     if os.path.isdir(os.path.join(tmp, d))
                     and d.lower().startswith("palworld")), None)
        if not raiz:
            return False, "Pacote invalido (raiz nao encontrada)."
        _log("copiando arquivos...")
        _copiar_sobre(raiz, BASE)
        return True, "Atualizado (pacote ZIP)."
    except Exception as ex:
        return False, "Falha ao instalar: %s" % ex
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _copiar_sobre(src, dst):
    for nome in os.listdir(src):
        if nome in PRESERVAR:
            continue
        s = os.path.join(src, nome)
        d = os.path.join(dst, nome)
        if os.path.isdir(s):
            _merge_dir(s, d)
        else:
            shutil.copy2(s, d)


def _merge_dir(src, dst):
    os.makedirs(dst, exist_ok=True)
    for nome in os.listdir(src):
        if nome == "__pycache__":
            continue
        s = os.path.join(src, nome)
        d = os.path.join(dst, nome)
        if os.path.isdir(s):
            _merge_dir(s, d)
        else:
            shutil.copy2(s, d)
