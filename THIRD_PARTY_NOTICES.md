# Bibliotecas e avisos

O código, a documentação e os recursos visuais próprios do Nodavira são disponibilizados sob a licença MIT, no arquivo `LICENSE`. O projeto também utiliza as bibliotecas de terceiros identificadas abaixo, que mantêm suas próprias licenças. Os desenhos vetoriais da marca são definidos em `scripts/generate_brand.py`.

O executável inclui Python e bibliotecas de terceiros. Os respectivos direitos permanecem com os autores. Textos de licença são incorporados ao executável e acessíveis pelo botão Licenças. No código-fonte, os originais estão na pasta `licenses`.

| Componente | Licença | Origem |
|---|---|---|
| Python | PSF e avisos incluídos no LICENSE | https://www.python.org/ |
| dnspython | ISC | https://www.dnspython.org/ |
| HTTPX / HTTPCore | BSD 3-Clause | https://www.python-httpx.org/ |
| AnyIO | MIT | https://anyio.readthedocs.io/ |
| h2 / hpack / hyperframe | MIT | https://python-hyper.org/ |
| h11 | MIT | https://github.com/python-hyper/h11 |
| idna | BSD 3-Clause | https://github.com/kjd/idna |
| certifi | MPL 2.0 | https://github.com/certifi/python-certifi |
| typing_extensions | PSF | https://github.com/python/typing_extensions |
| pywebview | BSD 3-Clause | https://pywebview.flowrl.com/ |
| pythonnet | MIT | https://pythonnet.github.io/ |
| clr_loader | Licença incluída em licenses/ | https://github.com/pythonnet/clr-loader |
| cffi | MIT-0 e avisos da distribuição | https://cffi.readthedocs.io/ |
| pycparser | BSD 3-Clause | https://github.com/eliben/pycparser |
| bottle | MIT | https://bottlepy.org/ |
| proxy_tools | MIT | https://github.com/jtushman/proxy_tools |
| WebView2 SDK (DLLs fornecidas com pywebview) | Termos da Microsoft | https://www.nuget.org/packages/Microsoft.Web.WebView2/ |
| PyInstaller (empacotamento) | GPL com exceção para aplicações empacotadas | https://pyinstaller.org/ |

A execução usa as versões de `requirements-lock.txt`. As ferramentas de compilação estão em `requirements-build.txt`. Pillow é utilizado apenas para gerar o PNG e o ICO; não faz parte do motor de medição. O código-fonte do aplicativo acompanha a entrega.

O Microsoft Edge WebView2 Runtime e o .NET Framework são pré-requisitos do sistema, instalados separadamente. Não são incorporados ao executável do projeto.
