# Regras do Financeiro (Caixa e Ranking)

> Fonte da verdade das regras de negócio do módulo financeiro. Sempre que uma regra
> mudar, atualize este arquivo junto com o código (`backend/app/routers/financial.py`).

## Conceitos

- **Rodada em aberto**: rodada com `is_current = True` e `is_finalized = False`. Ainda
  não foi finalizada, então seu dinheiro ainda não foi assentado no acumulado.
- **Rodada "da noite"**: a rodada exibida nos campos `*_noite` do resumo financeiro.
  É a rodada em aberto, se houver; senão, é a última rodada finalizada.
- **Rodada histórica**: toda rodada finalizada que **não** é a rodada "da noite".

## Constantes

| Constante | Valor | Descrição |
|---|---|---|
| `RANKING_PCT_FIXED` | 7,5% | fatia da base que vai para o ranking semestral |
| `CAIXA_ANTERIOR_PCT_FIXED` | 7,5% | fatia da base que fica retida no caixa |
| Premiação | 85% | fatia da base paga aos vencedores (70% para o 1º, 30% para o 2º) |
| `ENTRY_FEE` | R$ 10,00 | taxa por buy-in (não incide sobre rebuy) |
| `DEALER_FEE` | R$ 50,00 | taxa do dealer, cobrada quando a rodada tem 7+ jogadores; paga pelo caixa (não reduz a premiação) |

7,5% + 7,5% + 85% = 100% da "base" de cada rodada.

## Fórmulas por rodada

Para uma rodada com jogadores `rps`:

```
gross            = Σ (buyin_i * buyin_value + rebuy_i * rebuy_value)
addons_value     = Σ addon_i * addon_value
total_bruto      = gross + addons_value
total_fee        = Σ buyin_i * ENTRY_FEE                 (só conta buy-ins)
dealer_fee       = DEALER_FEE se num_jogadores >= 7, senão 0

total_arrecadado = gross + addons_value
taxa_total       = total_fee
base             = max(total_arrecadado - total_fee, 0)   # o dealer NÃO reduz a base
caixa_noite      = max(total_fee + base * 7,5% - dealer_fee, 0) # arrecadacao do caixa

premiacao_total  = base * 85%
premiacao_1      = premiacao_total * 70%
premiacao_2      = premiacao_total * 30%
ranking_noite    = base * 7,5%
```

No resumo da rodada, os descontos são exibidos como:

- **Caixa**: `R$ 10 por buy-in + 7,5% da base - dealer_fee`.
- **Ranking**: `7,5% da base`.

O `total_arrecadado_bruto` é `gross + addons_value`, antes desses descontos.

## Regra do Caixa

- **Rodada fechada (finalizada)**: assim que finaliza, contribui para o acumulado
  `total_fee + base * 7,5% - dealer_fee` — imediatamente, mesmo que nenhuma rodada nova tenha
  começado depois dela.
- **Rodada em aberto (não finalizada)**: exibe e soma provisoriamente o mesmo valor
  `total_fee + base * 7,5% - dealer_fee` com os buy-ins registrados até o momento. Quando novos
  buy-ins entram, o valor é recalculado; ao fechar, entra no acumulado uma única vez.
- **Despesas**: abatidas uma única vez no `caixa_total`, nunca na premiação, no
  `caixa_anterior` nem no `caixa_noite`. São a soma de todas as linhas da tabela no
  momento da consulta.

```
caixa_anterior = Financial.caixa_anterior (valor base editável)
               + Σ (rodadas finalizadas anteriores à "noite": total_fee + base * 7,5% - dealer_fee)

caixa_total    = caixa_anterior + caixa_noite - Σ despesas cadastradas
```

Despesas não reduzem `premiacao_total`; reduzem somente o caixa acumulado.

## Regra do Ranking

Mesma lógica do caixa, com uma diferença: o ranking **nunca** soma o valor da
rodada "da noite" dentro de `ranking_anterior` — ela sempre entra separada em
`ranking_noite`, para que a soma `anterior + noite` sempre bata com `total`.

```
ranking_anterior = Financial.ranking_anterior (valor base editável)
                 + Σ (rodadas finalizadas, exceto a "da noite": base * 7,5%)

ranking_total    = ranking_anterior + ranking_noite   (sempre)
```

O ranking (pontos, não dinheiro) exibido em `/ranking` é independente disso: soma o
campo `score` das rodadas com `is_active_in_ranking = True`, sem relação com os valores
financeiros acima.

## Editando os valores base

- `PUT /api/financial` sobrescreve `Financial.caixa_anterior` e `Financial.ranking_anterior`
  — o valor acumulado "antes da Rodada 01" (antes de o app existir/rastrear tudo).
- Se uma despesa antiga (ex: compra de equipamento) já estava embutida no valor base
  informado, ela **não** deve continuar na tabela de despesas — senão é descontada
  duas vezes.
