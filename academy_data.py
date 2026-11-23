"""
Conteúdo educacional avançado, apostilas quantitativas, decks de slides,
roteiros de vídeo-aulas interativas e banco de questões de nível complexo
para a Certificação Heurístika em Mercado Financeiro & Gestão Quantitativa.
"""

import json
from pathlib import Path
import re

MODULOS_EDUCACIONAIS = [
    {
        "numero": "01",
        "titulo": "Heurística Financeira, Convexidade & Critério de Kelly",
        "duracao": "18 min",
        "nivel": "Intermediário • Quant",
        "resumo": "Por que uma estratégia com 45%–50% de acerto pode ser altamente lucrativa quando a assimetria risco/retorno (TP2 vs SL) e o dimensionamento de Kelly protegem a carteira contra a matemática dos drawdowns.",
        "topicos": [
            "Critério de Kelly fracionado: f* = (b·p - q) / b para dimensionamento ótimo sem risco de ruína.",
            "Convexidade de payoff: limitando perdas lineares via Stop Loss enquanto os ganhos capturam caudas positivas.",
            "Eliminação de vieses comportamentais (aversão à perda e efeito disposição) por regras pré-definidas.",
        ],
        "estudo_completo": {
            "introducao": (
                "No mercado financeiro institucional, rentabilidade consistente não depende de acertar a maioria das operações, mas sim da combinação entre Expectativa Matemática Positiva (EV > 0) e Dimensionamento Ótimo de Capital. Traders amadores buscam taxas de acerto acima de 80% utilizando stops largos e alvos curtos — uma estrutura côncava que acumula pequenos ganhos até que um único evento de cauda devolva meses de lucro.\n\n"
                "A abordagem Heurístika inverte essa equação construindo payoffs convexos: cada perda é truncada mecanicamente em -1R (uma unidade pré-definida de risco) via Stop Loss pré-definido, enquanto os ganhos capturam movimentos estendidos (+1,5R em TP1 e +2,5R a +3,5R em TP2). Além disso, a matemática dos drawdowns é severamente não-linear: perder 40% do patrimônio exige um retorno subsequente de +66,7% apenas para retornar ao ponto de partida (break-even). Por isso, o Critério de Kelly define o teto teórico de crescimento geométrico — e sua fração conservadora (Half-Kelly) protege a carteira contra sequências estatísticas normais de perdas."
            ),
            "formula_principal": {
                "titulo": "Critério de Kelly, Expectativa Matemática & Recuperação de Drawdown",
                "equacao": "f* = (b · p - q) / b   |   EV = (p · b) - q   |   Rec = 1 / (1 - DD) - 1",
                "interpretacao": "p = probabilidade de acerto; q = 1 - p (probabilidade de erro); b = razão média ganho/perda (Payoff R:R); f* = fração ótima teórica de capital em risco por operação; DD = drawdown fracional.",
            },
            "exemplo_resolvido": {
                "titulo": "Cálculo Completo: Sistema com 45% de Acerto e Payoff 2,5:1",
                "cenario": "Considere um sistema quantitativo operando com capital de R$ 100.000, taxa de acerto histórica p = 45% (q = 55%) e razão ganho/perda média b = 2,5:1 (TP médio de +2,5R vs. Stop Loss fixo de -1,0R).",
                "passos": [
                    "Passo 1 — Expectativa Matemática (EV): EV = (0,45 × 2,5) - 0,55 = 1,125 - 0,55 = +0,575R por operação. Mesmo errando 55% das vezes, o sistema gera em média +0,575 unidade de risco por trade.",
                    "Passo 2 — Full Kelly (f*): f* = (2,5 × 0,45 - 0,55) / 2,5 = 0,575 / 2,5 = 0,23 (23,0% do capital por aposta). Esse é o ponto máximo teórico de crescimento logarítmico, porém com volatilidade extrema.",
                    "Passo 3 — Half-Kelly Institucional: Na prática, utiliza-se 0,5 × f* = 11,5% (ou frações ainda menores, como 1%–2% de risco em múltiplos ativos simultâneos). Half-Kelly retém 75% do retorno composto máximo cortando a variância da curva de equity pela metade.",
                    "Passo 4 — Perigo de Overbetting & Assimetria de Drawdown: Se o operador arriscar 25% por trade (acima de f* = 23%), uma sequência estatisticamente comum de 4 stops reduz o capital para (0,75)⁴ = 31,6% (-68,4% de drawdown). E lembre-se: uma perda de 40% já exige 1 / (1 - 0,40) - 1 = +66,7% apenas para empatar.",
                ],
                "conclusao": "Com EV = +0,575R e gestão via Kelly fracionado, o foco sai da previsão individual de cada candle e passa para a execução disciplinada de uma série de 100+ operações estatisticamente favoráveis.",
            },
            "erros_comuns": [
                "Arriscar acima do ponto de Kelly (overbetting): mesmo com EV > 0, apostas excessivas levam à ruína matemática em sequências normais de 4 a 6 stops seguidos.",
                "Efeito Disposição: encerrar operações ganhadoras cedo demais por medo de devolver lucro e segurar operações perdedoras removendo o Stop Loss.",
                "Julgar um sistema por 3 ou 5 trades isolados em vez de validar a amostra estatística completa (lei dos grandes números).",
                "Subestimar a assimetria de recuperação: um drawdown de 50% não precisa de +50% para recuperar, mas sim de +100%.",
            ],
            "checklist_pratico": [
                "Validar antes da entrada se a relação R:R até TP2 é igual ou superior a 2,0:1 (preferencialmente ≥ 2,5:1).",
                "Calcular o risco financeiro máximo em R$/USD dentro da banda conservadora (1% a 2% por trade ou fração de Half-Kelly).",
                "Registrar ordem OCO (Stop Loss + Alvos) imediatamente na execução — nunca operar com stop 'mental'.",
                "Auditar o histórico a cada 20 operações verificando se p e b reais permanecem alinhados à expectativa do modelo.",
            ],
        },
        "slides": [
            {
                "titulo": "Assimetria & Convexidade de Payoff",
                "subtitulo": "Por que perder pequeno e ganhar grande vence a alta taxa de acerto",
                "bullets": [
                    "Estratégias côncavas (win rate alto + stop longo) sofrem risco de cauda severo.",
                    "Na Heurístika, perdas são truncadas mecanicamente em -1R via Stop Loss.",
                    "Alvos escalonados (TP1 e TP2) capturam extensões de tendência de +2,5R a +3,5R.",
                    "Com b = 2,5:1 e p = 45%, a Expectativa Matemática é de +0,575R por operação.",
                ],
                "destaque": "EV = (p · b) - q = (0,45 × 2,5) - 0,55 = +0,575R / trade",
                "visual_type": "payoff_asymmetry",
            },
            {
                "titulo": "Curva do Critério de Kelly (Full vs Half)",
                "subtitulo": "Maximizando o crescimento geométrico sem expor a carteira à ruína",
                "bullets": [
                    "Full Kelly f* = (b·p - q) / b encontra o pico exato de crescimento composto.",
                    "Para p = 45% e b = 2,5:1, o Kelly completo resulta em f* = 23,0%.",
                    "Half-Kelly (11,5%) entrega ~75% da taxa de crescimento com metade da volatilidade.",
                    "Ultrapassar 2·f* torna o crescimento logarítmico negativo mesmo com sistema lucrativo.",
                ],
                "destaque": "f* = (2,5 × 0,45 - 0,55) / 2,5 = 23,0%  →  Half-Kelly: 11,5%",
                "visual_type": "kelly_curve",
            },
            {
                "titulo": "A Matemática Implacável do Drawdown",
                "subtitulo": "Por que a proteção do capital principal antecede qualquer busca por retorno",
                "bullets": [
                    "Perdas e ganhos não são simétricos: a base de capital encolhe após cada prejuízo.",
                    "Um drawdown de -10% exige +11,1% para recuperação; -25% exige +33,3%.",
                    "Um drawdown de -40% exige +66,7% líquidos apenas para voltar ao zero a zero.",
                    "Controlar o risco unitário evita entrar na zona exponencial de recuperação difícil.",
                ],
                "destaque": "DD -40%  →  Retorno Break-Even = 1 / (1 - 0,40) - 1 = +66,7%",
                "visual_type": "drawdown_asymmetry",
            },
            {
                "titulo": "Convergência Estatística & Sequências de Perda",
                "subtitulo": "Sobrevivendo às séries negativas inevitáveis de qualquer estratégia",
                "bullets": [
                    "Mesmo em sistemas com 50% de acerto, sequências de 5 stops consecutivos ocorrem naturalmente (~3,1% de chance a cada bloco).",
                    "Arriscar 25% por trade acima do Kelly gera drawdown de ~76% em apenas 5 stops.",
                    "Com risco calibrado em 1%–2% por sinal, 5 stops seguidos custam apenas 5%–10%.",
                    "Preservar margem garante capital emocional e financeiro para capturar a próxima pernada de TP2.",
                ],
                "destaque": "Risco 2%/trade × 5 stops = -9,6%  vs  Risco 25% × 5 stops = -76,3%",
                "visual_type": "ev_matrix",
            },
            {
                "titulo": "Engenharia Comportamental Anti-Viés",
                "subtitulo": "Substituindo decisões emocionais por protocolos quantitativos",
                "bullets": [
                    "Aversão à perda (Kahneman & Tversky): dor de perder pesa ~2× mais que alegria de ganhar.",
                    "Efeito Disposição: fechar ganhos cedo para 'garantir' e alongar perdas esperando reversão.",
                    "Protocolo de Mesa: Entrada, SL, TP1 e TP2 definidos antes do clique.",
                    "Auditoria automática registra cada resultado sem edição manual ou viés de memória.",
                ],
                "destaque": "Disciplina Quantitativa = Regras Imutáveis Pré-Execução",
                "visual_type": "behavioral_rules",
            },
        ],
        "video_aula": {
            "titulo": "Aula 01: Convexidade de Payoff, Kelly Fracionado & Sobrevivência Matemática",
            "duracao_segundos": 220,
            "instrutor": "Rafael Mendes • Estrategista Quantitativo",
            "audio_url": "/static/audio/academia_mod_01.mp3",
            "audio_voz": "pt-BR-AntonioNeural",
            "capitulos": [
                {
                    "tempo_inicio": 0,
                    "titulo": "1. O Mito da Alta Taxa de Acerto vs. Convexidade",
                    "destaque_visual": "EV = (p · b) - q = +0,575R",
                    "visual_mode": "payoff_asymmetry",
                    "roteiro": "Olá, eu sou o Rafael Mendes, e vamos abrir o Módulo Um desarmando a maior armadilha do mercado: achar que você precisa acertar quase todas as operações. Pensa num motorista de aplicativo que faz dezenove corridas curtas de vinte reais e, na vigésima, leva uma multa de quinhentos reais. Noventa e cinco por cento de acerto, mas fechou o dia no vermelho! Quem usa stop largo e alvo curto sofre exatamente assim. Na Heurístika, buscamos convexidade: cada perda trava mecanicamente em menos um érre no stop loss, enquanto os alvos de ganho buscam dois e meio a três e meio para um. Com quarenta e cinco por cento de acerto e razão dois e meio para um, a expectativa matemática dá mais zero vírgula cinco sete cinco érre por trade, mesmo errando a maioria. Agora, quanto apostar em cada sinal?",
                },
                {
                    "tempo_inicio": 44,
                    "titulo": "2. Derivando o Critério de Kelly na Prática",
                    "destaque_visual": "f* = (2,5 × 0,45 - 0,55) / 2,5 = 23%",
                    "visual_mode": "kelly_curve",
                    "roteiro": "Olha essa curva aqui na tela. Ela mostra o tamanho ideal da sua aposta. Imagina descer uma serra cheia de curvas: pisar a cento e oitenta por hora até empolga, mas você sai da pista; ir a vinte não te leva a lugar nenhum. O Critério de Kelly calcula exatamente a velocidade máxima segura para o capital crescer no composto. A conta é direta: dois e meio vezes quarenta e cinco por cento, menos cinquenta e cinco por cento, dividido por dois e meio. Isso dá zero vírgula cinco sete cinco sobre dois e meio, ou seja, vinte e três por cento no éfe estrela. Como o pico oscila bastante, na prática usamos o Half-Kelly de onze vírgula cinco por cento, ou um a dois por cento por sinal. Mas por que frear abaixo do pico? Porque perder e ganhar não têm o mesmo peso.",
                },
                {
                    "tempo_inicio": 88,
                    "titulo": "3. Assimetria Matemática do Drawdown (-40% → +66,7%)",
                    "destaque_visual": "Rec = 1 / (1 - 0,40) - 1 = +66,7%",
                    "visual_mode": "drawdown_asymmetry",
                    "roteiro": "Repara nessa rampa vermelha subindo cada vez mais íngreme na tela. A matemática do drawdown é traiçoeira porque a sua base de capital encolhe a cada prejuízo. Sabe quando uma camisa de cem reais cai quarenta por cento na promoção e vai para sessenta? Se no dia seguinte ela subir só quarenta por cento sobre sessenta, vai para oitenta e quatro, e não volta para cem! Na sua carteira acontece igual: se cem mil reais caem quarenta por cento, sobram sessenta mil. Para recuperar quarenta mil em cima de sessenta, você precisa de sessenta e seis vírgula sete por cento de ganho líquido só para voltar ao zero a zero. Se cair cinquenta por cento, precisa dobrar, fazendo cem por cento! Por isso, proteger o patrimônio vem sempre antes de buscar retorno. E olha o perigo quando alguém ignora esse teto.",
                },
                {
                    "tempo_inicio": 134,
                    "titulo": "4. O Perigo do Overbetting Mesmo com EV Positivo",
                    "destaque_visual": "Risco 25% + 5 stops = -76,3% (Ruína)",
                    "visual_mode": "ev_matrix",
                    "roteiro": "Muita gente acha que, se a estratégia tem expectativa matemática positiva, basta apostar pesado que o lucro aparece rápido. Cuidado! Imagina jogar cara ou coroa com uma moeda viciada a seu favor, apostando um quarto de tudo o que você tem a cada rodada. Mesmo com vantagem estatística, basta uma sequência normal de erros para quebrar antes da convergência no longo prazo. Olha na matriz: mesmo acertando cinquenta por cento, cinco stops seguidos são completamente normais. Quem arrisca vinte e cinco por cento por operação passa do limite de Kelly e amarga setenta e seis vírgula três por cento de queda em cinco stops: é ruína antes da virada. Já quem arrisca dois por cento perde só nove vírgula seis por cento na mesma série e segue inteiro para a próxima pernada. Agora falta blindar a nossa própria cabeça.",
                },
                {
                    "tempo_inicio": 178,
                    "titulo": "5. Eliminando Vieses Comportamentais com Regras Fixas",
                    "destaque_visual": "Stop Fixo • TP1 Parcial • Auditoria Live",
                    "visual_mode": "behavioral_rules",
                    "roteiro": "Sabe por que tanta gente com uma planilha excelente ainda devolve dinheiro no pregão? Decidir com o preço piscando na tela é como entrar no supermercado com fome e sem lista: você compra por impulso e estoura o orçamento. Na psicologia econômica, a dor de perder pesa duas vezes mais que o prazer de ganhar — é a aversão à perda. Daí nasce o efeito disposição: cortar ganhos cedo demais e segurar perdas tirando o stop na torcida. Aqui na mesa, travamos tudo antes do clique: entrada, stop loss, alvo um e alvo dois em ordem automática, sem stop mental. E só auditamos o modelo em blocos de vinte ou mais operações, sem emoção. No Módulo Dois, vamos descobrir onde cravar esse stop no gráfico usando a volatilidade real de cada ativo.",
                },
            ],
        },
    },
    {
        "numero": "02",
        "titulo": "Volatilidade (ATR), Microestrutura & Posicionamento de Stop",
        "duracao": "20 min",
        "nivel": "Avançado • Execução",
        "resumo": "Como calibrar distância de stops, tamanho de lote e realização parcial ao regime de volatilidade (ATR) e à liquidez do livro de ofertas, mantendo o risco financeiro constante.",
        "topicos": [
            "Average True Range (ATR): evitando stops curtos demais dentro do ruído intradiário.",
            "Diferença entre liquidez de livro (order book) em majors de Forex vs altcoins e small caps.",
            "Escalonamento de saída parcial em TP1 (proteção do ponto de entrada) e condução até TP2.",
        ],
        "estudo_completo": {
            "introducao": (
                "Um erro clássico na execução de sinais é utilizar stops arbitrários — como 'sempre 1% do preço' ou 'sempre 20 pips' — independentemente do ativo e do regime de mercado. Um stop fixo de 1% em um par Forex de baixa volatilidade pode ser largo demais, enquanto em Bitcoin ou em uma ação de tecnologia pós-balanço é facilmente varrido pelo ruído normal do book (livro de ofertas) em questão de minutos.\n\n"
                "O Average True Range (ATR) mede a amplitude real média de oscilação de cada candle (incluindo gaps entre fechamento e abertura). Ao posicionar o Stop Loss fora da zona de ruído (tipicamente entre 1,2× e 1,8× ATR₁₄) e dimensionar o lote de forma inversamente proporcional a essa distância, o operador garante duas propriedades vitais: (1) o stop só é acionado quando a tese estrutural é realmente invalidada, e (2) quando a volatilidade dobra, a distância do stop dobra para evitar violinadas e o tamanho do lote cai pela metade, mantendo o risco financeiro em reais ou dólares rigorosamente constante."
            ),
            "formula_principal": {
                "titulo": "Dimensionamento Inverso à Volatilidade & Risco Financeiro Constante",
                "equacao": "Risco ($) = Lote × |Entrada - Stop|   ⇒   Lote = (Capital × Risco%) / (k · ATR₁₄)",
                "interpretacao": "Quando a volatilidade (ATR) dobra, a distância do Stop Loss (k·ATR₁₄) também deve dobrar para evitar violinadas; consequentemente, o tamanho da posição (Lote) deve ser reduzido pela metade para manter o Risco ($) idêntico.",
            },
            "exemplo_resolvido": {
                "titulo": "Adaptação de Lote quando o ATR Dobra de Regime",
                "cenario": "Um trader opera uma conta de R$ 50.000 com limite rígido de 1% de risco financeiro por sinal (R$ 500 de perda máxima). O ativo negocia a R$ 100,00 com múltiplo de stop estrutural k = 1,5 × ATR₁₄.",
                "passos": [
                    "Passo 1 — Regime Calmo (ATR₁₄ = R$ 2,00): Distância do stop = 1,5 × 2,00 = R$ 3,00 (Stop em R$ 97,00). Lote máximo = R$ 500 / R$ 3,00 = 166 ações (exposição nominal R$ 16.600).",
                    "Passo 2 — Choque de Volatilidade (ATR₁₄ dobra para R$ 4,00): Para não cair no ruído intradiário, o stop acompanha o ATR e passa para 1,5 × 4,00 = R$ 6,00 (Stop em R$ 94,00).",
                    "Passo 3 — Ajuste Inverso de Lote: Mantendo o risco fixo de R$ 500, o novo lote cai pela metade: R$ 500 / R$ 6,00 = 83 ações (exposição nominal R$ 8.300).",
                    "Passo 4 — Escalonamento em TP1/TP2: No regime normal, TP1 fica em +2,0 ATR (R$ 104,00), onde realiza-se 50% da posição travando +R$ 332 e move-se o stop restante para o breakeven (R$ 100,00) buscando TP2 em +3,5 ATR (R$ 107,00).",
                ],
                "conclusao": "Independentemente de o ativo estar calmo ou altamente volátil, um eventual Stop Loss gera exatamente -R$ 500 (-1,0% do capital), protegendo a estabilidade da curva de equity.",
            },
            "erros_comuns": [
                "Aumentar a distância do stop pelo ATR mantendo o mesmo número de contratos/ações — isso dobra ou triplica o prejuízo real no stop.",
                "Colocar o stop em números redondos óbvios (ex.: 1,1000 ou R$ 50,00) onde há concentração de liquidez e caça a stops.",
                "Aplicar a mesma alavancagem de EUR/USD em altcoins ou ações small caps com book raso, sofrendo slippage severo na execução.",
                "Deixar uma operação vencedora em TP1 reverter completamente até o Stop Loss original por não ajustar proteção ao ponto de entrada.",
            ],
            "checklist_pratico": [
                "Consultar o ATR₁₄ do timeframe operacional antes de definir o preço de Stop Loss.",
                "Verificar spread e profundidade do livro de ofertas (especialmente próximo a notícias macro).",
                "Calcular o tamanho exato da posição pela fórmula Risco ($) / Distância do Stop (use a Calculadora do Terminal VIP).",
                "Ao atingir TP1, realizar parcial programada (ex.: 50%) e proteger a parcela restante rumo a TP2.",
            ],
        },
        "slides": [
            {
                "titulo": "Average True Range (ATR) vs. Ruído Intradiário",
                "subtitulo": "Calibrando o Stop Loss para fora da zona de oscilação aleatória",
                "bullets": [
                    "O True Range mede o maior valor entre (Máx - Mín), |Máx - Fech_ant| e |Mín - Fech_ant|.",
                    "O ATR₁₄ revela o 'respiro' natural do ativo em cada candle.",
                    "Stops abaixo de 0,8× ATR são frequentemente atingidos por mero ruído de microestrutura.",
                    "Stops estruturais entre 1,2× e 1,8× ATR respeitam suportes e resistências reais.",
                ],
                "destaque": "Stop Estrutural = Entrada ∓ (1,5 × ATR₁₄)",
                "visual_type": "atr_ladder",
            },
            {
                "titulo": "Regra de Ouro: Risco Financeiro Constante",
                "subtitulo": "Quando a volatilidade dobra, o stop dobra e o lote cai pela metade",
                "bullets": [
                    "Risco ($) = Tamanho da Posição × Distância do Stop.",
                    "Se o ATR dobra, encurtar o stop para manter o lote causa stops prematuros em série.",
                    "A solução quantitativa: ampliar a distância proporcionalmente ao ATR e dividir o lote por 2.",
                    "Resultado: a volatilidade da carteira em R$ permanece estável em qualquer ciclo.",
                ],
                "destaque": "ATR × 2  ⇒  Distância Stop × 2  &  Tamanho do Lote ÷ 2",
                "visual_type": "volatility_sizing",
            },
            {
                "titulo": "Microestrutura & Liquidez do Order Book",
                "subtitulo": "Spreads, profundidade de livro e slippage em diferentes classes de ativos",
                "bullets": [
                    "Majors de Forex (EUR/USD, USD/JPY) e BTC spot possuem livros profundos e spreads comprimidos.",
                    "Altcoins e small caps apresentam vácuos de liquidez entre níveis de preço.",
                    "Ordens a mercado grandes em books rasos geram derrapagem (slippage) que corrói o R:R.",
                    "Em horários de baixa liquidez (rollover / pré-payroll), reduza alavancagem ou aguarde normalização.",
                ],
                "destaque": "Custo Real = Spread + Slippage + Taxa (Impacta o R:R Efetivo)",
                "visual_type": "orderbook_liquidity",
            },
            {
                "titulo": "Escalonamento Parcial em TP1 & Condução a TP2",
                "subtitulo": "Transformando trades vencedores em posições de risco zero",
                "bullets": [
                    "Ao atingir TP1 (ex.: +1,5R a +2,0R), realiza-se 40%–50% da posição no lucro.",
                    "O Stop Loss do lote remanescente é ajustado para o preço de entrada (Breakeven).",
                    "A partir desse ponto, o trade passa a ter risco líquido zero ou positivo garantido.",
                    "O saldo restante captura a cauda longa até TP2 (+3,0R+) sem pressão psicológica.",
                ],
                "destaque": "TP1 Atingido: Realiza 50% + Move SL → Entrada = Free Roll até TP2",
                "visual_type": "partial_scaling",
            },
            {
                "titulo": "Regimes de Volatilidade: Compressão & Expansão",
                "subtitulo": "Identificando transições de mercado para calibrar alvos",
                "bullets": [
                    "Volatilidade é cíclica: períodos de baixa amplitude (compressão) precedem rompimentos fortes.",
                    "Na compressão, stops ficam menores e permitem lotes maiores dentro do mesmo risco ($).",
                    "Na expansão pós-notícia, alvos TP2 podem ser projetados a múltiplos maiores de ATR.",
                    "Reavaliar o ATR semanalmente evita operar com parâmetros defasados do mês anterior.",
                ],
                "destaque": "Compressão (ATR baixo) → Expansão (Rompimento) → Exaustão",
                "visual_type": "regime_shift",
            },
        ],
        "video_aula": {
            "titulo": "Aula 02: Stops por ATR, Dimensionamento de Lote & Microestrutura de Execução",
            "duracao_segundos": 225,
            "instrutor": "Rafael Mendes • Estrategista Quantitativo",
            "audio_url": "/static/audio/academia_mod_02.mp3",
            "audio_voz": "pt-BR-AntonioNeural",
            "capitulos": [
                {
                    "tempo_inicio": 0,
                    "titulo": "1. Por Que Stops Fixos Falham — Entendendo o ATR",
                    "destaque_visual": "ATR₁₄ = Amplitude Real Média (Ruído vs Tese)",
                    "visual_mode": "atr_ladder",
                    "roteiro": "De volta por aqui com você no Módulo Dois. Agora que já sabemos quanto arriscar, precisamos definir onde colocar o stop sem virar alvo fácil do ruído. Usar stop fixo de um por cento em qualquer ativo é como tentar estacionar um caminhão na vaga de um carro compacto: no câmbio calmo cabe, mas no Bitcoin você é varrido pelo balanço normal do dia. Para enxergar esse respiro real, usamos o Á-Tê-Érre de quatorze períodos, que mede a amplitude média dos candles incluindo os gaps. Olha na escada de preços: stops abaixo de zero vírgula oito Á-Tê-Érre morrem no ruído aleatório do mercado. O stop estrutural mora entre um vírgula dois e um vírgula oito, com referência em um vírgula cinco Á-Tê-Érre. Só que alargar o stop traz uma dúvida imediata: o que fazemos com o tamanho do lote?",
                },
                {
                    "tempo_inicio": 45,
                    "titulo": "2. Matemática do Lote quando a Volatilidade Dobra",
                    "destaque_visual": "Risco ($) = Lote × Stop  ⇒  ATR ×2 → Lote ÷2",
                    "visual_mode": "volatility_sizing",
                    "roteiro": "Essa regra vale ouro para a sua sobrevivência. Imagina dirigir na rodovia quando cai uma tempestade forte: você dobra a distância para o carro da frente e corta a velocidade pela metade para manter a mesma margem de segurança. No trade funciona exatamente igual, porque o risco financeiro é o tamanho da posição vezes a distância do stop. Numa conta de cinquenta mil reais com risco de um por cento, ou quinhentos reais, um stop de três reais comporta cento e sessenta e seis ações. Quando a volatilidade medida pelo Á-Tê-Érre dobra, você dobra a distância do stop para seis reais e reduz o tamanho da posição pela metade, para oitenta e três ações. Assim, seu risco em reais ou dólares continua rigorosamente constante em quinhentos reais! Agora, como o livro de ofertas muda essa execução?",
                },
                {
                    "tempo_inicio": 92,
                    "titulo": "3. Profundidade de Order Book: Forex Majors vs. Altcoins",
                    "destaque_visual": "Liquidez Profunda (0,2 pip) vs Book Raso (Slippage)",
                    "visual_mode": "orderbook_liquidity",
                    "roteiro": "Calcular o lote perfeito no papel não basta se o livro de ofertas for raso na hora do clique. Operar pares principais como Euro-Dólar ou Dólar-Iene é como dirigir numa avenida larga de seis pistas: liquidez institucional profunda e spread fininho, perto de zero vírgula dois pip. Já entrar pesado numa altcoin ou ação menor é tentar manobrar numa viela estreita: existem vácuos no livro, e uma ordem grande varre vários degraus de preço de uma vez. Essa derrapagem, chamada de slippage, somada ao spread e às taxas, encolhe a sua razão ganho-perda real. Evite também deixar stops em números redondos óbvios, como cinquenta reais, e reduza a mão perto de notícias macro e rollover. Com execução limpa, como protegemos o lucro quando o preço anda a nosso favor?",
                },
                {
                    "tempo_inicio": 138,
                    "titulo": "4. Escalonamento TP1 (Breakeven) e Captura de TP2",
                    "destaque_visual": "TP1: Realiza 50% + SL na Entrada → TP2 Livre",
                    "visual_mode": "partial_scaling",
                    "roteiro": "Todo operador já sentiu a frustração de ver um trade bonito quase bater no alvo, voltar tudo e fechar no prejuízo. Para equilibrar consistência e assimetria, pense num produtor rural que colhe metade da safra assim que amadurece para garantir o galpão, e deixa a outra metade no pé tentando um preço melhor. Aqui no gráfico, ao bater o alvo um — entre um vírgula cinco e dois érre — realizamos quarenta a cinquenta por cento da posição, colocando lucro no bolso, e trazemos o stop loss da parcela restante para o preço de entrada, o zero a zero, chamado de breakeven. A partir daí, você conduz uma operação de risco zero até o alvo dois, em três érre ou mais, sem pressão emocional. Falta agora ler quando o próprio mercado muda de marcha.",
                },
                {
                    "tempo_inicio": 182,
                    "titulo": "5. Leitura de Regimes de Compressão e Expansão",
                    "destaque_visual": "Baixo ATR → Rompimento → Alta Volatilidade",
                    "visual_mode": "regime_shift",
                    "roteiro": "Por fim, olha esse gráfico de regimes na tela. A volatilidade nunca é estática; ela funciona como uma mola sendo comprimida antes de saltar. Quando o preço passa dias quieto e o Á-Tê-Érre cai às mínimas, há energia acumulada para um rompimento forte. Na compressão, o stop fica curto, cabendo um lote maior dentro do mesmo limite de um por cento de risco. Mas quando vem a expansão, o movimento estica rápido e, depois, entra em exaustão; por isso recalibramos lotes e alvos aos novos múltiplos do Á-Tê-Érre. Atualizar essa leitura toda semana evita dirigir no nevoeiro com mapa velho. Agora eu passo a palavra para a Camila Duarte, que vai te guiar na engenharia de carteiras por horizonte de tempo no Módulo Três!",
                },
            ],
        },
    },
    {
        "numero": "03",
        "titulo": "Alocação Multi-Horizonte (2, 5 e 10+ Anos) & Sharpe Ratio",
        "duracao": "22 min",
        "nivel": "Estratégico • Portfólio",
        "resumo": "Arquitetura de carteiras resilientes por prazo de resgate combinando liquidez pós-fixada, juros reais IPCA+, crescimento global, reserva digital e proteção descorrelacionada para maximizar o Índice de Sharpe.",
        "topicos": [
            "Curto prazo (2 anos): prioridade em liquidez, duration baixa e controle rigoroso de drawdown.",
            "Médio prazo (5 anos): equilíbrio entre juro real (IPCA+), dividendos e crescimento global dolarizado.",
            "Longo prazo (10+ anos): captura de juros compostos em índices globais, tecnologia e reserva digital escassa.",
        ],
        "estudo_completo": {
            "introducao": (
                "Construir patrimônio de forma institucional exige separar objetivos financeiros por horizonte temporal. O maior erro na alocação de carteiras é aplicar recursos com data de resgate em 24 meses em ativos de alta volatilidade — submetendo o investidor ao risco de sequência de retornos, isto é, o perigo de uma queda cíclica de bolsa ou cripto coincidir exatamente com o mês do saque.\n\n"
                "A métrica central para comparar carteiras entre diferentes classes de risco é o Índice de Sharpe: Sharpe = (Rp - Rf) / σp, que mede quanto retorno excedente acima da taxa livre de risco (Rf) a carteira gera por unidade de volatilidade (σp). Ao combinar motores descorrelacionados — Renda Fixa Pós-Fixada/IPCA+, FIIs de renda, Índices Globais (NDX100/IVVB11), Bitcoin em dose calibrada e Ouro (GC=F), cuja baixa ou negativa correlação em crises atua como amortecedor sistêmico — é possível elevar o Índice de Sharpe reduzindo drawdowns em crises severas."
            ),
            "formula_principal": {
                "titulo": "Índice de Sharpe & Eficiência Risco-Retorno de Portfólio",
                "equacao": "Sharpe = (Rp - Rf) / σp   |   σ²_port = Σ wᵢ²σᵢ² + ΣΣ wᵢwⱼρᵢⱼσᵢσⱼ",
                "interpretacao": "Rp = retorno anualizado do portfólio; Rf = taxa livre de risco (Selic/CDI); σp = desvio-padrão (volatilidade) do portfólio; ρᵢⱼ = correlação entre ativos (quanto menor ρ, maior a redução de risco).",
            },
            "exemplo_resolvido": {
                "titulo": "Comparando Eficiência Sharpe com Diversificação & Ouro (Rf = 10,5% a.a.)",
                "cenario": "Considere dois investidores comparando retorno esperado e volatilidade anualizada contra uma taxa livre de risco Rf = 10,5% a.a.",
                "passos": [
                    "Passo 1 — Portfólio Concentrado (100% Tech/Cripto): Retorno esperado Rp = 18,0% a.a., mas com volatilidade elevada σp = 26,0% a.a. Sharpe = (18,0% - 10,5%) / 26,0% = 0,29.",
                    "Passo 2 — Portfólio Multi-Horizonte 5+ Anos (IPCA+ + Globais + 10% Ouro GC=F): Retorno esperado Rp = 16,5% a.a. com volatilidade reduzida pela descorrelação para σp = 12,0% a.a.",
                    "Passo 3 — Salto de Eficiência: Sharpe = (16,5% - 10,5%) / 12,0% = 0,50 — uma eficiência risco-retorno +72% superior ao portfólio concentrado.",
                    "Passo 4 — Escolha por Horizonte: Para 2 anos (Curto), prioriza-se Tesouro Selic/Liquidez para anular o risco de estar em queda no mês 24; para 10+ anos (Longo), amplia-se a exposição a índices globais, tecnologia e BTC para maximizar os juros compostos.",
                ],
                "conclusao": "Diversificação inteligente com ativos descorrelacionados como o Ouro aumenta o Sharpe Ratio e torna a carteira psicologicamente sustentável através de múltiplos ciclos econômicos.",
            },
            "erros_comuns": [
                "Alocar reserva de curto prazo (2 anos) em ações ou cripto esperando retorno rápido — risco severo de resgatar no fundo de um ciclo.",
                "Avaliar carteiras olhando apenas para o retorno nominal bruto sem medir volatilidade (σp) e drawdown máximo (Sharpe baixo).",
                "Acreditar que ter 15 ações do mesmo setor no mesmo país é diversificação — em crises locais a correlação tende a 1,0.",
                "Excluir ativos de proteção como Ouro (GC=F) por não pagarem dividendos, ignorando sua função de hedge em eventos de cauda.",
            ],
            "checklist_pratico": [
                "Mapear a data de uso de cada bloco de capital antes de escolher o veículo (2, 5 ou 10+ anos).",
                "Garantir liquidez imediata e baixa duration para compromissos abaixo de 24 meses.",
                "Manter parcela dolarizada (IVVB11/NDX100) e proteção real (IPCA+ / Ouro) em horizontes médios e longos.",
                "Calcular o Índice de Sharpe e o Max Drawdown esperado no Simulador da página /carteiras antes de executar aportes.",
            ],
        },
        "slides": [
            {
                "titulo": "Índice de Sharpe & Fronteira Eficiente",
                "subtitulo": "Medindo o retorno excedente por unidade de risco total assumido",
                "bullets": [
                    "Sharpe = (Rp - Rf) / σp compara qualquer portfólio contra o ativo livre de risco.",
                    "Um portfólio que retorna 16,5% com 12% de volatilidade supera outro de 18% com 26% de vol.",
                    "Ativos descorrelacionados deslocam a carteira para cima e para a esquerda na fronteira eficiente.",
                    "O objetivo quantitativo é maximizar retorno composto por unidade de drawdown tolerado.",
                ],
                "destaque": "Sharpe = (Rp - Rf) / σp  |  Multi-Ativos (0,50) > Concentrado (0,29)",
                "visual_type": "horizon_frontier",
            },
            {
                "titulo": "Horizonte Curto (2 Anos): Preservação & Liquidez",
                "subtitulo": "Neutralizando o risco de sequência de retornos no curto prazo",
                "bullets": [
                    "Em janelas de 24 meses, ativos de renda variável podem estar em ciclo de baixa na data do resgate.",
                    "A prioridade absoluta é preservação do principal, liquidez diária e variância mínima.",
                    "Concentração estrutural em Pós-Fixado (Tesouro Selic / CDI) e títulos de duration curtíssima.",
                    "Pequenas parcelas táticas só são admitidas no perfil Agressivo com controle estrito de perda.",
                ],
                "destaque": "Curto Prazo (2a): Foco em Liquidez + Baixa Duration + Drawdown Mínimo",
                "visual_type": "short_horizon_2y",
            },
            {
                "titulo": "Horizonte Médio (5 Anos): Equilíbrio Real & Renda",
                "subtitulo": "Combinando juro real brasileiro, FIIs e crescimento global",
                "bullets": [
                    "Juros reais (Tesouro IPCA+) protegem o poder de compra contra surpresas inflacionárias.",
                    "Fundos Imobiliários (FIIs) e ações pagadoras de dividendos geram fluxo mensal reinvestível.",
                    "Exposição global em dólar (IVVB11 / SPX500) protege contra risco fiscal doméstico.",
                    "O equilíbrio reduz a dependência de um único cenário macroeconômico.",
                ],
                "destaque": "Médio Prazo (5a): IPCA+ (Proteção) + FIIs (Renda) + Global (Crescimento)",
                "visual_type": "medium_horizon_5y",
            },
            {
                "titulo": "Horizonte Longo (10+ Anos): Juros Compostos Exponenciais",
                "subtitulo": "Capturando inovação global e escassez digital ao longo de décadas",
                "bullets": [
                    "No horizonte de 10+ anos, a volatilidade de curto prazo é diluída pelo crescimento exponencial.",
                    "Maior peso em índices de tecnologia (NDX100 / NVDA / AAPL) e ETFs globais de ações.",
                    "Alocação calibrada em Bitcoin (BTC) captura assimetria de reserva digital escassa.",
                    "Aportes mensais consistentes transformam quedas intermediárias em oportunidades de compra.",
                ],
                "destaque": "Longo Prazo (10+a): Tempo + Aportes + Assimetria Global = Efeito Bola de Neve",
                "visual_type": "long_horizon_10y",
            },
            {
                "titulo": "Ouro (GC=F) & Correlação em Eventos de Cauda",
                "subtitulo": "Por que ativos descorrelacionados salvam o portfólio nas crises",
                "bullets": [
                    "Em crises sistêmicas (2008, 2020), ações e crédito costumam cair juntos.",
                    "O Ouro (GC=F) apresenta correlação historicamente baixa ou negativa nesses choques.",
                    "Sua função não é pagar dividendos, mas amortecer o drawdown máximo da carteira.",
                    "Com menor queda no pânico, o investidor não vende na baixa e preserva capital para rebalancear.",
                ],
                "destaque": "Papel do Ouro: Reduzir Correlação & Amortecer Drawdowns Sistêmicos",
                "visual_type": "correlation_hedge",
            },
        ],
        "video_aula": {
            "titulo": "Aula 03: Engenharia de Carteiras (2, 5 e 10+ Anos), Sharpe Ratio & Hedge",
            "duracao_segundos": 230,
            "instrutor": "Camila Duarte • Estrategista de Portfólios & Macro",
            "audio_url": "/static/audio/academia_mod_03.mp3",
            "audio_voz": "pt-BR-ThalitaMultilingualNeural",
            "capitulos": [
                {
                    "tempo_inicio": 0,
                    "titulo": "1. Índice de Sharpe e Eficiência da Fronteira",
                    "destaque_visual": "Sharpe = (Rp - Rf) / σp",
                    "visual_mode": "horizon_frontier",
                    "roteiro": "Olá, aqui é a Camila Duarte. No Módulo Três, saímos da operação isolada para desenhar a sua carteira inteira. Escolher ativos olhando só o retorno bruto passado engana muito. Pensa em dois carros na mesma viagem: um chacoalha em todo buraco e gasta demais; o outro chega no mesmo horário com suavidade e eficiência. Quem mede essa eficiência é o Índice de Sharpe: o retorno excedente da carteira acima da taxa livre de risco, dividido pela volatilidade total, ou seja, o desvio-padrão. Olha na fronteira da tela: com Selic a dez vírgula cinco por cento, um portfólio concentrado de dezoito por cento com vinte e seis por cento de volatilidade entrega Sharpe de zero vírgula vinte e nove. Diversificando para dezesseis vírgula cinco por cento com doze de risco, o Sharpe salta para zero vírgula cinquenta. E o primeiro passo dessa engenharia começa nos dois anos.",
                },
                {
                    "tempo_inicio": 46,
                    "titulo": "2. Curto Prazo (2 Anos): Por Que o Pós-Fixado Domina",
                    "destaque_visual": "24 Meses: Preservação > Volatilidade",
                    "visual_mode": "short_horizon_2y",
                    "roteiro": "Imagina um plano com data marcada daqui a exatamente vinte e quatro meses — a entrada de um apartamento ou uma reforma importante. Você colocaria o dinheiro da escritura na montanha-russa da bolsa ou das criptos torcendo para estar no topo na véspera do pagamento? Claro que não! O grande inimigo no prazo de dois anos se chama risco de sequência de retornos: ativos voláteis como ações e criptomoedas podem estar em ciclo de baixa exatamente na data do resgate, no mês vinte e quatro, sem tempo para recuperação. Por isso, uma carteira conservadora de curto prazo concentra maior peso em pós-fixado e liquidez, como o Tesouro Selic, garantindo resgate imediato, baixíssima duration e preservação do principal. Já quando ampliamos o horizonte para cinco anos, a carteira ganha fôlego para acionar três motores juntos.",
                },
                {
                    "tempo_inicio": 94,
                    "titulo": "3. Médio Prazo (5 Anos): Juro Real, FIIs e Dolarização",
                    "destaque_visual": "5 Anos: IPCA+ + Renda + ETF Global",
                    "visual_mode": "medium_horizon_5y",
                    "roteiro": "Quando temos cinco anos de horizonte, não precisamos deixar tudo parado no caixa, nem apostar todas as fichas em um único cenário econômico. Pensa numa casa apoiada em três pilares diferentes: se uma tempestade bater forte de um lado, os outros dois seguram o telhado de pé. O primeiro pilar traz títulos I-P-C-A mais, travando juro real acima da inflação brasileira. O segundo combina fundos imobiliários e ações de dividendos, gerando fluxo mensal que você reinveste em novas cotas. E o terceiro coloca uma fatia global em dólar, por meio de ETFs como o I-V-V-B onze, protegendo o patrimônio contra sustos fiscais domésticos. Juntos, esses motores equilibram crescimento e renda com estabilidade. Agora, o que muda quando destravamos dez anos ou mais? É aí que o tempo vira nosso maior sócio.",
                },
                {
                    "tempo_inicio": 140,
                    "titulo": "4. Longo Prazo (10+ Anos): Poder dos Juros Compostos",
                    "destaque_visual": "10+ Anos: NDX100 + Tech + BTC Calibrado",
                    "visual_mode": "long_horizon_10y",
                    "roteiro": "Acima de dez anos, o tempo deixa de ser vilão e vira o grande combustível da multiplicação patrimonial. Sabe uma bola de neve descendo uma montanha bem comprida? Nos primeiros metros ela parece lenta e qualquer pedra no caminho assusta. Mas, com aportes mensais constantes, cada queda vira promoção para acumular mais cotas, fazendo os juros compostos acelerarem de forma exponencial. Nesse horizonte de dez anos ou mais, alocamos maior peso em crescimento global e tecnologia — como o índice Nasdaq cem, com líderes como Nvidia e Apple — somado a uma fatia calibrada de Bitcoin como reserva digital escassa. A oscilação curta se dilui diante do CDI e da inflação. Mas fica uma pergunta crucial: o que segura essa carteira quando uma crise global derruba ações e cripto juntos?",
                },
                {
                    "tempo_inicio": 186,
                    "titulo": "5. O Papel Estrutural do Ouro em Choques Sistêmicos",
                    "destaque_visual": "Ouro (GC=F): Baixa Correlação + Amortecedor",
                    "visual_mode": "correlation_hedge",
                    "roteiro": "Muita gente olha para uma carteira de dez anos ou mais com tecnologia — como Nvidia e Nasdaq cem — e Bitcoin, e pergunta por que incluir ouro se ele não paga dividendo mensal. Olha, cobrar dividendo do ouro é como reclamar que o airbag do carro não economiza gasolina! Você não instala airbag pensando no passeio calmo; ele salva a viagem na batida. Em crises sistêmicas, como dois mil e oito ou dois mil e vinte, ativos de risco e crédito costumam despencar juntos. O contrato de ouro mantém correlação historicamente baixa ou negativa nesses momentos, amortecendo o drawdown da carteira e elevando o Índice de Sharpe. Com queda menor, você evita vender no pânico e ainda sobra fôlego para rebalancear. No Módulo Quatro, fechamos com duration, carry trade e bandas!",
                },
            ],
        },
    },
    {
        "numero": "04",
        "titulo": "Renda Fixa (Duration), Câmbio (Carry Trade) & Derivativos",
        "duracao": "24 min",
        "nivel": "Avançado • Macro & Renda Fixa",
        "resumo": "Domine a marcação a mercado pela Duration Modificada em títulos IPCA+, o diferencial de juros no Carry Trade de câmbio, o hedge macro e o rebalanceamento sistemático por bandas.",
        "topicos": [
            "Duration modificada: impacto de +100 bps na taxa de juros real sobre títulos IPCA+ longos.",
            "Carry trade e paridade descoberta de juros em pares como USD/JPY e EUR/USD.",
            "Rebalanceamento sistemático por bandas de peso (vender o que subiu demais, comprar o que caiu).",
        ],
        "estudo_completo": {
            "introducao": (
                "Muitos investidores tratam Renda Fixa como sinônimo de ausência de volatilidade — um equívoco custoso em títulos prefixados e indexados à inflação (IPCA+) com vencimentos longos. Embora o retorno contratado seja garantido caso o título seja levado até o vencimento, o preço diário pelo qual o título seria negociado hoje (marcação a mercado) oscila inversamente à taxa de juros exigida pelo mercado, numa proporção aproximada pela Duration Modificada.\n\n"
                "No mercado macro global, a dinâmica de taxas de juros também governa o câmbio através do Carry Trade — comprar moedas de juros elevados financiando-se em moedas de juros baixos (como o iene japonês em longos ciclos). Finalmente, para integrar todas essas classes de ativos em uma carteira viva, o rebalanceamento sistemático por bandas impõe disciplina matemática: vende-se o excesso do ativo que disparou acima da banda e compra-se o ativo descontado abaixo da banda, mantendo o risco fiel ao perfil original e capturando o chamado 'rebalancing bonus' (vender na alta e comprar na baixa de forma automática)."
            ),
            "formula_principal": {
                "titulo": "Sensibilidade por Duration Modificada & Diferencial de Carry",
                "equacao": "ΔP / P ≈ -D_mod × Δy + ½ · Convexidade · (Δy)²   |   Carry ≈ i_long - i_short",
                "interpretacao": "D_mod = Duration Modificada (em anos); Δy = variação instantânea da taxa de juros em decimal (+100 bps = +0,01). O sinal negativo indica relação inversa entre juros de mercado e preço do título.",
            },
            "exemplo_resolvido": {
                "titulo": "Choque de +100 bps em IPCA+ Duration 9 Anos & Carry USD/JPY",
                "cenario": "Parte A: Um título Tesouro IPCA+ com vencimento longo possui Duration Modificada D_mod = 9 anos e negocia a R$ 1.000,00. Parte B: Análise de Carry Trade em câmbio.",
                "passos": [
                    "Passo 1 — Choque de Alta nos Juros (+100 bps = +1,00% = +0,01): Aplicando ΔP/P ≈ -D_mod × Δy = -9 × (+0,01) = -0,09 (-9,0%). O preço do título cai instantaneamente de R$ 1.000 para ~R$ 910 na marcação a mercado.",
                    "Passo 2 — Choque de Queda nos Juros (-100 bps = -0,01): Aplicando a mesma relação, ΔP/P ≈ -9 × (-0,01) = +9,0% (mais um pequeno ganho positivo da convexidade), valorizando o título para ~R$ 1.095 além do carrego.",
                    "Passo 3 — Carry Trade Cambial: Comprar uma moeda com juros de 4,75% a.a. (USD) ou 11%+ (BRL) financiando-se em uma moeda com juros de 0,25% a.a. (JPY) gera diferencial positivo diário (swap), exigindo stop estrutural contra reversões bruscas de risco (unwind).",
                    "Passo 4 — Rebalanceamento por Bandas (±5%): Se Ações Globais têm peso-alvo de 30% (banda 25%–35%) e sobem até 36%, vende-se 6% realocando em Renda Fixa ou Ouro que caiu abaixo do alvo — vendendo caro e comprando barato automaticamente.",
                ],
                "conclusao": "Controlar a Duration no vencimento adequado evita surpresas na marcação a mercado, enquanto bandas de rebalanceamento transformam a volatilidade entre ativos em retorno extra.",
            },
            "erros_comuns": [
                "Comprar Tesouro IPCA+ 2045 para reserva de curto prazo (2 anos) e amargar prejuízo de 15%–25% caso precise resgatar após alta nos juros reais.",
                "Ignorar o risco de apreciação repentina da moeda de funding (ex.: JPY) em operações alavancadas de Carry Trade durante aversão a risco global.",
                "Deixar o ativo mais volátil crescer indefinidamente na carteira sem rebalancear, mudando o perfil de risco original de Moderado para Agressivo sem perceber.",
                "Vender títulos IPCA+ em pânico durante pico de juros reais quando não havia necessidade de liquidez antes do vencimento.",
            ],
            "checklist_pratico": [
                "Conferir a Duration Modificada de qualquer título prefixado ou IPCA+ antes de alocá-lo — casar o prazo com o horizonte da carteira.",
                "Avaliar o calendário de Bancos Centrais (Fed, Copom, BoJ, BCE) ao operar pares sensíveis a diferencial de juros.",
                "Definir bandas de tolerância (ex.: ±5 pontos percentuais) para acionar o rebalanceamento trimestral da carteira.",
                "Utilizar derivativos ou Ouro (GC=F) como hedge de portfólio apenas com dimensionamento compatível ao risco da carteira.",
            ],
        },
        "slides": [
            {
                "titulo": "Duration Modificada & Marcação a Mercado",
                "subtitulo": "Por que títulos IPCA+ longos oscilam como ações antes do vencimento",
                "bullets": [
                    "Duration Modificada mede a sensibilidade percentual do preço do título a variações na taxa de juros.",
                    "ΔP / P ≈ -D_mod × Δy: quanto maior a duration, maior a alavancagem implícita aos juros.",
                    "Com D_mod = 9 anos e alta de +100 bps (+1%), o título cai aproximadamente -9,0% no mercado.",
                    "Se os juros fecharem (-100 bps), ocorre o efeito inverso: ganho de capital de ~+9,0%.",
                ],
                "destaque": "ΔP/P ≈ -9 × (+0,01) = -9,0% para +100 bps na Taxa Real",
                "visual_type": "duration_curve",
            },
            {
                "titulo": "Curva de Carrego vs. Convexidade em IPCA+",
                "subtitulo": "Diferença entre levar até o vencimento e capturar ciclos de juros",
                "bullets": [
                    "Até o vencimento, o título IPCA+ entrega exatamente inflação + juro real contratado.",
                    "No meio do caminho, a curva de preço é convexa: ganhos na queda de juros superam perdas equivalentes na alta.",
                    "Carteiras de 2 anos evitam duration alta para não sofrer marcação negativa no resgate.",
                    "Carteiras de 5–10 anos usam IPCA+ intermediário/longo estrategicamente quando o juro real está esticado.",
                ],
                "destaque": "Casamento de Prazo: Horizonte Curto → Baixa Duration | Longo → Carrego Real",
                "visual_type": "ipca_convexity",
            },
            {
                "titulo": "Carry Trade & Paridade de Juros no Forex",
                "subtitulo": "Capturando o diferencial de taxas entre economias globais",
                "bullets": [
                    "Carry Trade clássico: comprar moeda de taxa de juros alta financiando-se em moeda de juros baixos.",
                    "Exemplo histórico: comprado em USD/BRL ou USD/JPY recebendo swap diário positivo.",
                    "Funciona muito bem em regimes de baixa volatilidade e apetite por risco.",
                    "Risco principal: 'carry unwind' rápido quando choques levam investidores a recomprar a moeda de funding.",
                ],
                "destaque": "Carry Trade = Long Moeda Juros Altos + Short Moeda Juros Baixos",
                "visual_type": "carry_trade",
            },
            {
                "titulo": "Hedge com Ouro & Futuros em Carteiras Multi-Classe",
                "subtitulo": "Protegendo ganhos acumulados sem desmontar posições centrais",
                "bullets": [
                    "Em vez de liquidar toda a carteira em incertezas macro, hedges reduzem o beta líquido.",
                    "Futuros de Índices (ES=F, NQ=F) e Ouro (GC=F) permitem proteção líquida e instantânea.",
                    "O custo do hedge deve ser tratado como prêmio de seguro calibrado ao drawdown tolerado.",
                    "Evite sobre-hedge que neutralize completamente os retornos compostos do portfólio.",
                ],
                "destaque": "Hedge Eficiente = Redução de Variância Mantendo Exposição Estrutural",
                "visual_type": "hedge_derivatives",
            },
            {
                "titulo": "Rebalanceamento Sistemático por Bandas (±5%)",
                "subtitulo": "A regra mecânica para comprar na baixa, vender na alta e travar o risco",
                "bullets": [
                    "Cada classe recebe um peso-alvo (ex.: Ações 30%) e bandas de tolerância (25% a 35%).",
                    "Se uma classe dispara acima da banda superior, realiza-se o excesso.",
                    "Os recursos migram para a classe que ficou descontada abaixo da banda inferior.",
                    "Gera 'rebalancing bonus' e impede que o portfólio fique superconcentrado no topo de bolhas.",
                ],
                "destaque": "Bandas de Peso = Disciplina Antivieses + Rebalancing Bonus",
                "visual_type": "rebalancing_bands",
            },
        ],
        "video_aula": {
            "titulo": "Aula 04: Duration em Renda Fixa, Carry Trade Cambial & Rebalanceamento",
            "duracao_segundos": 240,
            "instrutor": "Camila Duarte • Estrategista de Portfólios & Macro",
            "audio_url": "/static/audio/academia_mod_04.mp3",
            "audio_voz": "pt-BR-ThalitaMultilingualNeural",
            "capitulos": [
                {
                    "tempo_inicio": 0,
                    "titulo": "1. Duration Modificada e Marcação a Mercado (-9%)",
                    "destaque_visual": "D_mod = 9a  &  +100 bps  ⇒  ΔP ≈ -9,0%",
                    "visual_mode": "duration_curve",
                    "roteiro": "Bem-vindo ao nosso quarto e último módulo da certificação. Muita gente acredita que renda fixa nunca cai, mas títulos longos balançam forte na tela. Imagina fechar um contrato de aluguel fixo por vinte anos e, logo depois, os aluguéis do bairro inteiro dispararem: para repassar seu contrato hoje para outra pessoa, você precisa dar um bom desconto no valor à vista. Na marcação a mercado, quem mede o tamanho dessa gangorra é a Duration Modificada. Olha essa curva na tela: pegue um título I-P-C-A mais com duration modificada de nove anos, valendo mil reais. Se os juros reais subirem cem pontos-base de repente — um ponto percentual — multiplicamos nove por um e a queda aproximada é de nove por cento no preço, indo para novecentos e dez reais. Mas isso destrói a taxa contratada?",
                },
                {
                    "tempo_inicio": 48,
                    "titulo": "2. Convexidade do Preço vs. Carrego até o Vencimento",
                    "destaque_visual": "Alta de Juros = Queda Preço | Queda Juros = Ganho Real",
                    "visual_mode": "ipca_convexity",
                    "roteiro": "Essa resposta separa quem vende no susto de quem entende a curva do título. Pense numa passagem de avião com destino garantido versus tentar revender o bilhete no saguão no meio da escala. Se você levar o título I-P-C-A mais até o vencimento, recebe exatamente a inflação mais o juro real contratado na compra. No meio do trajeto, a curva é convexa: se os juros fecharem cem pontos-base, o ganho supera nove por cento, indo perto de mil e noventa e cinco reais. O erro grave está no descasamento de prazos: carteiras de dois anos fogem de duration longa, como um I-P-C-A dois mil e quarenta e cinco, enquanto carteiras de cinco a dez anos aproveitam picos de juros reais. Agora vamos ver como diferenças de juros movem o câmbio.",
                },
                {
                    "tempo_inicio": 98,
                    "titulo": "3. Mecânica do Carry Trade no Mercado de Câmbio",
                    "destaque_visual": "Long Juros Altos (USD) / Short Juros Baixos (JPY)",
                    "visual_mode": "carry_trade",
                    "roteiro": "Essa mesma força das taxas de juros movimenta trilhões por dia no mercado de câmbio por meio do Carry Trade. Imagina tomar um empréstimo quase sem juros em um país para aplicar o dinheiro em outro que remunera muito bem. No Forex, o operador compra a moeda de um país com taxa de juros mais alta financiando-se na moeda de juros mais baixos. É o caso clássico de comprar Dólar a quatro vírgula setenta e cinco por cento ao ano — ou Real acima de onze por cento — financiado em Iene japonês a zero vírgula vinte e cinco por cento, embolsando o diferencial no swap diário positivo. Mas nunca dispense o calendário dos bancos centrais e o stop: em choques de pânico global, o desmonte dessas posições acontece rápido demais. Como blindar a carteira sem liquidar tudo?",
                },
                {
                    "tempo_inicio": 148,
                    "titulo": "4. Uso de Ouro e Derivativos como Hedge Macro",
                    "destaque_visual": "GC=F + Futuros: Blindagem de Eventos de Cauda",
                    "visual_mode": "hedge_derivatives",
                    "roteiro": "Quando a tensão geopolítica ou monetária aperta, muitos investidores zeram a carteira inteira no susto, pagam imposto à toa e ficam de fora da retomada. Fazer hedge é como colocar escoras e lona no telhado antes do temporal, em vez de demolir a casa inteira. Combinando ouro e contratos futuros líquidos de S&P quinhentos e Nasdaq, reduzimos o beta líquido do portfólio sem precisar desmontar as posições centrais de longo prazo. Encare o custo dessa trava como o prêmio de um seguro calibrado ao drawdown que você aceita tolerar: ele blinda eventos de cauda sem cair no erro do sobre-hedge, que anularia os juros compostos. Para fechar nossa jornada, falta a regra mecânica que mantém os pesos no lugar e faz você agir ao contrário da manada.",
                },
                {
                    "tempo_inicio": 195,
                    "titulo": "5. Rebalanceamento Sistemático por Bandas de Peso",
                    "destaque_visual": "Vender Excesso no Topo • Comprar Desconto na Baixa",
                    "visual_mode": "rebalancing_bands",
                    "roteiro": "Fechamos a certificação com o rebalanceamento sistemático por bandas de peso. Na euforia, dá vontade de comprar o que já disparou; na queda, bate o medo de aportar. Rebalancear é como podar um jardim: você apara os galhos que cresceram além da conta para dar água e força ao pé que ficou para trás. Cada classe recebe um peso-alvo e uma banda — por exemplo, trinta por cento em ações globais, aceitando entre vinte e cinco e trinta e cinco por cento. Se subir a trinta e seis, você vende o excesso e compra renda fixa ou ouro descontado abaixo do alvo. Assim, mantém o risco dentro do perfil original e captura o rebalancing bonus, vendendo na alta e comprando na baixa automaticamente. Respire fundo e faça uma excelente prova!",
                },
            ],
        },
    },
]

PROVA_QUESTOES = [
    {
        "id": "q1",
        "enunciado": "1. Um sistema quantitativo possui taxa de acerto (p) de 45% e razão média ganho/perda (b) de 2,5:1. Aplicando o Critério de Kelly completo f* = (b·p - q) / b, qual é aproximadamente a fração ótima de capital por operação?",
        "opcoes": [
            ("a", "12,0%"),
            ("b", "23,0%"),
            ("c", "35,0%"),
            ("d", "8,5%"),
        ],
        "correta": "b",
        "explicacao": "b·p = 2,5 × 0,45 = 1,125; q = 0,55. Logo (1,125 - 0,55) / 2,5 = 0,575 / 2,5 = 0,23 (23,0%). Na prática usa-se Half-Kelly (11,5%) para reduzir volatilidade.",
    },
    {
        "id": "q2",
        "enunciado": "2. Se uma carteira sofre um drawdown de 40%, qual é o ganho percentual mínimo necessário apenas para retornar ao patrimônio inicial (break-even)?",
        "opcoes": [
            ("a", "40,0%"),
            ("b", "50,0%"),
            ("c", "66,7%"),
            ("d", "80,0%"),
        ],
        "correta": "c",
        "explicacao": "Retorno necessário = 1 / (1 - 0,40) - 1 = 1 / 0,60 - 1 = 66,7%. Essa assimetria matemática justifica o uso rígido de Stop Loss.",
    },
    {
        "id": "q3",
        "enunciado": "3. Um título público IPCA+ possui Duration Modificada de 9 anos. Se a taxa de juros real de mercado subir 1,0 ponto percentual (+100 bps) de forma instantânea, qual é a variação aproximada no preço do título por marcação a mercado?",
        "opcoes": [
            ("a", "Queda aproximada de 9,0%"),
            ("b", "Alta aproximada de 9,0%"),
            ("c", "Queda aproximada de 1,0%"),
            ("d", "Permanece inalterado até o vencimento"),
        ],
        "correta": "a",
        "explicacao": "ΔP/P ≈ -Duration_Modificada × Δy = -9 × (+0,01) = -9,0%. Por isso carteiras de curto prazo (2 anos) evitam duration longa.",
    },
    {
        "id": "q4",
        "enunciado": "4. Qual métrica avalia o retorno excedente de um portfólio acima da taxa livre de risco dividido pela sua volatilidade total (desvio-padrão)?",
        "opcoes": [
            ("a", "Beta de Mercado"),
            ("b", "Índice de Sharpe"),
            ("c", "Value at Risk (VaR)"),
            ("d", "Dividend Yield"),
        ],
        "correta": "b",
        "explicacao": "Sharpe = (Rp - Rf) / σp. Mede eficiência por unidade de risco total assumido.",
    },
    {
        "id": "q5",
        "enunciado": "5. Ao dimensionar um Stop Loss via ATR (Average True Range) em um ativo cuja volatilidade dobrou recentemente, o que deve ocorrer para manter o risco financeiro em reais/dólares constante?",
        "opcoes": [
            ("a", "Manter o mesmo tamanho de lote e encurtar o stop pela metade"),
            ("b", "Aumentar a distância do stop proporcionalmente ao ATR e reduzir o tamanho da posição pela metade"),
            ("c", "Dobrar o tamanho da posição e remover o stop"),
            ("d", "Operar apenas com alavancagem máxima fixa"),
        ],
        "correta": "b",
        "explicacao": "Risco ($) = Tamanho da Posição × Distância do Stop. Se o stop dobra por conta do ATR, o tamanho da posição deve cair pela metade.",
    },
    {
        "id": "q6",
        "enunciado": "6. Em uma carteira de longo prazo (10+ anos) composta por ações de tecnologia (NVDA/NDX100), Cripto (BTC) e Ouro (GC=F), qual é o principal papel estrutural do Ouro?",
        "opcoes": [
            ("a", "Maximizar dividendos mensais recorrentes"),
            ("b", "Reduzir a correlação do portfólio e amortecer drawdowns em crises sistêmicas"),
            ("c", "Substituir a reserva de liquidez diária de curto prazo"),
            ("d", "Aumentar o beta direcional em mercados de alta"),
        ],
        "correta": "b",
        "explicacao": "O ouro apresenta baixa/negativa correlação com ativos de risco em eventos de cauda, melhorando o Sharpe da carteira.",
    },
    {
        "id": "q7",
        "enunciado": "7. Uma estratégia tem Expected Value (EV) positivo, porém o trader arrisca 25% do capital em cada trade consecutivo. Qual é o principal risco dessa conduta?",
        "opcoes": [
            ("a", "Risco de ruína por sequência estatística normal de stops (drawdown severo antes da convergência)"),
            ("b", "Impossibilidade de atingir TP2"),
            ("c", "Redução do spread bancário"),
            ("d", "Aumento automático da taxa de acerto"),
        ],
        "correta": "a",
        "explicacao": "Mesmo com EV > 0, apostas superdimensionadas (acima do Kelly) levam à ruína em sequências normais de 4–6 stops seguidos.",
    },
    {
        "id": "q8",
        "enunciado": "8. No mercado de câmbio (Forex), o que caracteriza uma operação clássica de Carry Trade?",
        "opcoes": [
            ("a", "Comprar moeda de país com taxa de juros mais alta financiando-se em moeda de juros mais baixos"),
            ("b", "Operar apenas rompimentos de 1 minuto sem considerar juros"),
            ("c", "Comprar ouro e vender prata no mesmo vencimento"),
            ("d", "Zerar todas as posições antes do fechamento diário"),
        ],
        "correta": "a",
        "explicacao": "Carry trade busca capturar o diferencial de taxas de juros (swap positivo) entre duas economias.",
    },
    {
        "id": "q9",
        "enunciado": "9. Por que uma carteira Conservadora de Curto Prazo (2 anos) concentra maior peso em Pós-Fixado/Liquidez (ex.: Tesouro Selic) do que em Ações e Cripto?",
        "opcoes": [
            ("a", "Porque ativos voláteis podem estar em ciclo de baixa exatamente na data do resgate em 24 meses"),
            ("b", "Porque ações não possuem liquidez na bolsa"),
            ("c", "Porque pós-fixado tem maior retorno esperado em 20 anos que ações globais"),
            ("d", "Porque criptomoedas pagam juros prefixados"),
        ],
        "correta": "a",
        "explicacao": "Em horizontes curtos (2 anos), o risco de sequência de retornos exige preservação de principal e baixa variância.",
    },
    {
        "id": "q10",
        "enunciado": "10. Qual é o efeito do rebalanceamento periódico por bandas (vender excesso do ativo que disparou e comprar o ativo que ficou abaixo do peso-alvo)?",
        "opcoes": [
            ("a", "Controla o risco mantendo o perfil original e captura 'rebalancing bonus' comprando na baixa e vendendo na alta"),
            ("b", "Aumenta a concentração no ativo mais volátil indefinidamente"),
            ("c", "Elimina a necessidade de diversificação"),
            ("d", "Garante retorno fixo livre de risco em qualquer prazo"),
        ],
        "correta": "a",
        "explicacao": "O rebalanceamento sistemático impõe disciplina contrária ao viés emocional, mantendo a volatilidade dentro do perfil escolhido.",
    },
]


_SUBTITLE_REPLACEMENTS = (
    (re.compile(r"\bÁ-Tê-Érre\b"), "ATR"),
    (re.compile(r"\bI-P-C-A\s+dois\s+mil\s+e\s+quarenta\s+e\s+cinco\b"), "IPCA+ 2045"),
    (re.compile(r"\bI-P-C-A\s+mais\b"), "IPCA+"),
    (re.compile(r"\bI-V-V-B\s+onze\b"), "IVVB11"),
    (re.compile(r"\béfe\s+estrela\b"), "f*"),
    (re.compile(r"\bérre\b"), "R"),
    (re.compile(r"\bS&P\s+quinhentos\b"), "S&P 500"),
    (re.compile(r"\bNasdaq\s+cem\b"), "Nasdaq 100"),
)


def format_subtitle_text(text: str) -> str:
    """Normaliza grafias fonéticas usadas no TTS para exibição limpa em tela."""
    cleaned = str(text or "").strip()
    for pattern, repl in _SUBTITLE_REPLACEMENTS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned


def _split_clause_to_limit(clause: str, max_chars: int) -> list[str]:
    """Divide uma cláusula sem pontuação em blocos de até max_chars nos limites de palavras."""
    words = clause.split()
    chunks = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip() if cur else w
        if cur and len(cand) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    return chunks


def _split_sentence_balanced(sentence: str, max_chars: int) -> list[str]:
    """Divide uma frase longa em pausas naturais mantendo cada bloco <= max_chars."""
    if len(sentence) <= max_chars:
        return [sentence]

    raw_clauses = [c.strip() for c in re.split(r"(?<=[,:;—])\s+", sentence) if c.strip()]
    clauses: list[str] = []
    for c in raw_clauses:
        if len(c) <= max_chars:
            clauses.append(c)
        else:
            clauses.extend(_split_clause_to_limit(c, max_chars))

    if len(clauses) <= 1:
        return _split_clause_to_limit(sentence, max_chars)

    n_chunks = max(2, (len(sentence) + max_chars - 1) // max_chars)
    soft_target = len(sentence) / n_chunks
    chunks: list[str] = []
    cur = ""
    for idx, clause in enumerate(clauses):
        cand = f"{cur} {clause}".strip() if cur else clause
        if not cur:
            cur = clause
            continue
        if len(cand) > max_chars:
            chunks.append(cur)
            cur = clause
            continue
        rem_len = sum(len(c) + 1 for c in clauses[idx:])
        rem_slots = max(1, n_chunks - len(chunks) - 1)
        if len(cur) >= soft_target * 0.75 and rem_len <= rem_slots * max_chars:
            chunks.append(cur)
            cur = clause
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    return chunks


def _split_long_subtitle(inicio: float, fim: float, texto: str, max_chars: int = 165) -> list[dict]:
    """Divide legendas muito longas mantendo o intervalo temporal total sincronizado."""
    ini = round(float(inicio), 3)
    end = round(max(float(fim), ini), 3)
    clean = str(texto or "").strip()
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [{"inicio": ini, "fim": end, "texto": clean}]

    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean) if p.strip()]
    parts: list[str] = []
    for sent in sentences or [clean]:
        parts.extend(_split_sentence_balanced(sent, max_chars))

    if len(parts) <= 1:
        return [{"inicio": ini, "fim": end, "texto": clean}]

    total_chars = max(1, sum(len(p) for p in parts))
    total_span = max(0.0, end - ini)
    cursor = ini
    segments = []
    for idx, part in enumerate(parts):
        if idx == len(parts) - 1:
            seg_end = end
        else:
            seg_end = round(cursor + total_span * (len(part) / total_chars), 3)
            seg_end = min(end, max(cursor, seg_end))
        segments.append({"inicio": round(cursor, 3), "fim": seg_end, "texto": part})
        cursor = seg_end
    return segments


def _hydrate_academy_audio_manifest() -> None:
    """Hidrata metadados reais de áudio e legendas sincronizadas a partir do manifesto gerado."""
    manifest_path = Path(__file__).resolve().parent / "static" / "audio" / "academia_audio_manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return

    modules_map = manifest.get("modules", {})
    if not isinstance(modules_map, dict):
        return

    for mod in MODULOS_EDUCACIONAIS:
        m_info = modules_map.get(mod.get("numero"))
        if not isinstance(m_info, dict):
            continue
        video = mod.get("video_aula")
        if not isinstance(video, dict):
            continue

        if m_info.get("duracao_segundos") is not None:
            video["duracao_segundos"] = round(float(m_info["duracao_segundos"]), 2)
        if m_info.get("audio_url"):
            video["audio_url"] = str(m_info["audio_url"])
        if m_info.get("audio_voz"):
            video["audio_voz"] = str(m_info["audio_voz"])

        cap_manifest = m_info.get("capitulos", [])
        for idx, cap in enumerate(video.get("capitulos", [])):
            if idx >= len(cap_manifest) or not isinstance(cap_manifest[idx], dict):
                continue
            c_info = cap_manifest[idx]
            if c_info.get("tempo_inicio") is not None:
                cap["tempo_inicio"] = round(float(c_info["tempo_inicio"]), 2)
            raw_subs = c_info.get("legendas")
            if isinstance(raw_subs, list):
                hydrated_subs = []
                for item in raw_subs:
                    if not isinstance(item, dict) or not item.get("texto"):
                        continue
                    clean_text = format_subtitle_text(str(item["texto"]))
                    hydrated_subs.extend(
                        _split_long_subtitle(float(item["inicio"]), float(item["fim"]), clean_text)
                    )
                cap["legendas"] = hydrated_subs


_hydrate_academy_audio_manifest()

