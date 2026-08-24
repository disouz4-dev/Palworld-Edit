<p align="center">
  <img src="assets/logo.png" alt="Palworld Editor" width="360">
</p>

<h1 align="center">Palworld Editor</h1>

<p align="center">
  <b>🪟 Windows only</b> — save editor for <b>Palworld (Xbox / Microsoft Store / Game Pass build)</b>.
  <br>
  <b>Languages / Idiomas:</b> <a href="#-english">🇺🇸 English</a> · <a href="#-portugues-pt-br">🇧🇷 Português</a>
</p>

---

## 🇺🇸 English

> **Windows only.** Desktop app for Windows 10/11 that reads the Xbox/Game Pass save under
> `%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_*`. It does not run on macOS or Linux.
>
> **Unofficial tool**, not affiliated with Pocketpair. Use only with a save from a game you own. See [NOTICE](NOTICE.md).

### Features
- **Items** — edit any quantity, add items you don't have, per chest / storage / inventory, with in-game names and icons.
- **Character** — level, experience and status points.
- **Pals** — level, gender, IVs (HP/Attack/Defense), soul rank and the 4 passive skills, with a "suggest best passives" helper.
- **Day / night** modern theme (Windows 11 Fluent).
- **Automatic backups** and one-click restore. An untouched copy of your original save is kept forever.

This targets the **Xbox/GDK** build, which the common Steam editors do not read.

### Install
Open **PowerShell** and run:
```powershell
git clone https://github.com/disouz4-dev/Palworld-Edit.git
cd Palworld-Edit
powershell -ExecutionPolicy Bypass -File install.ps1
```
The installer checks for **Python** (installs it if missing), installs the dependencies and
creates a **Desktop shortcut** with the app icon. Then open **Palworld Editor** from your Desktop.

> No git? Download the ZIP from the green **Code** button on GitHub, extract it, then run `install.ps1`.

### Usage
1. **Close Palworld** before saving (the game overwrites the save on exit).
2. Open the app, pick your world.
3. Edit in **Items / Character / Pals**, then click **SAVE TO GAME**.
4. If anything goes wrong in-game, use **Restore backup** on the home screen.

### How it works
The Xbox save is four nested layers, all decoded from scratch in Python:
`containers.index (WGS) → container.N → CNK0 → PlZ2 (double zlib) → GVAS`. The reader/writer
round-trips the save **byte-for-byte** when nothing is edited. Names and icons are read directly
from the game's IoStore (`.utoc`/`.ucas`) via the Oodle decompressor — no FModel export needed.

### License
[MIT](LICENSE). Names and artwork belong to Pocketpair — see [NOTICE](NOTICE.md).

---

## 🇧🇷 Português (PT-BR)

> **Somente Windows.** Aplicativo de desktop para Windows 10/11 que le o save da versao
> Xbox/Game Pass em `%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_*`. Nao roda em macOS nem Linux.
>
> **Ferramenta nao oficial**, sem vinculo com a Pocketpair. Use so com um save de um jogo que voce possui. Veja o [AVISO](NOTICE.md).

### Recursos
- **Itens** — altere qualquer quantidade, adicione itens que voce nao tem, por bau / armazem / inventario, com os **nomes e icones do jogo**.
- **Personagem** — nivel, experiencia e pontos de atributo.
- **Pals** — nivel, sexo, IVs (Vida/Ataque/Defesa), rank de alma e as 4 passivas, com o botao **"sugerir melhores passivas"**.
- **Tema claro / escuro** moderno (Fluent do Windows 11).
- **Backups automaticos** e restauracao com um clique. Uma copia intocada do seu save original fica guardada para sempre.

Feito para a versao **Xbox/GDK**, que os editores comuns de Steam nao conseguem ler.

### Instalar
Abra o **PowerShell** e rode:
```powershell
git clone https://github.com/disouz4-dev/Palworld-Edit.git
cd Palworld-Edit
powershell -ExecutionPolicy Bypass -File install.ps1
```
O instalador verifica o **Python** (instala se faltar), instala as dependencias e cria um
**atalho na Area de Trabalho** com o icone. Depois e so abrir o **Palworld Editor** pela Area de Trabalho.

> Sem git? Baixe o ZIP no botao verde **Code** do GitHub, extraia e rode o `install.ps1`.

### Como usar
1. **Feche o Palworld** antes de salvar (o jogo reescreve o save ao sair).
2. Abra o app e escolha o seu mundo.
3. Edite em **Itens / Personagem / Pals** e clique em **SALVAR NO JOGO**.
4. Se algo der errado no jogo, use **Restaurar backup** na tela inicial.

### Como funciona
O save do Xbox tem quatro camadas, todas decodificadas na mao em Python:
`containers.index (WGS) → container.N → CNK0 → PlZ2 (zlib duplo) → GVAS`. O leitor/escritor
devolve o save **byte a byte identico** quando nada e editado. Nomes e icones sao lidos direto
do IoStore do jogo (`.utoc`/`.ucas`) usando o Oodle — sem precisar exportar no FModel.

### Licenca
[MIT](LICENSE). Nomes e arte pertencem a Pocketpair — veja o [AVISO](NOTICE.md).
