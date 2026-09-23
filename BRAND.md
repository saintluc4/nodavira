# Identidade do Nodavira

**Nodavira · Clareza em cada consulta.**

O nome identifica este aplicativo de análise de resolvedores DNS. A identidade foi desenhada para o projeto: um monograma em forma de fita, letras vetoriais e uma paleta violeta com um ponto âmbar.

## Construção

O símbolo é construído em uma grade de 64 × 64 unidades. Uma faixa forma o “N”; um pequeno terminal separado sugere o destino de uma consulta. A separação continua visível em tamanhos pequenos. O lettering `NODAVIRA` usa traços próprios sobre uma grade de 22 × 32 unidades, com curvas e espaçamento definidos no código. Os arquivos do lettering não dependem de fontes instaladas.

Os desenhos são definidos em [`scripts/generate_brand.py`](scripts/generate_brand.py). Não foram importados logotipos, ícones de bancos de imagens nem recursos gráficos de outros aplicativos. A interface usa fontes do sistema; não há arquivos de fontes redistribuídos. O banner usa texto auxiliar em Segoe UI/Arial, com alternativa sans-serif.

## Paleta

| Cor | Hex | Uso |
|---|---|---|
| Tinta | `#201B32` | Navegação, fundo do ícone e banner |
| Violeta | `#7252DB` | Símbolo sobre fundo claro |
| Violeta de ação | `#6544C4` | Botões e links sobre superfícies claras |
| Lilás | `#C7B6FF` | Símbolo sobre fundo escuro |
| Âmbar | `#F5BD64` | Terminal do símbolo e detalhes |
| Papel | `#F7F5FB` | Fundo da interface |

Verde e vermelho continuam sendo cores de estado: sucesso e falha. A cor da marca não muda o significado dos resultados.

## Arquivos

| Arquivo | Uso |
|---|---|
| [`brand/mark.svg`](brand/mark.svg) | Símbolo vetorial, fundo transparente |
| [`brand/wordmark.svg`](brand/wordmark.svg) | Assinatura completa para fundo claro |
| [`brand/wordmark-light.svg`](brand/wordmark-light.svg) | Assinatura completa para fundo escuro |
| [`brand/banner.svg`](brand/banner.svg) | Cabeçalho do README e apresentação do projeto |
| [`brand/app-icon.png`](brand/app-icon.png) | Ícone de 256 × 256 pixels |
| [`static/favicon.svg`](static/favicon.svg) | Ícone da interface |
| [`static/wordmark.svg`](static/wordmark.svg) | Assinatura utilizada na navegação |
| [`static/app.ico`](static/app.ico) | Ícone do executável e da janela do Windows |

O ICO inclui 16, 20, 24, 32, 40, 48, 64, 128 e 256 pixels. Preserve proporções, cores e uma margem livre de pelo menos 8 unidades da grade do símbolo. Evite efeitos, estiramento e uso do detalhe âmbar como indicador de resultado.

## Gerar os recursos

Com as dependências de compilação instaladas:

```powershell
python scripts/generate_brand.py
```

O comando recria SVG, PNG e ICO a partir das mesmas coordenadas. `python build.py` executa essa geração antes de compilar, incorporando o ICO ao `.exe`.

## Escopo

Este guia documenta a criação e o uso dos recursos do projeto; não certifica exclusividade nem disponibilidade jurídica do nome ou símbolo. Os desenhos, seus arquivos editáveis e o gerador são disponibilizados sob a [licença MIT](LICENSE). As orientações visuais deste guia são recomendações de consistência, não condições adicionais à licença. As dependências conservam suas licenças e atribuições, descritas em [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
