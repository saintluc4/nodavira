# Metodologia e limites — Nodavira 0.4.0

## O objetivo da comparação

Medir resolução DNS a partir do computador do usuário com um conjunto de nomes e condições registrados. A métrica principal não deve confundir a velocidade de uma resposta do cache do roteador com a velocidade de resolver todos os nomes de uma página moderna.

O desenho do experimento e a fórmula de comparação abaixo são escolhas explícitas do projeto. Os transportes seguem padrões DNS públicos e usam as bibliotecas documentadas nos avisos de terceiros.

## Desenho do experimento

1. Configuração: IP de destino, protocolo, URL/hostname TLS, porta, domínios, tipos A/AAAA, número de passagens, concorrência, timeout e semente aleatória são registrados.
2. Sondagem: cada faixa de concorrência consulta `example.com A`. Se todas falharem, uma segunda tentativa usa `iana.org A`. Sucesso NOERROR em pelo menos uma sonda mantém o servidor. Essa etapa está registrada em `diagnostics`, fora da amostra principal. O bloqueio dos dois nomes pode causar exclusão mesmo em um servidor funcional.
3. Primeira passagem: cada par domínio/tipo é consultado uma vez por resolvedor disponível. A ordem é embaralhada. Não se pode garantir cache vazio.
4. Repetições: os mesmos pares são consultados novamente por tantas passagens quanto configuradas. Cache pode expirar ou ser compartilhado; não se infere hit a partir da latência.
5. Intercalação: em cada bloco de até N consultas, todos os servidores disponíveis recebem o mesmo bloco, um servidor de cada vez, em ordem sorteada. Pausa de 50 ms entre lotes. Essa técnica reduz viés temporal, sem eliminar mudanças de rede.
6. Tempo: `time.perf_counter()` mede o intervalo da troca até a recepção e validação básica. O teto `asyncio.wait_for` limita a operação toda, inclusive estabelecimento e fallback. Tempo de criação do objeto de consulta não entra. Processamento local, sistema operacional e escalonamento ainda participam.
7. Lotes: medem o tempo até concluir todas as consultas paralelas daquele bloco. É uma aproximação de custo agregado DNS; não simula dependências de descoberta de domínios de uma página.

## Protocolos

- UDP com EDNS e payload de 1232 bytes; fallback a TCP para truncamento. Consultas direcionadas ao IP, fora do cache DNS do sistema operacional.
- DoH por POST `application/dns-message`, HTTP/2 habilitado e HTTP/1.1 permitido, protocolo negociado registrado. ID DNS zero. Destino fixado no IP bootstrap via transporte dnspython; hostname HTTPS e validação TLS preservados. Sem redirects ou proxy automático do ambiente.
- DoT por TLS autenticado, porta 853 por padrão, enquadramento DNS com prefixo de comprimento de dois bytes. Uma conexão sequencial por faixa de concorrência; múltiplas faixas usam múltiplas conexões. Não há pipelining numa mesma conexão DoT.
- DoH também usa um cliente persistente por faixa, até N conexões. Não reproduz o multiplexing exato de um navegador ou sistema operacional. Conexões podem expirar e reabrir; reaberturas ocorridas durante a amostra contam na latência.
- O campo `connection_new` informa criação explícita do cliente HTTP ou stream TLS. Não é um contador confiável de todos os handshakes, pois o pool HTTP pode reconectar internamente.
- Certificados e hostname são sempre validados. A versão atual não implementa DoQ nem DoH sobre HTTP/3.
- A/AAAA é tipo de registro. IPv4/IPv6 do resolvedor é família do transporte. São variáveis distintas.

## Respostas e falhas

`NOERROR` é válido; se não há registro do tipo solicitado na seção de respostas, é rotulado `NODATA`. NODATA entra na latência, mas não comprova obtenção de um endereço utilizável. O aplicativo registra valores e TTL para auditoria e não faz uma segunda consulta automática para resolver CNAME sem registro final.

NXDOMAIN, SERVFAIL, REFUSED, outros erros DNS, pacotes incompatíveis, truncamento residual, erros TLS/HTTP, timeout e respostas A/AAAA com `0.0.0.0`/`::` são falhas para esse workload. Não é uma medição universal de disponibilidade: políticas de bloqueio e nomes inexistentes também causam falhas. Não são detectados todos os possíveis modos de filtragem ou adulteração. Não se confirma a veracidade de todos os IPs retornados.

Não eliminamos outliers ou tentativas lentas. Não fazemos retentativa silenciosa que apague falhas de uma amostra. Depois de uma falha de stream TLS, a próxima consulta abre uma conexão nova. UDP truncado inclui seu fallback TCP dentro da mesma amostra e do mesmo orçamento de tempo.

O bit AD é uma declaração do resolvedor, registrado para inspeção; não é validação DNSSEC independente nem prova da segurança do provedor. DNS UDP pode ser interceptado pela rede. Esta versão não detecta interceptação transparente, DNS64 ou políticas de ECS.

## Estatísticas

Mediana, média, desvio padrão populacional, mínimo e máximo consideram somente respostas válidas. P95 usa interpolação linear com posição `(n−1) × 0,95` nos valores ordenados. O P95 de poucos dados é apenas exploratório.

Cada consulta válida custa sua latência. Cada falha custa `max(latência observada, timeout)`. A média desses custos é calculada separadamente para primeira passagem e repetições. O índice final é a média simples das duas fases (50/50), uma escolha explícita de política de comparação, não uma probabilidade estimada da navegação do usuário.

Servidores com zero respostas válidas não são apresentados como líder. Sem dados nas duas fases, o índice não é calculado. Um teste cancelado não apresenta vencedor. Durante o teste, resultados são provisórios e podem ter quantidades de amostras diferentes.

Não há teste de significância, intervalo de confiança ou garantia de estabilidade futura. Resultados de protocolos ou políticas diferentes precisam ser interpretados em contexto. Para escolher um DNS, repita o experimento e avalie diferenças de falhas, filtro, privacidade e compatibilidade.

## Fora do escopo desta versão

Cache recursivo vazio controlado exigiria infraestrutura autoritativa própria. O aplicativo não força misses usando subdomínios aleatórios de terceiros. Também não mede ping de jogos, disponibilidade de todos os serviços, qualidade de streaming, download, seleção de CDN ou tempo real de carregamento de página. Importar HAR apenas personaliza os nomes consultados; não replica tempos ou dependências da navegação.

Não altera configurações de DNS, não instala serviço de sistema e não usa telemetria.

## Referências primárias

- IETF, DNS over HTTPS: https://www.rfc-editor.org/rfc/rfc8484
- IETF, DNS over TLS: https://www.rfc-editor.org/rfc/rfc7858
- IETF, DNS over TCP: https://www.rfc-editor.org/rfc/rfc7766
- Cloudflare, endereços e configuração: https://developers.cloudflare.com/1.1.1.1/setup/
- Google, transportes seguros: https://developers.google.com/speed/public-dns/docs/secure-transports
- Quad9, serviços: https://docs.quad9.net/services/

Consultadas em 22/09/2026.

## DNS local no Linux

Um endereço como `127.0.0.53` representa um intermediário local. Nesse caso, a amostra inclui esse serviço e seu cache; não equivale a consultar diretamente o provedor upstream. O programa preserva o endereço configurado e não deduz nem substitui o upstream.
