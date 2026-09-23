# Nodavira

![Nodavira — Clareza em cada consulta](brand/banner.svg)

**Aplicativo open-source para Windows que compara resolvedores DNS com IPv4, IPv6, DNS over HTTPS e DNS over TLS.**

**[Baixar Nodavira.exe](https://github.com/saintluc4/nodavira/releases/latest/download/Nodavira.exe)** · [Versões e requisitos](https://github.com/saintluc4/nodavira/releases) · [Reportar um problema](https://github.com/saintluc4/nodavira/issues/new/choose)

O Nodavira mede o tempo e a confiabilidade das consultas DNS a partir da sua conexão, usando um conjunto de nomes que você pode personalizar. Ele considera primeira passagem, consultas repetidas, respostas lentas e falhas, com uma metodologia explícita e dados exportáveis.

O programa abre em uma **janela própria do Windows**, não altera o DNS do sistema e não exige uma instalação de Python para usar o executável. A interface, a identidade visual e o motor de medição foram desenvolvidos neste projeto. As bibliotecas utilizadas estão identificadas nos avisos de terceiros.

**Versão:** `0.3.2`, em desenvolvimento inicial. O ranking é exploratório; não certifica a qualidade de um provedor nem prevê seu desempenho futuro.

## Usar, estudar ou contribuir

| Objetivo | Onde encontrar |
|---|---|
| Usar o aplicativo | Baixe `Nodavira.exe` na seção **Releases** e abra o arquivo |
| Ler e modificar o código | Explore `nodavira/`, `static/` e `app.py` neste repositório |
| Acessar logo e recursos editáveis | Veja [`brand/`](brand/), [`static/`](static/) e o [guia de identidade](BRAND.md) |
| Entender a medição | Leia a seção Metodologia abaixo e [`METHODOLOGY.md`](METHODOLOGY.md) |
| Compilar ou contribuir | Siga [`CONTRIBUTING.md`](CONTRIBUTING.md) |

O executável é a entrega para uso imediato. O repositório contém os arquivos necessários para estudar, modificar, testar e compilar o projeto.

## Identidade

**Nodavira · Clareza em cada consulta.** O símbolo, o lettering vetorial e a paleta têm arquivos editáveis no repositório. O mesmo ícone identifica a janela e o executável. Consulte o [guia de identidade](BRAND.md) para os arquivos, a construção e a geração das versões SVG/ICO.

## Recursos

| Recurso | Implementação |
|---|---|
| DNS tradicional | UDP com fallback para TCP quando a resposta é truncada |
| DNS over HTTPS — DoH | POST em formato DNS binário, HTTP/2 habilitado e HTTP/1.1 permitido |
| DNS over TLS — DoT | TLS com validação de certificado e hostname |
| IPv4 e IPv6 | IP de destino selecionado explicitamente, inclusive no DoH |
| Tipos de registro | A e AAAA, selecionáveis separadamente |
| Métricas | Mediana, P95, média, dispersão, falhas e índice com penalidades |
| Testes personalizados | Servidores, domínios, passagens, concorrência e timeout configuráveis |
| Importação | TXT ou hostnames extraídos localmente de um HAR |
| Exportação | JSON completo e CSV com uma linha por consulta |
| Interface | Português, janela Windows e opção de execução no navegador |

## Usar o executável

Baixe somente **`Nodavira.exe`** nos anexos da seção **Releases** do repositório. Esse é o arquivo destinado ao usuário final: não é necessário baixar ZIP, código-fonte, Python ou pastas de bibliotecas.

1. Salve `Nodavira.exe` em uma pasta com permissão de escrita.
2. Abra o arquivo com dois cliques.
3. Escolha **Uso geral · completo** e clique em **Iniciar medição**.
4. Aguarde a conclusão. Clique em uma linha para ver detalhes do servidor.
5. Exporte o resultado em JSON ou CSV. O JSON também é salvo automaticamente em `reports/`, ao lado do executável.
6. Use **Encerrar aplicativo** ou feche a janela. Um teste em andamento será interrompido e os resultados parciais serão preservados quando possível.

### Requisitos

- **Windows x64**. A compilação foi verificada em Windows 10 x64; outras versões e arquiteturas não foram validadas.
- **Microsoft Edge WebView2 Runtime** para a janela integrada. [Download oficial do WebView2](https://developer.microsoft.com/microsoft-edge/webview2/).
- **.NET Framework 4.6.2 ou superior**, utilizado pelo componente de janela.
- Conectividade com os resolvedores selecionados; IPv6 funcional para testes de transporte IPv6.

O executável inclui o interpretador Python e as bibliotecas do aplicativo, mas **não inclui o instalador do WebView2 nem do .NET Framework**. Não instala serviço do Windows e não exige privilégios de administrador para operar.

Se a janela integrada não estiver disponível, é possível abrir a mesma interface no navegador:

```powershell
.\Nodavira.exe --browser
```

O arquivo não tem assinatura digital de editor. Para conferir sua integridade, compare o resultado abaixo com o SHA-256 publicado na descrição da Release pelo mantenedor:

```powershell
Get-FileHash .\Nodavira.exe -Algorithm SHA256
```

## Funcionamento

A interface HTML/CSS/JavaScript é exibida dentro de uma janela **pywebview + WebView2**. O motor Python roda no próprio computador. A comunicação usa uma API HTTP autenticada em `127.0.0.1`, numa porta temporária; a interface não depende de um site hospedado.

```text
Janela Windows / WebView2
           |
           | API local autenticada (loopback)
           v
Motor Python de benchmark
           |
           +---- UDP / TCP ----> resolvedor selecionado
           +---- HTTPS -------> resolvedor selecionado
           +---- TLS ---------> resolvedor selecionado
```

As ações de benchmark usam a API HTTP local; nenhum objeto `js_api` do aplicativo é exposto à página. A API exige token e verifica origem e cabeçalho Host. Fechar a janela solicita o cancelamento do teste, aguarda as consultas em andamento dentro de limites e encerra o servidor.

### Configuração padrão

| Parâmetro | Valor |
|---|---|
| Domínios | 30 nomes de navegação, serviços, streaming, jogos e conteúdo externo |
| Tipos de consulta | A e AAAA |
| Passagens | 3: primeira passagem e 2 repetições |
| Concorrência | Até 4 consultas simultâneas, para um servidor por vez |
| Timeout | 1.500 ms por consulta, incluindo conexão e eventual fallback |
| Seleção inicial | DNS do sistema e serviços públicos em IPv4, UDP e DoH |

DoT e IPv6 podem ser selecionados em **Servidores e domínios**. O catálogo inclui Cloudflare, Google e Quad9 e aceita servidores personalizados. A lista de nomes está em [`nodavira/config.py`](nodavira/config.py).

O volume planejado é `servidores × domínios × tipos × passagens`. Por exemplo, nove configurações, 30 nomes, dois tipos e três passagens produzem **1.620 consultas**, além das sondagens. Servidores indisponíveis na sondagem não entram nessa amostra.

**A/AAAA e IPv4/IPv6 são variáveis distintas:** o primeiro identifica o registro consultado; o segundo, o transporte até o resolvedor. Consultar AAAA por um resolvedor IPv4 não exige rota IPv6.

## Metodologia

### 1. Sondagem e preparação

O programa registra parâmetros e semente aleatória. Cada faixa de concorrência consulta `example.com A` para verificar conectividade e abrir conexões. Se todas falharem, uma segunda tentativa usa `iana.org A`. Pelo menos uma resposta considerada válida mantém o servidor no teste.

As sondagens são registradas separadamente, fora do ranking. Servidores indisponíveis continuam visíveis. O bloqueio dos dois nomes pode excluir um servidor que funcionaria para outros domínios.

### 2. Consultas comparáveis

Todos os servidores disponíveis recebem os mesmos pares domínio/tipo. Em cada passagem, a ordem desses pares é embaralhada e dividida em blocos de até N consultas. Para cada bloco, a ordem dos servidores também é embaralhada.

Um servidor recebe um bloco por vez, com pausa de 50 ms entre lotes. Isso reduz a competição criada pelo próprio teste e parte do viés de ordem, sem eliminar mudanças de rota ou carga da rede. A semente fica no JSON para reproduzir a ordem; ela não reproduz as condições externas.

O tempo é medido com `time.perf_counter()`, desde a troca até a recepção e validação básica da resposta. Reconexões e fallback ocorridos nessa operação contam. A criação do objeto da consulta fica fora da medição.

### 3. Primeira passagem e repetições

**Primeira passagem não significa cache vazio.** As consultas vão diretamente ao IP do resolvedor e não usam o cache DNS local do Windows, mas o provedor pode já ter o nome em cache. Serviços e transportes de um mesmo provedor também podem compartilhar cache.

As passagens seguintes repetem os mesmos nomes. É provável que alguns dados estejam aquecidos, mas o programa não comprova um cache hit pela latência. Não esvaziamos caches públicos nem usamos subdomínios aleatórios como equivalentes a consultas positivas reais sem cache.

### 4. Índice equilibrado

```text
custo de uma resposta válida = latência observada
custo de uma falha           = máximo(latência observada, timeout configurado)

índice = 0,5 × média dos custos da primeira passagem
       + 0,5 × média dos custos das repetições
```

**Menor é melhor dentro dessa regra.** A penalidade evita premiar um servidor que recusa consultas rapidamente. O peso das fases permanece 50/50 mesmo com mais repetições. Esse peso é uma escolha do projeto, não uma estimativa da frequência real de cache hits do usuário.

Exemplo: primeira passagem com custo médio de 40 ms e repetições com custo médio de 20 ms produzem índice de 30 ms. Em uma fase com duas respostas de 20 ms e uma falha penalizada em 1.500 ms, o custo médio é `(20 + 20 + 1500) / 3 ≈ 513,3 ms`.

### 5. Estatísticas e classificação

| Métrica ou resposta | Tratamento |
|---|---|
| Mediana, média, mínimo, máximo e dispersão | Calculados apenas sobre respostas válidas |
| P95 | Interpolação linear na posição `(n − 1) × 0,95` das latências válidas ordenadas |
| Falhas | Proporção de amostras medidas que não produziram resposta considerada válida |
| P95 do lote | Tempo para concluir consultas paralelas de um bloco; não é tempo de página |
| `NOERROR` com registro solicitado | Resposta válida |
| `NOERROR` sem registro solicitado | Rotulada `NODATA`; válida, sem comprovar endereço utilizável |
| `NXDOMAIN`, `SERVFAIL`, `REFUSED` e outros erros DNS | Falha de resolução para esse conjunto de nomes |
| Endereço `0.0.0.0` ou `::` | Rotulado `BLOCKED`; falha |
| Erro TLS/HTTP, timeout, resposta incompatível ou truncamento residual | Falha |

**Leia mediana e P95 junto com as falhas**, pois essas latências excluem as amostras inválidas. Não descartamos outliers ou tentativas lentas, nem apagamos falhas com retentativas silenciosas.

Nomes desativados e políticas de bloqueio podem produzir falhas. O percentual observado não equivale à disponibilidade universal do provedor. Também não são detectados todos os métodos de filtragem ou confirmados todos os IPs retornados.

Resultados em andamento são provisórios. Um teste interrompido não apresenta vencedor; configurações sem respostas válidas também não são apresentadas como líder.

### 6. Particularidades dos transportes

- **UDP:** EDNS com payload de 1.232 bytes; fallback TCP incluído na mesma amostra e no mesmo timeout.
- **DoH:** POST `application/dns-message`, ID zero, IP bootstrap fixado e hostname/SNI preservados. HTTP/2 habilitado, HTTP/1.1 permitido e versão negociada registrada. Sem redirects ou proxy automático do ambiente.
- **DoT:** enquadramento com prefixo de comprimento de dois bytes, TLS autenticado e porta 853 por padrão.
- **Conexões:** um cliente persistente por faixa de concorrência. Não há pipelining numa mesma conexão DoT; o conjunto de conexões DoH não reproduz exatamente o multiplexing de um navegador.
- **Erros:** encerramentos de conexão recebidos como erro contam como falhas. Aplicativos que repetem automaticamente uma operação podem apresentar comportamento diferente.
- **Reconexões:** `connection_new` registra criação explícita de cliente/stream, não todos os handshakes internos do pool HTTP.

Certificados e hostname são validados. O bit AD é registrado como declaração do resolvedor, sem validação DNSSEC independente. Veja [`METHODOLOGY.md`](METHODOLOGY.md) para discussão complementar.

## Personalizar com TXT ou HAR

A lista padrão é um ponto de partida. Edite-a ou importe um HAR exportado do painel Rede das ferramentas de desenvolvedor do navegador. Apenas os hostnames HTTP/HTTPS são extraídos localmente: caminhos, cookies, cabeçalhos e conteúdo não são enviados ao motor.

A importação adapta os nomes consultados; não replica as dependências ou os tempos de carregamento de uma página. Limites: 300 domínios, 32 configurações de servidor, 2–10 passagens, concorrência de 1–8, timeout de 500–5.000 ms, 50.000 consultas por teste e arquivos de até 30 MB.

## Limitações e interpretação

- O resultado depende de conexão, rota, horário, carga e nomes escolhidos. Repita em horários diferentes e evite downloads intensos durante o teste.
- Não há intervalos de confiança nem teste de significância. Diferenças pequenas e amostras curtas não sustentam uma escolha definitiva.
- Não mede velocidade de download, ping de partida, qualidade de streaming, seleção de CDN ou tempo de carregamento de páginas.
- Não implementa cache recursivo vazio controlado, DoQ, DoH/HTTP3 ou DNSSEC independente.
- Não detecta interceptação transparente de UDP, DNS64 ou políticas de ECS.
- Não demonstra superioridade científica sobre outros benchmarks.

## Privacidade e dados locais

Não há telemetria, conta online ou recursos da interface carregados de CDN. **As consultas são enviadas aos resolvedores selecionados**, que recebem os nomes testados. DoH e DoT protegem o transporte, mas não escondem a consulta do próprio provedor.

JSON e CSV podem conter nomes personalizados, IPs, respostas e parâmetros da rede. `reports/` e `session*.json` ficam fora do Git e do pacote de código-fonte. Não publique arquivos de sessão, pois contêm dados de acesso à API local.

## Executar pelo código-fonte

Ambiente de referência: Windows x64 e Python 3.13. Abra um terminal na raiz do projeto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --target .deps -r requirements-lock.txt
.\.venv\Scripts\python.exe app.py
```

Não é necessário ativar scripts no PowerShell. Alternativas:

```powershell
# Interface no navegador; encerra após inatividade se não houver teste em execução
.\.venv\Scripts\python.exe app.py --browser

# Somente servidor; URL/token impressos no terminal; Ctrl+C para encerrar
.\.venv\Scripts\python.exe app.py --no-browser --port 8765
```

`--session-file caminho.json` grava a URL para automação local. Esse arquivo não deve ser publicado. No modo `--no-browser`, não há encerramento automático por inatividade.

## Compilar o `.exe`

Execute em Windows x64 com Python x64, após instalar as dependências acima:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build.py
```

O PyInstaller empacota interpretador, motor, dependências da janela e interface. São gerados:

```text
dist/Nodavira.exe        # Único arquivo a anexar à Release para o usuário final
dist/SHA256.txt          # Hash para o mantenedor copiar à descrição da Release
```

As versões são registradas nos arquivos de dependências; isso não garante um binário idêntico byte a byte em ambientes diferentes. O build não assina digitalmente o executável.

## Testes

```powershell
# Testes sem consultas a DNS públicos
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Verificação dos transportes na rede real
.\.venv\Scripts\python.exe scripts/smoke_network.py

# Verificação da janela e do executável já compilado, usando rede real
.\.venv\Scripts\python.exe scripts/verify_package.py
```

Os testes de rede dependem das rotas e permissões locais; a verificação do pacote exige IPv6 funcional e inclui um controle TLS com hostname incorreto. O histórico de validação está em [`TESTING.md`](TESTING.md).

## Estrutura

```text
app.py                    # Inicialização e ciclo de vida
nodavira/config.py        # Catálogo e validação
nodavira/engine.py        # Protocolos, agendamento e estatísticas
nodavira/server.py        # API local, exportação e relatórios
nodavira/desktop.py       # Janela Windows e WebView2
static/                   # Interface em português
tests/                    # Testes automatizados
scripts/                  # Verificação, identidade e empacotamento
brand/                    # Símbolo, lettering e banner editáveis
packaging/                # Metadados do executável
build.py                  # Build da distribuição
requirements-lock.txt     # Dependências de execução
requirements-build.txt    # Ferramentas de compilação
```

## Publicar no GitHub

1. Mantenha código, README e metodologia no repositório, respeitando o `.gitignore`.
2. Crie uma tag, por exemplo `v0.3.2`, e uma **Release** correspondente.
3. Anexe somente **`dist/Nodavira.exe`** para download pelo usuário final. O executável não precisa fazer parte do histórico do código-fonte.
4. Na descrição, informe os requisitos, as mudanças, a validação e o hash de `dist/SHA256.txt`.

Para preparar uma cópia limpa do repositório, execute `python scripts/package_release.py --source`. Extraia **`Nodavira-Source.zip`** e publique seu conteúdo na raiz do repositório público, incluindo os arquivos ocultos como `.gitignore`. Assim, o código e os recursos ficam navegáveis para todos. Esse ZIP usa uma lista explícita: `.deps/`, `.venv/`, `build/`, `dist/`, relatórios e sessões ficam de fora.

O usuário final continua baixando somente `Nodavira.exe` na Release. Quem quiser o código poderá navegar, clonar ou baixar o repositório. Orientações de contribuição estão em [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Licenças

O código, a documentação e os recursos visuais próprios deste repositório são disponibilizados sob a [licença MIT](LICENSE). Ela permite usar, modificar e redistribuir o projeto, inclusive comercialmente, preservando o aviso de copyright e a licença. O texto integral está no arquivo `LICENSE`; a [Open Source Initiative](https://opensource.org/license/mit) também publica o texto da licença.

As dependências mantêm suas próprias licenças, identificadas em [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) e [`licenses/`](licenses/). A licença do projeto e esses avisos também estão incorporados ao executável e podem ser lidos no botão **Licenças** da interface, sem arquivos externos.

## Referências

- [RFC 8484 — DNS over HTTPS](https://www.rfc-editor.org/rfc/rfc8484)
- [RFC 7858 — DNS over TLS](https://www.rfc-editor.org/rfc/rfc7858)
- [RFC 7766 — DNS sobre TCP](https://www.rfc-editor.org/rfc/rfc7766)
- [Cloudflare — configuração](https://developers.cloudflare.com/1.1.1.1/setup/)
- [Google — transportes seguros](https://developers.google.com/speed/public-dns/docs/secure-transports)
- [Quad9 — serviços](https://docs.quad9.net/services/)
- [pywebview — API](https://pywebview.flowrl.com/api/)
- [pywebview — empacotamento](https://pywebview.flowrl.com/guide/freezing)
