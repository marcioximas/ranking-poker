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
| `RANKING_PCT_FIXED` | 7,5% | fatia do total arrecadado que vai para o ranking semestral |
| `CAIXA_ANTERIOR_PCT_FIXED` | 7,5% | fatia do total arrecadado que fica retida no caixa |
| Premiação | 85% | fatia do total arrecadado paga aos vencedores (70% para o 1º, 30% para o 2º) |
| `DEALER_FEE` | R$ 50,00 | taxa do dealer, cobrada quando a rodada tem 7+ jogadores; paga pelo caixa (não reduz a premiação) |

O rake é 15% do total arrecadado: 7,5% vai para o ranking, 7,5% para o caixa e
os 85% restantes são pagos como premiação.

## Fórmulas por rodada

Para uma rodada com jogadores `rps`:

```
gross            = Σ (buyin_i * buyin_value + rebuy_i * rebuy_value)
addons_value     = Σ addon_i * addon_value
total_bruto      = gross + addons_value
dealer_fee       = DEALER_FEE se num_jogadores >= 7, senão 0

total_arrecadado = gross + addons_value
base             = total_arrecadado
caixa_noite      = max(base * 7,5% - dealer_fee, 0) # arrecadacao do caixa

premiacao_total  = base * 85%
premiacao_1      = premiacao_total * 70%
premiacao_2      = premiacao_total * 30%
ranking_noite    = base * 7,5%
```

No resumo da rodada, a divisão é exibida como:

- **Caixa**: `7,5% do total arrecadado - dealer_fee`.
- **Ranking**: `7,5% do total arrecadado`.

O `total_arrecadado_bruto` é `gross + addons_value`, antes desses descontos.

## Regra do Caixa

- **Rodada fechada (finalizada)**: assim que finaliza, contribui para o acumulado
  `base * 7,5% - dealer_fee` — imediatamente, mesmo que nenhuma rodada nova tenha
  começado depois dela.
- **Rodada em aberto (não finalizada)**: exibe e soma provisoriamente o mesmo valor
  `base * 7,5% - dealer_fee` com os buy-ins registrados até o momento. Quando novos
  buy-ins entram, o valor é recalculado; ao fechar, entra no acumulado uma única vez.
- **Despesas**: abatidas uma única vez no `caixa_total`, nunca na premiação, no
  `caixa_anterior` nem no `caixa_noite`. São a soma de todas as linhas da tabela no
  momento da consulta.

```
caixa_anterior = Financial.caixa_anterior (valor base editável)
               + Σ (rodadas finalizadas anteriores à "noite": base * 7,5% - dealer_fee)

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
