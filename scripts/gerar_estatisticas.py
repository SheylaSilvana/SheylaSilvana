"""Gera os cards de estatísticas do perfil (assets/stats.svg e assets/langs.svg).

Roda todo dia pela automação em .github/workflows/estatisticas.yml.
Usa a API GraphQL do GitHub com o token em GITHUB_TOKEN (ou GH_TOKEN).
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USUARIO = os.environ.get("USUARIO", "SheylaSilvana")
PASTA = Path(__file__).resolve().parent.parent / "assets"

# Cores no tema tokyonight, iguais ao resto do perfil
FUNDO = "#1a1b27"
TITULO = "#70a5fd"
TEXTO = "#a9b1d6"
VALOR = "#38bdae"
ICONE = "#bf91f3"

# Notebooks guardam saídas e gráficos, então pesam muito mais que o código em si
IGNORAR = {"Jupyter Notebook"}

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def consultar():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Defina GITHUB_TOKEN ou GH_TOKEN.")
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode()
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {token}", "User-Agent": "gerar-estatisticas-perfil"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        dados = json.load(resposta)
    if "errors" in dados:
        sys.exit(f"Erro da API: {dados['errors']}")
    return dados["data"]["user"]


def numero(n):
    return f"{n:,}".replace(",", ".")


def card_estatisticas(u):
    c = u["contributionsCollection"]
    repos = u["repositories"]
    linhas = [
        ("⟳", "Contribuições no último ano", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("⇄", "Pull requests", c["totalPullRequestContributions"]),
        ("!", "Issues", c["totalIssueContributions"]),
        ("◆", "Repositórios em que contribuí", u["repositoriesContributedTo"]["totalCount"]),
        ("▣", "Repositórios públicos", repos["totalCount"]),
    ]
    altura = 60 + len(linhas) * 26 + 10
    itens = []
    for i, (icone, rotulo, valor) in enumerate(linhas):
        y = 70 + i * 26
        itens.append(
            f'<text x="25" y="{y}" class="ic">{icone}</text>'
            f'<text x="50" y="{y}" class="tx">{escape(rotulo)}:</text>'
            f'<text x="330" y="{y}" class="vl" text-anchor="end">{numero(valor)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{altura}" viewBox="0 0 360 {altura}">
<style>
.tt{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TITULO}}}
.tx{{font:600 14px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXTO}}}
.vl{{font:700 14px 'Segoe UI',Ubuntu,Sans-Serif;fill:{VALOR}}}
.ic{{font:700 14px 'Segoe UI',Ubuntu,Sans-Serif;fill:{ICONE}}}
</style>
<rect width="100%" height="100%" rx="6" fill="{FUNDO}"/>
<text x="25" y="35" class="tt">Estatísticas no GitHub</text>
{''.join(itens)}
</svg>
"""


def card_linguagens(u):
    tamanhos = {}
    cores = {}
    for repo in u["repositories"]["nodes"]:
        for aresta in repo["languages"]["edges"]:
            nome = aresta["node"]["name"]
            if nome in IGNORAR:
                continue
            tamanhos[nome] = tamanhos.get(nome, 0) + aresta["size"]
            cores[nome] = aresta["node"]["color"] or "#858585"
    total = sum(tamanhos.values()) or 1
    principais = sorted(tamanhos.items(), key=lambda x: -x[1])[:6]

    barra, x = [], 25
    largura_barra = 310
    for nome, tam in principais:
        w = largura_barra * tam / total
        barra.append(f'<rect x="{x:.1f}" y="50" width="{w:.1f}" height="8" fill="{cores[nome]}"/>')
        x += w

    legenda = []
    for i, (nome, tam) in enumerate(principais):
        col, lin = i % 2, i // 2
        lx, ly = 25 + col * 160, 85 + lin * 24
        legenda.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{cores[nome]}"/>'
            f'<text x="{lx + 16}" y="{ly}" class="tx">{escape(nome)} {100 * tam / total:.1f}%</text>'
        )
    altura = 85 + ((len(principais) + 1) // 2) * 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{altura}" viewBox="0 0 360 {altura}">
<style>
.tt{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TITULO}}}
.tx{{font:400 12px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXTO}}}
</style>
<rect width="100%" height="100%" rx="6" fill="{FUNDO}"/>
<text x="25" y="35" class="tt">Linguagens mais usadas</text>
<clipPath id="arredonda"><rect x="25" y="50" width="{largura_barra}" height="8" rx="4"/></clipPath>
<g clip-path="url(#arredonda)">{''.join(barra)}</g>
{''.join(legenda)}
</svg>
"""


def main():
    u = consultar()
    PASTA.mkdir(exist_ok=True)
    (PASTA / "stats.svg").write_text(card_estatisticas(u), encoding="utf-8")
    (PASTA / "langs.svg").write_text(card_linguagens(u), encoding="utf-8")
    print(f"Cards gerados em {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")


if __name__ == "__main__":
    main()
