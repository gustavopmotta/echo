# Usa uma versão oficial e leve do Python
FROM python:3.13.15-slim

# Instala ferramentas básicas que o Reflex usa nos bastidores
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

# Instala o Bun oficial e adiciona às variáveis de ambiente (PATH)
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências do seu projeto
# (Certifique-se de ter um arquivo requirements.txt com 'reflex', 'sqlmodel', 'bcrypt', etc)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do seu painel Echo
COPY . .

# Comando que o container vai rodar ao ligar
CMD ["sh", "-c", "reflex db migrate && reflex run --env prod"]