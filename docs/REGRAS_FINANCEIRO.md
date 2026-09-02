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
| `DEALER_FEE` | R$ 50,00 | taxa do dealer, cobrada quando a rodada tem 7+ jogadores |

7,5% + 7,5% + 85% = 100% da "base" de cada rodada.

## Fórmulas por rodada

Para uma rodada com jogadores `rps`:

```
gross            = Σ (buyin_i * buyin_value + rebuy_i * rebuy_value)
addons_value     = Σ addon_i * addon_value
total_fee        = Σ buyin_i * ENTRY_FEE                 (só conta buy-ins)
dealer_fee       = DEALER_FEE se num_jogadores >= 7, senão 0

base             = max(gross - total_fee - dealer_fee, 0) + addons_value
caixa_noite      = max(gross + addons_value - dealer_fee, 0)   # pote inteiro, sem taxa fixa

premiacao_total  = base * 85%
premiacao_1      = premiacao_total * 70%
premiacao_2      = premiacao_total * 30%
ranking_noite    = base * 7,5%
```

## Regra do Caixa

- **Rodada fechada (finalizada)**: assim que finaliza, contribui para o acumulado
  `total_fee + base * 7,5%` — imediatamente, mesmo que nenhuma rodada nova tenha
  começado depois dela. Não importa se ela ainda é a última rodada exibida como
  "da noite": o valor já está assentado no acumulado.
- **Rodada em aberto (não finalizada)**: soma o `caixa_noite` **inteiro** por cima do
  acumulado — o dinheiro ainda está fisicamente na caixa e ainda não tem `total_fee`
  nem `7,5%` definidos (a rodada pode receber mais buy-ins). Assim que finalizar,
  passa a valer a regra acima e para de somar o pote inteiro (evita duplicidade).
- **Despesas**: abatem diretamente do `caixa_anterior` (não do `caixa_noite`). São a
  soma de todas as linhas da tabela de despesas no momento da consulta — não há
  histórico/congelamento, editar/remover uma despesa muda o cálculo retroativamente.

```
caixa_anterior = Financial.caixa_anterior (valor base editável)
               + Σ (todas as rodadas finalizadas: total_fee + base * 7,5%)
               - Σ despesas cadastradas

caixa_atual    = caixa_anterior + (caixa_noite, só se houver rodada em aberto)
```

`caixa_com_despesas = premiacao_total - despesas` — indicador à parte (prêmio líquido
da noite descontando despesas), não faz parte do acumulado de caixa.

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
