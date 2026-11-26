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
        "titulo": "Assimetria & A Matemática do Lucro (Para Iniciantes)",
        "duracao": "18 min",
        "nivel": "Iniciante • Essencial",
        "resumo": "Por que você não precisa acertar 90% das vezes para lucrar alto no mercado. Aprenda como a regra de ganhar muito nos acertos e perder pouco nos erros protege seu dinheiro e constrói patrimônio consistente.",
        "topicos": [
            "O mito da alta taxa de acerto: como lucrar consistentemente acertando apenas 45% a 50% das operações.",
            "A assimetria do lucro: como o Stop Loss trava seu prejuízo e os Alvos (TP1 e TP2) multiplicam seu retorno.",
            "A matemática do Drawdown: por que evitar perdas grandes é a única regra obrigatória para nunca quebrar.",
        ],
        "estudo_completo": {
            "introducao": (
                "Seja muito bem-vindo à Academia Heurístika! Se você é iniciante no mercado financeiro, a primeira lição que vai transformar seus resultados é esta: você NÃO precisa prever o futuro nem ter uma taxa de acerto de 90% para ganhar dinheiro de verdade.\n\n"
                "A maioria das pessoas que perde dinheiro no mercado comete o mesmo erro clássico: buscam acertar quase todas as operações, arriscando perder R$ 500 para ganhar meros R$ 30. Quando erram uma única vez, devolvem semanas de pequenos lucros. Na metodologia Heurístika, nós fazemos exatamente o oposto: trabalhamos com Assimetria Favorável. Cada operação tem uma perda máxima rigidamente controlada via Stop Loss (por exemplo, -1% do seu capital). Já quando o mercado anda a nosso favor, nossos alvos buscam ganhos de duas a três vezes e meia o valor arriscado (TP1 e TP2).\n\n"
                "Além disso, proteger o capital principal é a lei número um: uma queda de 40% na sua conta exige um ganho posterior de +66,7% só para voltar ao zero a zero! É por isso que utilizamos o Critério de Kelly em sua versão conservadora (Half-Kelly), garantindo que sua conta cresça de forma constante mesmo quando passar por sequências normais de oscilação."
            ),
            "formula_principal": {
                "titulo": "Critério de Kelly, Expectativa Matemática & Recuperação de Drawdown",
                "equacao": "f* = (b · p - q) / b   |   EV = (p · b) - q   |   Rec = 1 / (1 - DD) - 1",
                "interpretacao": "Em português simples: se você arrisca 1 real para buscar 2,50 reais (b = 2,5) e acerta 45% das vezes (p = 0,45), você ganha em média +0,575 real a cada operação. A fórmula de Kelly calcula o tamanho ideal da aposta para maximizar seu crescimento sem correr risco de ruína.",
            },
            "exemplo_resolvido": {
                "titulo": "Cálculo Prático: Começando com R$ 10.000 e Sistema de Payoff 2,5:1",
                "cenario": "Imagine que você começou com R$ 10.000 na sua conta, seguindo os sinais oficiais da Heurístika. O modelo tem taxa de acerto histórica de 45% (erra 55%) e paga em média R$ 2,50 de lucro para cada R$ 1,00 arriscado.",
                "passos": [
                    "Passo 1 — Expectativa Matemática (EV): A cada 100 operações, você ganha 45 vezes (45 × 2,5 = +112,5 unidades) e perde 55 vezes (55 × 1 = -55 unidades). Saldo líquido: +57,5 unidades de lucro! Mesmo errando mais da metade das vezes, o sistema é altamente lucrativo.",
                    "Passo 2 — Quanto Arriscar por Sinal (Kelly): A fórmula matemática teórica (Full Kelly) indica até 23% por sinal, mas esse nível oscila demais.",
                    "Passo 3 — O Modelo Seguro (Half-Kelly Institucional): Na prática da Heurístika, recomendamos arriscar apenas entre 1% e 2% do seu capital total por sinal (R$ 100 a R$ 200 em uma conta de R$ 10.000). Isso corta a oscilação pela metade e protege você totalmente.",
                    "Passo 4 — O Perigo de Apostar Demais: Se você arriscasse 25% por sinal, uma sequência normal de 4 erros seguidos derrubaria sua conta em quase 70%. E lembre-se: recuperar uma perda de 40% exige um ganho de +66,7% líquidos apenas para empatar.",
                ],
                "conclusao": "Com expectativa matemática positiva e risco controlado de 1% a 2%, você não precisa se preocupar com o resultado de uma operação isolada. Você tem a estatística trabalhando a seu favor em uma série de operações disciplinadas.",
            },
            "erros_comuns": [
                "Arriscar mais do que 2% do capital em um único sinal achando que tem 'certeza' de que ele vai dar certo (no mercado, certeza não existe).",
                "Tirar ou empurrar o Stop Loss para longe por medo de aceitar uma perda pequena e controlada.",
                "Fechar operações vencedoras com 10 reais de lucro por ansiedade, deixando de capturar a alta completa projetada no Alvo 2 (TP2).",
                "Julgar o método por apenas 2 ou 3 sinais isolados, em vez de avaliar a média consistente ao longo de um mês ou de um bloco de 20 operações.",
            ],
            "checklist_pratico": [
                "Verificar se a operação oferece um potencial de ganho de pelo menos 2 vezes o tamanho do Stop Loss antes de entrar.",
                "Calcular o tamanho da ordem para que uma perda atinja no máximo 1% a 2% do seu saldo total (utilize a calculadora na Área VIP).",
                "Programar a ordem completa na corretora (Entrada, Stop Loss e Alvos) logo após receber o sinal — nunca opere com stop 'mental'.",
                "Manter a calma diante de um stop loss normal: ele é apenas a proteção que mantém seu capital vivo para a próxima oportunidade.",
            ],
        },
        "slides": [
            {
                "titulo": "Assimetria & Convexidade de Payoff",
                "subtitulo": "Por que perder pequeno e ganhar grande vence a alta taxa de acerto",
                "bullets": [
                    "Estratégias amadoras que buscam 90% de acerto usam stops gigantescos e quebram cedo ou tarde.",
                    "Na Heurístika, cada erro é travado mecanicamente em uma perda pequena e pré-definida via Stop Loss.",
                    "Nossos alvos parciais e finais (TP1 e TP2) capturam ganhos de 2,0x a 3,5x o risco assumido.",
                    "Mesmo acertando menos da metade das vezes (45%), o sistema gera lucro líquido consistente.",
                ],
                "destaque": "EV = (0,45 × 2,5) - 0,55 = +0,575R de lucro médio por operação",
                "visual_type": "payoff_asymmetry",
            },
            {
                "titulo": "Curva do Critério de Kelly (Full vs Half)",
                "subtitulo": "Maximizando o crescimento do seu capital sem risco de ruína",
                "bullets": [
                    "A fórmula matemática de Kelly descobre a velocidade máxima segura para o dinheiro crescer.",
                    "Para o nosso sistema, o teto teórico é 23,0% do capital por trade.",
                    "Na prática real, usamos Half-Kelly fracionado (1% a 2% por sinal) para ter estabilidade e tranquilidade.",
                    "Apostar pesado demais transforma um sistema vencedor em prejuízo por excesso de oscilação.",
                ],
                "destaque": "Regra Prática Heurístika: Arrisque entre 1% e 2% do seu capital por sinal",
                "visual_type": "kelly_curve",
            },
            {
                "titulo": "A Matemática Implacável do Drawdown",
                "subtitulo": "Por que a proteção do capital principal antecede qualquer busca por retorno",
                "bullets": [
                    "Perder e ganhar não têm a mesma proporção: sua base de dinheiro encolhe a cada prejuízo.",
                    "Uma perda de 10% exige apenas +11,1% de ganho para voltar ao zero a zero.",
                    "Uma perda de 40% exige +66,7% de lucro líquido apenas para empatar a conta.",
                    "Se você perder 50%, precisará de +100% (dobrar o que sobrou) só para recuperar o ponto de partida.",
                ],
                "destaque": "Perda de -40%  →  Exige +66,7% para recuperação (Implacável)",
                "visual_type": "drawdown_asymmetry",
            },
            {
                "titulo": "Convergência Estatística & Sequências de Perda",
                "subtitulo": "Sobrevivendo com tranquilidade às oscilações naturais de qualquer mercado",
                "bullets": [
                    "Mesmo nos melhores sistemas do mundo, sequências de 3 a 5 stops consecutivos acontecem naturalmente.",
                    "Quem arrisca 20% por operação perde mais de 60% do dinheiro em uma sequência dessas.",
                    "Quem segue a regra de 1% a 2% por sinal perde apenas 5% a 8% e segue com a conta blindada.",
                    "O investidor disciplinado preserva o capital para colher os próximos alvos cheios de TP1 e TP2.",
                ],
                "destaque": "Risco 1% a 2% por trade: conta protegida mesmo em sequências difíceis",
                "visual_type": "ev_matrix",
            },
            {
                "titulo": "Engenharia Comportamental Anti-Viés",
                "subtitulo": "Substituindo o medo e a ansiedade por regras matemáticas automáticas",
                "bullets": [
                    "Aversão à perda: psicologicamente, a dor de perder pesa duas vezes mais que a alegria de ganhar.",
                    "O perigo do improviso: quem não usa regras automáticas fecha os ganhos cedo e segura os prejuízos.",
                    "Nosso protocolo oficial: Entrada, Stop Loss, Alvo 1 e Alvo 2 programados antes do clique.",
                    "Auditoria em tempo real: todas as operações são registradas em banco de dados sem edição humana.",
                ],
                "destaque": "Disciplina Automática = Lucro no Longo Prazo",
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
        "titulo": "Como Executar Sinais na Prática: Entrada, Stop Loss e Alvos",
        "duracao": "20 min",
        "nivel": "Prático • Passo a Passo",
        "resumo": "Aprenda passo a passo como pegar um sinal da Heurístika e colocá-lo na sua corretora. Saiba onde programar o Stop Loss de proteção e como colher lucros no Alvo 1 e Alvo 2 sem precisar ficar colado na tela.",
        "topicos": [
            "Entendendo os 4 números de cada sinal: Ativo, Ponto de Entrada, Stop Loss de proteção e Alvos de Lucro (TP1 e TP2).",
            "Por que o Stop Loss evita violinadas do mercado e deve ser proporcional à oscilação real (ATR) do ativo.",
            "A estratégia do Breakeven: como colocar lucro no bolso em TP1 e conduzir o restante com risco zero até TP2.",
        ],
        "estudo_completo": {
            "introducao": (
                "Recebeu uma notificação de sinal no Telegram ou no Painel VIP da Heurístika e quer saber exatamente o que fazer? Este módulo é o seu manual de campo prático.\n\n"
                "Um erro clássico de quem começa é usar stops 'de cabeça' ou fixos (como 'sempre 1% do preço' ou 'sempre 20 centavos'), sem considerar como o ativo se move. Um stop de 1% em um par de moedas calmo é largo, enquanto em Bitcoin ou numa ação após divulgação de balanço é facilmente atingido pelo balanço normal dos primeiros 5 minutos.\n\n"
                "Na Heurístika, cada sinal já vem calculado com base no Average True Range (ATR), que é a amplitude real média de oscilação do ativo. Isso significa que nosso Stop Loss fica fora da zona de ruído aleatório. E a regra mais importante de todas: quando o mercado oscila mais, o stop fica mais longo para proteger você, mas o número de ações ou contratos é reduzido na mesma proporção — mantendo o seu prejuízo financeiro máximo em reais rigorosamente idêntico."
            ),
            "formula_principal": {
                "titulo": "Dimensionamento Inverso à Volatilidade & Risco Financeiro Constante",
                "equacao": "Risco ($) = Lote × |Entrada - Stop|   ⇒   Lote = (Capital × Risco%) / (k · ATR₁₄)",
                "interpretacao": "Em português claro: se o mercado está agitado e o Stop Loss precisa ficar mais distante para não tomar violinada, nós diminuímos a quantidade de ações compradas. Assim, se a operação der errado, você perde exatamente os mesmos R$ 100 ou R$ 500 que havia planejado.",
            },
            "exemplo_resolvido": {
                "titulo": "Adaptação de Lote na Prática: Protegendo R$ 500 de Risco Fixo",
                "cenario": "Você tem R$ 50.000 e decidiu arriscar no máximo 1% por sinal (perda máxima de R$ 500 se o stop for atingido). O sinal indica compra a R$ 100,00.",
                "passos": [
                    "Passo 1 — Mercado Normal (Stop a R$ 3,00 de distância): Seu Stop Loss fica em R$ 97,00. Quantas ações comprar? R$ 500 / R$ 3,00 = 166 ações. Se cair a R$ 97,00, você perde exatamente R$ 500.",
                    "Passo 2 — Mercado Muito Volátil (Stop a R$ 6,00 de distância): Para não ser estopado por oscilação à toa, o Stop Loss vai para R$ 94,00. O que fazer com as ações?",
                    "Passo 3 — Ajuste Automático: Dividimos R$ 500 / R$ 6,00 = 83 ações (metade do lote anterior!). Se cair a R$ 94,00, você perde exatamente os mesmos R$ 500.",
                    "Passo 4 — Realizando o Lucro (TP1 e TP2): O preço subiu para R$ 104,00 (Alvo 1). Você vende 50% das suas ações e embolsa o lucro! Em seguida, puxa o Stop Loss das ações restantes para R$ 100,00 (o preço em que você comprou). Agora você tem risco ZERO e pode esperar o Alvo 2 a R$ 107,00 com total paz de espírito.",
                ],
                "conclusao": "Não importa se o mercado está calmo ou tempestuoso: o seu risco financeiro em Reais fica sempre blindado e previsível.",
            },
            "erros_comuns": [
                "Aumentar o tamanho da ordem após uma vitória achando que 'está com sorte' (mantenha o risco percentual sempre constante).",
                "Colocar o Stop Loss em números redondos óbvios (como R$ 50,00 ou R$ 10,00), onde os grandes bancos e robôs caçam ordens de iniciantes.",
                "Não programar a ordem OCO (One Cancels Other) na corretora e esquecer a operação aberta sem proteção.",
                "Ver o preço bater no Alvo 1 (TP1) e não puxar o stop para o preço de entrada (breakeven), correndo o risco de ver um lucro virar prejuízo.",
            ],
            "checklist_pratico": [
                "Abra a notificação do sinal e identifique: Ativo, Direção (Compra/Venda), Entrada, Stop Loss, TP1 e TP2.",
                "Use a calculadora da Área VIP Heurístika para saber exatamente quantas cotas ou contratos comprar com base no seu saldo.",
                "Envie a ordem com Stop Loss e Alvos já cadastrados no seu Home Broker ou app da corretora.",
                "Assim que o robô avisar que o Alvo 1 (TP1) foi atingido, realize 50% do lucro e mova o stop da outra metade para o preço de entrada.",
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
        "titulo": "Gestão de Risco Simples: Quanto Investir por Sinal sem Perigo",
        "duracao": "22 min",
        "nivel": "Iniciante ao Avançado",
        "resumo": "A regra de ouro de 1% a 2% por sinal que impede qualquer investidor de quebrar. Saiba como calcular o tamanho exato da sua ordem e como estruturar sua carteira por prazos (2, 5 e 10+ anos) maximizando o retorno.",
        "topicos": [
            "A regra de ouro de arriscar no máximo 1% a 2% do capital total em cada sinal.",
            "Como dividir seus recursos entre operações rápidas (sinais) e investimentos de curto, médio e longo prazo.",
            "O papel protetor do Ouro e de ativos descorrelacionados para amortecer crises e manter seus ganhos.",
        ],
        "estudo_completo": {
            "introducao": (
                "Se você pudesse levar apenas uma única lição de toda a Academia para o resto da sua vida como investidor, seria esta: a gestão de risco é o que separa quem constrói riqueza duradoura de quem perde tudo no mercado.\n\n"
                "Muitos iniciantes começam cometendo o erro de aplicar dinheiro que vão precisar daqui a 1 ou 2 anos (como a compra de um imóvel ou uma viagem) em ações voláteis ou criptomoedas. Se o mercado entra em um ciclo de baixa temporário exatamente no mês em que o dinheiro precisa ser sacado, a pessoa é forçada a vender no prejuízo. Isso se chama 'risco de sequência de retornos'.\n\n"
                "Para evitar isso, organizamos a carteira em 3 horizontes: Curto Prazo (2 anos), onde a prioridade é segurança e liquidez (como Tesouro Selic); Médio Prazo (5 anos), equilibrando inflação (IPCA+), dividendos de fundos imobiliários e ações; e Longo Prazo (10+ anos), onde os juros compostos multiplicam seu patrimônio através de tecnologia global e ativos escassos. A métrica que os grandes fundos usam para medir se uma carteira é eficiente é o Índice de Sharpe: ele mede quanto lucro a carteira gera para cada gota de risco que você assume."
            ),
            "formula_principal": {
                "titulo": "Índice de Sharpe & Eficiência Risco-Retorno de Portfólio",
                "equacao": "Sharpe = (Rp - Rf) / σp   |   σ²_port = Σ wᵢ²σᵢ² + ΣΣ wᵢwⱼρᵢⱼσᵢσⱼ",
                "interpretacao": "Em termos simples: o Índice de Sharpe mostra a qualidade da sua carteira. Duas pessoas podem ganhar 15% no ano: se uma passou o ano inteiro sem conseguir dormir com oscilações bruscas e a outra teve um caminho suave e diversificado, a segunda teve um Sharpe muito superior e um risco muito menor.",
            },
            "exemplo_resolvido": {
                "titulo": "Comparando Duas Carteiras Reais: Concentrada vs. Inteligente Heurístika",
                "cenario": "Vamos comparar dois investidores com R$ 100.000 aplicados, considerando uma taxa livre de risco (Selic) de 10,5% ao ano.",
                "passos": [
                    "Passo 1 — Investidor Afobado (100% em Cripto e Ações Arriscadas): Teve um retorno de 18% ao ano, mas com uma oscilação gigantesca de 26% (Sharpe = 0,29). Quase infartou nos meses de queda e quase vendeu no fundo.",
                    "Passo 2 — Investidor Inteligente (Carteira Diversificada Heurístika + 10% Ouro): Teve um retorno de 16,5% ao ano com oscilação de apenas 12% (Sharpe = 0,50).",
                    "Passo 3 — O Salto de Qualidade: O investidor inteligente teve 72% mais eficiência de risco! Ele ganhou quase o mesmo tanto, mas dormindo tranquilo todas as noites.",
                    "Passo 4 — Separando por Prazos: O dinheiro que você vai usar em até 24 meses fica 100% seguro em pós-fixado. Já o dinheiro dos sinais e do longo prazo fica livre para buscar multiplicações assimétricas.",
                ],
                "conclusao": "Diversificação inteligente com ativos que se protegem mutuamente (como o Ouro nas crises) é o verdadeiro segredo para permanecer no jogo e enriquecer com consistência.",
            },
            "erros_comuns": [
                "Colocar o dinheiro do aluguel ou de contas do mês que vem em operações de sinais rápidos (sinais devem ser operados com capital de risco).",
                "Olhar apenas para a rentabilidade passada sem medir o risco de queda máxima (drawdown).",
                "Achar que comprar 10 ações diferentes de bancos é estar diversificado (se o setor sofrer, todas caem juntas).",
                "Ignorar ativos de proteção como Ouro achando que 'não rendem nada': na hora do pânico mundial, o ouro é o airbag que salva o seu patrimônio.",
            ],
            "checklist_pratico": [
                "Separe seu dinheiro em gavetas: reserva de emergência (liquidez diária), carteira de médio prazo e capital dos sinais.",
                "Nos sinais da Heurístika, nunca comprometa mais que 1% a 2% do seu saldo total por entrada.",
                "Mantenha uma fatia em dólar ou índices globais para não ficar refém apenas da economia brasileira.",
                "Revise sua alocação periodicamente no simulador da página de Carteiras.",
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
        "titulo": "Mentalidade Blindada, Proteção Patrimonial & Rebalanceamento",
        "duracao": "24 min",
        "nivel": "Comportamental & Estratégia",
        "resumo": "Como proteger seu dinheiro contra oscilações de juros, inflação e câmbio, manter a disciplina psicológica e usar o rebalanceamento automático para vender na alta e comprar na baixa sem estresse.",
        "topicos": [
            "Por que títulos de renda fixa de longo prazo oscilam como ações antes do vencimento (marcação a mercado).",
            "Como o rebalanceamento automático por bandas vende o que subiu muito e compra o que ficou barato.",
            "Blindagem psicológica: como manter a consistência e colher lucros ano após ano sem ansiedade.",
        ],
        "estudo_completo": {
            "introducao": (
                "Chegamos ao módulo final da sua jornada na Academia Heurístika. Aqui conectamos a psicologia do investidor com a mecânica de proteção do seu patrimônio.\n\n"
                "Muitos iniciantes acreditam que 'Renda Fixa' significa que o dinheiro nunca oscila. Isso só é verdade se você deixar o título até o dia do vencimento. Se você comprar um título de inflação longo (como Tesouro IPCA+ 2045) e precisar vender antes, o preço de venda varia todos os dias (marcação a mercado): se as taxas de juros sobem, o valor de venda cai; se as taxas caem, o título valoriza muito. Entender isso evita que você compre títulos longos para objetivos de curto prazo.\n\n"
                "Por fim, para manter seus lucros crescendo no piloto automático sem que você precise tentar adivinhar topos e fundos, os profissionais usam o Rebalanceamento por Bandas. Funciona assim: se suas ações subiram muito e passaram do limite planejado, você vende um pedaço do lucro e compra o que está barato e descontado. Você vende na alta e compra na baixa de forma 100% matemática, sem emoção e sem achismos."
            ),
            "formula_principal": {
                "titulo": "Sensibilidade por Duration Modificada & Diferencial de Carry",
                "equacao": "ΔP / P ≈ -D_mod × Δy + ½ · Convexidade · (Δy)²   |   Carry ≈ i_long - i_short",
                "interpretacao": "Em termos simples: se um título tem prazo longo (Duration 9 anos) e o juro sobe 1%, o título desvaloriza cerca de 9% se você for vender naquele dia. Se os juros caem 1%, ele valoriza 9%. O rebalanceamento aproveita essas oscilações para comprar barato e vender caro.",
            },
            "exemplo_resolvido": {
                "titulo": "Rebalanceamento na Prática: Lucrando com o Efeito Gangorra",
                "cenario": "Você montou uma carteira com 50% em Renda Fixa e 50% em Ações/Sinais Heurístika, com capital de R$ 100.000 (R$ 50.000 em cada).",
                "passos": [
                    "Passo 1 — Mercado em Alta: Graças aos sinais e à valorização do mercado, sua fatia de Ações salta para R$ 70.000, enquanto a Renda Fixa foi para R$ 52.000. Saldo total: R$ 122.000 (a fatia de ações virou quase 60%).",
                    "Passo 2 — O Que o Amador Faz? O amador se empolga, acha que nada vai cair e compra mais ações no topo histórico.",
                    "Passo 3 — O Que o Investidor Inteligente Faz (Rebalanceamento): Você vende R$ 9.000 de ações (colocando o lucro no bolso no topo) e aplica na Renda Fixa, voltando para o equilíbrio de 50/50 (R$ 61.000 em cada).",
                    "Passo 4 — A Mágica do Longo Prazo: Quando o mercado passa por uma correção natural, você tem muito dinheiro protegido na Renda Fixa para recomprar ativos excelentes a preços de liquidação.",
                ],
                "conclusao": "O rebalanceamento automático é a única estratégia que obriga você psicologicamente a sempre vender na euforia e comprar no pessimismo.",
            },
            "erros_comuns": [
                "Comprar Tesouro IPCA+ com vencimento em 2045 com dinheiro que você vai precisar usar em 2027.",
                "Deixar a carteira correr solta por anos sem rebalancear, até perceber que está correndo 3 vezes mais risco do que planejou.",
                "Operar por vingança: após um stop loss, entrar correndo em outra operação sem análise só para tentar recuperar rápido (é o caminho mais curto para quebrar).",
                "Vender investimentos de longo prazo em pânico no meio de uma notícia negativa de jornal.",
            ],
            "checklist_pratico": [
                "Defina seu horizonte: dinheiro de curto prazo em Tesouro Selic; dinheiro de longo prazo em títulos e ações.",
                "Revise sua carteira a cada 3 ou 6 meses para rebalancear as classes de ativos.",
                "Nunca opere sinais por impulso: espere a notificação oficial do robô com Entrada, Stop e Alvos.",
                "Após concluir os 4 módulos, faça a Avaliação da Academia para emitir seu Certificado de Certificação Heurístika.",
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

