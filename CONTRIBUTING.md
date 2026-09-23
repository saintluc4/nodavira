# Contribuir com o Nodavira

O código do motor, a interface, a metodologia e os recursos visuais estão disponíveis neste repositório sob a [licença MIT](LICENSE). Você pode estudar a implementação, propor melhorias e compilar sua própria versão.

## Preparar o ambiente

Use Windows x64 e Python 3.13. Para a janela integrada, também são necessários WebView2 Runtime e .NET Framework 4.6.2 ou superior.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --target .deps -r requirements-lock.txt
.\.venv\Scripts\python.exe app.py
```

Leia o [README](README.md) para executar no navegador ou entender os parâmetros. A [metodologia](METHODOLOGY.md) documenta as regras de comparação e os limites dos resultados.

## Propor uma mudança

Abra uma issue para descrever um problema ou discutir uma alteração de metodologia. Em um pull request, explique o comportamento anterior, o que muda e como verificou o resultado. Inclua testes quando uma mudança alterar protocolos, estatísticas, tratamento de falhas ou validação de entrada.

Para problemas de DNS, informe a versão, o protocolo, a família IPv4/IPv6 e um exemplo mínimo. Revise os dados antes de compartilhar relatórios: eles podem conter domínios personalizados, endereços da rede e nomes de arquivos locais. Arquivos `session*.json` contêm acesso à API local e não devem ser publicados.

## Verificar e compilar

```powershell
# Testes sem consultas a DNS públicos
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Compilar o executável de arquivo único
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build.py

# Conferir o executável com consultas reais; exige conectividade IPv4 e IPv6
.\.venv\Scripts\python.exe scripts/verify_package.py
```

O build gera `dist/Nodavira.exe`. As versões fixadas facilitam repetir o ambiente; não garantem binários idênticos byte a byte. O build não assina o executável.

## Recursos visuais

Os SVG editáveis e o PNG estão em `brand/`; favicon, lettering da interface e ICO ficam em `static/`. O [guia de identidade](BRAND.md) explica as coordenadas, a paleta e o comando para regenerar esses arquivos. Não é necessário um editor proprietário.

## Distribuição

Mantenha o código e a documentação navegáveis na raiz do repositório público. Para quem deseja apenas usar o aplicativo, anexe `Nodavira.exe` à Release. O GitHub também oferece o código da tag em seus próprios arquivos de código-fonte.

`python scripts/package_release.py --source` gera uma cópia limpa dos arquivos públicos para preparar o repositório. A extração desse ZIP deve resultar nos arquivos e pastas do projeto; não publique apenas o ZIP como substituto do código navegável.
