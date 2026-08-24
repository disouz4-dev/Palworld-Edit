# -*- coding: utf-8 -*-
"""Backup e restauracao dos saves. Copia a pasta inteira da conta WGS."""
import os, shutil, time, json

class BackupManager(object):
    def __init__(self, wgs_root, store):
        self.wgs_root = wgs_root          # .../wgs/<conta>
        self.store = store
        os.makedirs(store, exist_ok=True)

    def _meta_path(self, d):
        return os.path.join(self.store, d, "_backup.json")

    def list(self):
        out = []
        for d in sorted(os.listdir(self.store), reverse=True):
            p = os.path.join(self.store, d)
            if not os.path.isdir(p):
                continue
            meta = {"label": "", "time": d, "original": False}
            try:
                meta.update(json.load(open(self._meta_path(d), encoding="utf-8")))
            except Exception:
                pass
            meta["dir"] = d
            meta["path"] = p
            meta["size"] = sum(os.path.getsize(os.path.join(r, f))
                               for r, _, fs in os.walk(p) for f in fs)
            out.append(meta)
        out.sort(key=lambda m: (not m["original"], m["dir"]), reverse=False)
        originais = [m for m in out if m["original"]]
        resto = sorted([m for m in out if not m["original"]], key=lambda m: m["dir"], reverse=True)
        return originais + resto

    def create(self, label="", original=False):
        name = time.strftime("%Y%m%d_%H%M%S")
        if original:
            name += "_ORIGINAL"
        dest = os.path.join(self.store, name)
        i = 1
        while os.path.exists(dest):
            dest = os.path.join(self.store, "%s_%d" % (name, i)); i += 1
        shutil.copytree(self.wgs_root, os.path.join(dest, "conta"))
        json.dump({"label": label, "time": time.strftime("%d/%m/%Y %H:%M:%S"),
                   "original": original},
                  open(os.path.join(dest, "_backup.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return dest

    def ensure_original(self):
        if not any(m["original"] for m in self.list()):
            return self.create("save original, antes de qualquer edicao", original=True)
        return None

    def restore(self, backup_path):
        """Restaura por cima do save atual. Faz um backup de seguranca antes."""
        src = os.path.join(backup_path, "conta")
        if not os.path.isdir(src):
            raise FileNotFoundError("backup invalido: " + backup_path)
        self.create("automatico, antes de restaurar")
        for nome in os.listdir(self.wgs_root):
            alvo = os.path.join(self.wgs_root, nome)
            if os.path.isdir(alvo):
                shutil.rmtree(alvo)
            else:
                os.remove(alvo)
        for nome in os.listdir(src):
            s = os.path.join(src, nome)
            d = os.path.join(self.wgs_root, nome)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
