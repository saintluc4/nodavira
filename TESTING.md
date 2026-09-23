# Verificação — Nodavira 0.3.2

Executada em 22/09/2026, Windows 10 x64, na conexão local disponível durante o desenvolvimento.

## Testes automatizados

38 testes aprovados em `python -m unittest discover -s tests -v`:

- normalização de domínios e IDN, limites de configuração e deduplicação de servidores;
- distinção entre família de transporte e tipo de registro;
- percentil, ausência de dados, falhas rápidas penalizadas e peso constante das fases;
- mensagens DoH binárias, correspondência de ID, tipo de conteúdo, tamanho, erros HTTP e timeouts;
- respostas NODATA/NXDOMAIN, endereços de bloqueio e registro de fallback TCP;
- mesmo conjunto de consultas por servidor, ordem reproduzível, cancelamento e fechamento de clientes;
- proteção de fórmulas no CSV;
- autenticação da API local, origem, cabeçalho Host, configuração inválida e restrição de arquivos estáticos.
- inicialização da janela, configuração do WebView2, encerramento pela API e cancelamento em caso de falha de inicialização;
- exclusão de dados locais do pacote público e resolução dos links relativos do README.
- geração do pacote de código em uma cópia limpa, sem executável previamente compilado.

## Rede real e interface — ensaio original da versão 0.1.0

UDP, DoH e DoT responderam via IPv4 e IPv6. HTTPS negociou HTTP/2. Um benchmark completo pela interface produziu 1.620 amostras em nove configurações, com 180 amostras por configuração, em aproximadamente 55 segundos. Console da interface sem erros nesse fluxo. Detalhes de servidor e tela de configuração foram inspecionados no navegador integrado.

Houve falhas reais de transporte (inclusive encerramento de conexões DoH) no benchmark completo. Elas permanecem no relatório e no índice, conforme a metodologia. Não devem ser generalizadas como uma taxa permanente de falhas do provedor.

Após esse ensaio, quatro nomes da lista inicial foram substituídos por hostnames de conteúdo verificados: `raw.githubusercontent.com`, `download.windowsupdate.com`, `static-cdn.jtvnw.net` e `i.scdn.co`. A quantidade padrão permanece em 30 domínios.

## Executável independente

`python scripts/verify_package.py` copia somente o executável para uma nova pasta de verificação vazia, sem código-fonte, documentação ou `.deps` junto dele. Na versão 0.3.2, também exige que a janela Windows oculta de teste carregue seu conteúdo com o renderer `edgechromium`. Os controles incluem:

- 48 de 48 consultas válidas: oito para cada combinação UDP/DoH/DoT × IPv4/IPv6;
- HTTP/2 no DoH;
- endpoint DoT com hostname incorreto rejeitado por `SSLCertVerificationError`, sem ranking;
- JSON válido e CSV com 48 linhas de dados mais cabeçalho;
- cancelamento preservando o estado `cancelled`;
- encerramento do processo após a verificação.
- avisos de bibliotecas servidos de dentro do executável, com conteúdo idêntico ao arquivo gerado na compilação.

O relatório estruturado de cada execução bem-sucedida fica em `reports/packaged-verification.json`, incluindo o estado da janela e o SHA-256 do binário. Compare esse hash com `dist/SHA256.txt`. Relatórios locais não são incluídos nos arquivos ZIP públicos.

Na verificação final de 22/09/2026, a versão 0.3.2 carregou a janela com WebView2, completou 48/48 consultas válidas nos seis transportes, exportou 49 linhas CSV (cabeçalho + 48 dados), rejeitou três sondagens com hostname TLS incorreto e cancelou/encerrou corretamente o teste seguinte. A janela foi executada em modo oculto de teste; isso valida inicialização e integração, sem equivaler a uma inspeção visual de cada controle nativo.

## Limites da validação

A identidade visual atual foi inspecionada no navegador durante a preparação da versão 0.3.0, incluindo monograma, lettering, cores e navegação para configurações; não houve erros ou avisos no console nessa inspeção. O diálogo de licenças foi conferido visualmente na versão 0.3.1. A versão 0.3.2 mantém esses componentes e inclui a licença MIT no conteúdo incorporado, cuja integridade é verificada no teste do executável. Seus metadados identificam Nodavira 0.3.2; o ICO inclui nove tamanhos. A API local e os arquivos de relatório/exportação usam o nome Nodavira.

Não houve teste em outros computadores, todas as versões do Windows, todos os roteadores, links congestionados ou todos os provedores. DoQ/HTTP/3, cache recursivo vazio e DNSSEC independente não são funcionalidades desta versão. Os resultados não constituem validação científica de superioridade sobre outro benchmark nem uma recomendação permanente de DNS.
