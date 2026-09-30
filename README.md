# ECHO

![https://www.python.org/downloads/release/python-31315/](https://img.shields.io/badge/3.13.15-3776AB?style=flat-square&logo=python&logoColor=white&label=Python)
![https://reflex.dev/](https://img.shields.io/badge/0.8.28-6E56CF?style=flat-square&logo=reflex&logoColor=white&label=Reflex)
![https://reflex.dev/](https://img.shields.io/badge/WSL2-2496ED?style=flat-square&logo=docker&logoColor=white&label=Docker)

## O que o Echo faz
- **Monitoramento em Tempo Real:** Dispara testes de ping simultâneos para verificar a conectividade e a latência de dispositivos na rede.

- **Dashboard Dinâmico:** Exibe um painel visual atualizado automaticamente, organizado por grupos, com gráficos de histórico que só carregam quando expandidos para economizar memória.

- **Alertas e Segurança:** Possui sistema de login seguro para administradores e dispara alertas automáticos por e-mail quando equipamentos críticos ficam offline.

## Como gerenciar os ativos
- **Pela Interface Web:** Adicione, edite ou remova equipamentos individualmente direto no painel, sem precisar mexer no código.

- **Importação em Massa (CSV):** Suba um arquivo .csv com a lista dos seus IPs, nomes, locais e grupos, e o sistema faz a validação e o cadastro de todos os equipamentos de uma só vez no banco de dados.

## Hospedagem e Configuração via Docker

Esta aplicação pode ser executada em ambiente de produção containerizado utilizando **Docker** e **Docker Compose**. O ambiente já inclui suporte ao **Bun** (exigido pelo Reflex para compilação do frontend) e resolução de DNS para monitorar ativos da rede local por *hostname*.

---

### Pré-requisitos

* **Docker Desktop** instalado (com suporte a WSL 2 ativo, caso utilize Windows).
* IP estático configurado na máquina hospedeira para garantir acesso consistente na rede.

---

### Arquivos de Implantação

Certifique-se de que os seguintes arquivos estejam presentes na raiz do projeto:

#### 1. `Dockerfile`
```dockerfile
FROM python:3.13.15-slim

# Instalar dependências do sistema para o Bun e ferramentas de rede
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    ca-certificates \
    git \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Instalar o Bun oficial (exigido pelo Reflex 0.9+)
RUN curl -fsSL [https://bun.sh/install](https://bun.sh/install) | bash
ENV PATH="/root/.bun/bin:${PATH}"

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Executar migração do banco e subir o servidor em produção
CMD ["sh", "-c", "reflex db migrate && reflex run --env prod"]