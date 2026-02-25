# 📊 Dashboard GD — Stine

Dashboard interno de **Geração de Demanda (GD)** da Stine Sementes, desenvolvido em Streamlit. Consolida e visualiza dados de ensaios de campo — desde o plantio até a colheita — permitindo acompanhar a performance de materiais STINE frente à concorrência em toda a base de produtores.

---

## 🌾 O que é este dashboard?

O **Dashboard GD Stine** é uma ferramenta de inteligência comercial e agronômica que centraliza informações de ensaios de geração de demanda realizados em propriedades rurais. Cada **área** representa um ensaio onde um cultivar ou híbrido (de soja ou milho) é plantado em uma faixa da propriedade de um produtor parceiro. Após a colheita, o resultado é avaliado em **sacas por hectare (sc/ha)**, comparando o desempenho dos materiais STINE com os da concorrência.

Os dados são carregados em tempo real a partir de uma view no **Supabase** (`view_gd_resultados_dashboard`), com cache de 10 minutos.

---

## 🗂️ Páginas e Funcionalidades

### 📍 Áreas
Visão geral da carteira de ensaios, com foco em distribuição geográfica e mix de materiais.

- **KPIs principais:** total de áreas, produtores ativos, proporção de ensaios com resultado vs. aguardando colheita.
- **Visão Hierárquica Regional → Cidade → RC → Produtor:** expanders interativos por regional mostrando saúde dos ensaios por cidade (semáforo 🟢🟡🔴 baseado em % com resultado), cultura dominante, responsável comercial (RC), produtor principal e % de penetração STINE.
- **Distribuição por status:** gráfico de pizza/barras mostrando áreas com resultado, aguardando colheita e não definidas.
- **Mix STINE vs. Concorrência:** distribuição de ensaios por categoria de material.
- **Classificação de produtores:** segmentação por percentual STINE (100% STINE, Maioria STINE, Misto, Maioria Concorrência, 100% Concorrência).
- **Perfil de potencial:** gráfico de barras em espelho (soja vs. milho) por faixa de área plantada, com tabela interativa (AgGrid) e indicadores de faixa dominante.

### 📈 Performance de Materiais
Análise aprofundada dos resultados agronômicos dos ensaios concluídos.

- **KPIs de panorama:** total de áreas avaliadas, áreas em campo, potencial de soja e milho na base (em ha), cobertura de GD por produtor.
- **Marcha de plantio:** evolução semanal acumulada do percentual de áreas plantadas, com zonas de referência coloridas e tamanho dos pontos proporcional à quantidade de plantios na semana.
- **Análise comparativa de materiais:** gráficos de dispersão e box plots comparando a produtividade (sc/ha) dos materiais STINE frente à concorrência, com médias destacadas.
- **Análise geográfica:** distribuição dos resultados por Regional, Estado ou Cidade — com pontos individuais (jitter), marcador de média por região e paleta de cores diferenciada para STINE vs. concorrência.

---

## 🔍 Filtros Globais

Os filtros ficam na barra lateral e se aplicam a todas as páginas:

| Filtro | Opções |
|---|---|
| **Cultura** | Todos / Soja / Milho |
| **Safra** | Todas as safras disponíveis na base |

---

## 🎨 Identidade Visual

O dashboard segue a paleta oficial da Stine Sementes:

| Cor | Uso |
|---|---|
| `#005FAE` (Azul Stine) | Milho, cor primária |
| `#009D57` (Verde Stine) | Soja |
| `#7ED321` | Áreas com resultado |
| `#4A90D9` | Áreas aguardando colheita |
| `#9E9E9E` | Não definido |

---

## 🛠️ Tecnologias

| Lib | Uso |
|---|---|
| [Streamlit](https://streamlit.io) `>=1.35` | Framework principal |
| [Pandas](https://pandas.pydata.org) `>=2.0` | Manipulação de dados |
| [Plotly](https://plotly.com/python/) `>=5.18` | Gráficos interativos |
| [Supabase Python](https://github.com/supabase/supabase-py) `>=2.4` | Banco de dados / API |
| [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid) `>=0.3.4` | Tabelas interativas |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Variáveis de ambiente (local) |

---

## ⚙️ Estrutura do Projeto

```
.
├── app.py              # Página principal (Áreas) + lógica de dados
├── performance.py      # Página de Performance de Materiais
├── requirements.txt    # Dependências Python
├── .streamlit/
│   └── config.toml     # Tema e configurações do Streamlit
└── .env                # Credenciais locais (NÃO versionar)
```

---

## 🚀 Como Rodar Localmente

**1. Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/seu-repo.git
cd seu-repo
```

**2. Instale as dependências:**
```bash
pip install -r requirements.txt
```

**3. Configure as variáveis de ambiente:**

Crie um arquivo `.env` na raiz do projeto:
```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sua_service_role_key
```

**4. Execute o app:**
```bash
streamlit run app.py
```

---

## ☁️ Deploy no Streamlit Community Cloud

**1.** Certifique-se que `.env` está no `.gitignore` e que o repositório está no GitHub.

**2.** Acesse [share.streamlit.io](https://share.streamlit.io) e clique em **New app**.

**3.** Selecione o repositório, a branch e o arquivo `app.py`.

**4.** Antes de clicar em Deploy, vá em **Advanced settings → Secrets** e adicione:

```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sua_service_role_key"
```

**5.** Clique em **Deploy** 🚀

> O app irá acessar as secrets via `os.getenv()`, que funciona tanto com o `.env` local quanto com os Secrets do Streamlit Cloud.

---

## 📦 Fonte dos Dados

Os dados são consumidos diretamente via Supabase SDK da view:

```
view_gd_resultados_dashboard
```

As principais dimensões disponíveis incluem: produtor, fazenda, cultura, material, regional, estado, cidade, RC responsável, datas de plantio e colheita, produtividade (sc/ha), umidade, peso de mil grãos e área plantada.

---

## 🔒 Segurança

- Nunca versione o arquivo `.env`
- Utilize a **Service Role Key** do Supabase com cuidado — ela bypassa as políticas de RLS
- Para ambientes de produção, considere restringir permissões via RLS no Supabase

---

*Desenvolvido para uso interno — Stine Sementes.*
