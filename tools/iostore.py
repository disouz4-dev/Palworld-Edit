# -*- coding: utf-8 -*-
"""Leitor minimo do IoStore da UE5 (.utoc/.ucas) do Palworld.

So o necessario para localizar um arquivo pelo caminho e extrair seus bytes
(descomprimindo os blocos Oodle). Nao interpreta .uasset - serve para tirar
arquivos crus como .locres. Reaproveita o Oodle via tools/pak.py.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # oodle_dec
import paths

UTOC = paths.iostore_base() + ".utoc"
UCAS = paths.iostore_base() + ".ucas"

class R:
    def __init__(s,b,o=0): s.b=b; s.o=o
    def u32(s): v=struct.unpack_from("<I",s.b,s.o)[0]; s.o+=4; return v
    def fstr(s):
        n=struct.unpack_from("<i",s.b,s.o)[0]; s.o+=4
        if n==0: return ""
        if n<0:
            n=-n; v=s.b[s.o:s.o+n*2-2].decode("utf-16-le","replace"); s.o+=n*2
        else:
            v=s.b[s.o:s.o+n-1].decode("utf-8","replace"); s.o+=n
        return v

def _u40be(b):  # 5 bytes big-endian
    return int.from_bytes(b, "big")

def carregar():
    d = open(UTOC,"rb").read()
    assert d[:16]==b"-==--==--==--==-"
    ver=d[16]
    o=20
    (hsize,nent,nblk,blkstruct,nmeth,methlen,cbs,diridx_sz,nparts)=struct.unpack_from("<IIIIIIIII",d,o)
    o=hsize  # pula o resto do header de 144 bytes
    # arrays
    chunk_o = o
    o += nent*12                    # FIoChunkId
    offlen_o = o
    o += nent*10                    # FIoOffsetAndLength
    # perfect hash: precisa dos contadores do header
    phseeds = struct.unpack_from("<I", d, 84)[0]
    nowo    = struct.unpack_from("<I", d, 96)[0]
    if phseeds>0: o += phseeds*4
    if nowo>0:    o += nowo*4
    blocks_o = o
    o += nblk*12                    # compression blocks
    meth_o = o
    o += nmeth*methlen              # metodos
    # (assinaturas: assumimos nao assinado)
    dir_o = o
    diridx = d[dir_o:dir_o+diridx_sz]
    metodos = ["None"]
    for i in range(nmeth):
        metodos.append(d[meth_o+i*methlen:meth_o+i*methlen+methlen].split(b"\x00")[0].decode("ascii","replace"))
    return dict(d=d, ver=ver, nent=nent, nblk=nblk, cbs=cbs,
                offlen_o=offlen_o, blocks_o=blocks_o, diridx=diridx, metodos=metodos)

def _dir_index(t):
    r=R(t["diridx"])
    mount=r.fstr()
    ndir=r.u32(); dirs=[struct.unpack_from("<IIII",t["diridx"],r.o+i*16) for i in range(ndir)]; r.o+=ndir*16
    nfile=r.u32(); files=[struct.unpack_from("<III",t["diridx"],r.o+i*12) for i in range(nfile)]; r.o+=nfile*12
    nstr=r.u32(); strs=[]
    for _ in range(nstr): strs.append(r.fstr())
    NONE=0xFFFFFFFF
    saida={}
    def anda(di, prefixo):
        while di!=NONE:
            nome_i,child,sib,firstfile = dirs[di]
            nome = strs[nome_i] if nome_i!=NONE else ""
            p = prefixo + ("/" if prefixo and nome else "") + nome
            fi=firstfile
            while fi!=NONE:
                fnome_i,nextf,userdata = files[fi]
                fn = strs[fnome_i] if fnome_i!=NONE else ""
                saida[p+"/"+fn] = userdata
                fi=nextf
            if child!=NONE: anda(child, p)
            di=sib
    anda(0, mount.rstrip("/"))
    return saida

def extrair(t, chunk_idx):
    d=t["d"]; cbs=t["cbs"]
    ol = d[t["offlen_o"]+chunk_idx*10 : t["offlen_o"]+chunk_idx*10+10]
    off=_u40be(ol[:5]); length=_u40be(ol[5:10])
    first=off//cbs
    saida=b""
    ucas=open(UCAS,"rb")
    bi=first
    restam = (off % cbs) + length
    consumido_ini = off % cbs
    while len(saida) < consumido_ini + length:
        e=d[t["blocks_o"]+bi*12 : t["blocks_o"]+bi*12+12]
        boff=int.from_bytes(e[0:5],"little")
        csz=int.from_bytes(e[5:8],"little")
        usz=int.from_bytes(e[8:11],"little")
        meth=e[11]
        ucas.seek(boff); comp=ucas.read(csz)
        saida += comp if meth==0 else pak.oodle_dec(comp, usz)
        bi+=1
    ucas.close()
    return saida[consumido_ini:consumido_ini+length]

if __name__=="__main__":
    t=carregar()
    print("entradas=%d blocos=%d cbs=%d metodos=%s" % (t["nent"],t["nblk"],t["cbs"],t["metodos"]))
    idx=_dir_index(t)
    print("arquivos no indice:", len(idx))
    locs=sorted(k for k in idx if k.lower().endswith("game.locres") and "Game/" in k)
    for k in locs: print("  ", k, "chunk", idx[k])
    alvo=[k for k in idx if "pt-BR/Game.locres" in k]
    if alvo:
        b=extrair(t, idx[alvo[0]])
        MG=bytes([0x0E,0x14,0x74,0x75,0x67,0x4A,0x03,0xFC,0x4A,0x15,0x90,0x9D,0xC3,0x37,0x7F,0x1B])
        print("\npt-BR/Game.locres: %d bytes | magic ok: %s" % (len(b), b[:16]==MG))
