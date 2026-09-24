# Nodavira no Linux

Adaptei a janela para **GTK 3 + WebKitGTK 4.1**, por meio do pywebview. Uso o mesmo motor de benchmark, interface, catálogo e regras de pontuação da versão Windows. Não utilizo Wine nem WebView2 no Linux.

O alvo inicial do pacote Debian é **Ubuntu 24.04 ou posterior e Linux Mint 22 ou posterior**. Para Arch, o pacote usa as bibliotecas dos repositórios da distribuição. Python 3.11 ou posterior é necessário. O código é independente de arquitetura; isso não significa que todas as arquiteturas e distribuições tenham sido testadas.

## Ubuntu e Linux Mint

Depois de obter o `.deb` da versão desejada, abra-o no instalador de aplicativos da distribuição ou execute, na pasta do download:

```bash
sudo apt install ./nodavira_0.4.0-1_all.deb
```

O APT instala Python, PyGObject, GTK e WebKitGTK quando necessário. As bibliotecas Python do benchmark acompanham o pacote em uma pasta privada; não são instaladas no Python global via pip. É necessária conexão para obter dependências que ainda não estejam instaladas. Ubuntu 22.04 e Mint 21 não fazem parte do alvo inicial.

Abra **Nodavira** no menu de aplicativos ou execute `nodavira`. O aplicativo funciona como usuário comum. Somente a instalação do pacote requer privilégios administrativos.

Para remover:

```bash
sudo apt remove nodavira
```

## Arch Linux: pacman

O `PKGBUILD` utiliza `makepkg` e as dependências Python do Arch. Depois de obter o pacote construído pelo workflow Linux:

```bash
sudo pacman -U ./nodavira-0.4.0-1-any.pkg.tar.zst
nodavira
```

O pacote local não cria um repositório pacman. `pacman -S nodavira` só funcionaria se um repositório configurado oferecesse o pacote. Para remover, use `sudo pacman -Rns nodavira` e revise a lista de dependências proposta.

### Preparar o AUR e o yay

**O projeto ainda não foi publicado no AUR.** Preparar `PKGBUILD` e `.SRCINFO` não cria uma entrada automaticamente. Não há, neste estágio, um comando `yay -S nodavira` funcional confirmado.

O empacotamento gera um `PKGBUILD` com versão e SHA-256 do arquivo-fonte. O workflow Arch gera `.SRCINFO` usando `makepkg --printsrcinfo`. Para publicar:

1. Valide os jobs Ubuntu e Arch do workflow Linux e teste a interface em uma sessão gráfica real.
2. Publique `nodavira-0.4.0.tar.gz` na Release `v0.4.0`, com os bytes exatos usados para gerar o SHA-256 do `PKGBUILD`.
3. Verifique a disponibilidade do nome no AUR e prepare uma conta com chave SSH.
4. Envie somente `PKGBUILD` e `.SRCINFO` ao repositório AUR correspondente, seguindo as regras do AUR.
5. Após confirmar a publicação, documente `yay -S nodavira` como opção de instalação.

Não uso `sha256sums=('SKIP')`. Cada alteração no arquivo-fonte exige regenerar o checksum. As atualizações das bibliotecas no Arch são gerenciadas pelo pacman; isso difere das versões Python fixadas no `.deb`.

## Dados, DNS do sistema e exportações

Os relatórios automáticos ficam em `$XDG_DATA_HOME/nodavira/reports`, ou `~/.local/share/nodavira/reports` quando a variável não está definida ou não contém um caminho absoluto. Não gravo relatórios em `/usr`, junto ao programa instalado. JSON e CSV também podem ser baixados pelos botões de exportação.

O item **DNS do sistema** usa os endereços reportados pelo dnspython a partir da configuração do sistema. Em máquinas com `systemd-resolved`, pode aparecer `127.0.0.53`. Esse endereço é um intermediário local e pode ter cache próprio: a medição inclui esse caminho, não identifica automaticamente o DNS upstream. VPNs e configuração por interface podem produzir diferenças. Não altero `/etc/resolv.conf`, NetworkManager ou systemd-resolved.

## Executar pelo código-fonte

Ubuntu/Mint:

```bash
sudo apt install python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 ca-certificates xdg-utils
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-deps -r requirements-linux-lock.txt
.venv/bin/python app.py
```

`--system-site-packages` permite usar o PyGObject da distribuição. Crie o ambiente no próprio Linux; não copie `.venv` ou `.deps` do Windows. Não execute `sudo pip`.

Arch:

```bash
sudo pacman -S --needed python python-dnspython python-httpx python-h2 python-pywebview python-gobject python-cairo gtk3 webkit2gtk-4.1 ca-certificates xdg-utils
python app.py
```

Os modos `--browser` e `--no-browser` também funcionam no Linux. A janela precisa de uma sessão gráfica X11 ou Wayland com suporte ao GTK/WebKit disponível. Sem sessão gráfica, use `--no-browser` para testes locais; a API continua restrita ao loopback e exige token.

## Gerar os pacotes

Debian/Ubuntu, a partir de um checkout limpo:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps --target build/linux-deps -r requirements-linux-lock.txt
.venv/bin/python scripts/package_linux.py --vendor build/linux-deps
```

O script produz em `dist/linux/` o `.deb`, o arquivo-fonte `.tar.gz`, `SHA256SUMS` e a pasta `aur/` com `PKGBUILD` e uma cópia do arquivo-fonte para builds locais. Ele inclui apenas distribuições Python explicitamente fixadas e independentes de arquitetura, e omite auxiliares nativos do Windows. Python, GTK e WebKit continuam sendo dependências do sistema, atualizadas pela distribuição. Esse formato não é um executável congelado nem um AppImage.

No Arch, para gerar e instalar o pacote a partir do código:

```bash
python scripts/package_linux.py
cd dist/linux/aur
makepkg -si
makepkg --printsrcinfo > .SRCINFO
```

`makepkg` deve rodar como usuário comum. Como o arquivo-fonte está ao lado do PKGBUILD, não é necessário que a Release já exista para o build local. A instalação de dependências e do pacote pode pedir a senha do sudo.

## Validação

O workflow [Linux packages](../.github/workflows/linux.yml) constrói e instala o `.deb` no Ubuntu 24.04 e o pacote `makepkg` em um ambiente Arch. O teste de integração abre a janela GTK em Xvfb, faz consultas a um servidor DNS de teste no loopback, confere autenticação, exportações, gravação em XDG e encerramento. Não depende de DNS público nem desabilita o sandbox do WebKit.

O arquivo do workflow define a validação; somente uma execução concluída com sucesso comprova que ela passou. Xvfb não substitui testes visuais no desktop do Mint, em Wayland, em outras arquiteturas ou com diferentes placas gráficas. Os limites observados estão em [TESTING.md](../TESTING.md).

Referências: [pywebview no Linux](https://pywebview.flowrl.com/guide/installation.html), [PKGBUILD](https://man.archlinux.org/man/PKGBUILD.5.en), [formato Debian](https://manpages.debian.org/bookworm/dpkg-dev/deb.5.en.html).
