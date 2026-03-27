<div align="center">
<h1>ECHO.</h1>

![Reflex](https://img.shields.io/badge/Reflex-6E56CF?style=flat-square&logo=reflex&label=Framework)
![Python](https://img.shields.io/badge/3.13-3776AB?style=flat-square&logo=python&label=Python)
</div>

O Echo é uma ferramenta de código aberto desenvolvida em Python para monitorar a conectividade e a latência de ativos de rede interna. Utilizando o framework Reflex, o sistema fornece um painel web em tempo real para visualização do status de roteadores, switches, servidores e outros dispositivos.

## Funcionalidades Principais

* Monitoramento Contínuo: Dispara testes de latência (ping) em intervalos regulares configuráveis.
* Dashboard Dinâmico: Interface web responsiva que atualiza automaticamente sem necessidade de recarregar a página.
* Indicadores Visuais: Classificação automática do status de cada ativo:
   * Conexão estável e latência normal.
   * O equipamento responde, mas o tempo de resposta está acima do limite aceitável.
   * Falha na comunicação ou perda de pacotes.
   * Sistema em pausa ou aguardando o primeiro ciclo de testes.
* Lista de Ativos Customizável: Gerenciamento seguro de quais IPs monitorar através de um arquivo JSON externo, garantindo que dados sensíveis da sua rede não sejam expostos no código-fonte.
* Controles de Execução: Botões integrados na interface para iniciar e pausar o ciclo de monitoramento a qualquer momento.

## Pré-requisitos

Para executar o projeto, você precisará ter instalado em sua máquina:
* Python 3.8 ou superior.
* Reflex (Framework full-stack em Python).

## Como Instalar e Executar

1. Clone este repositório para o seu ambiente local:
   git clone https://github.com/gustavopmotta/echo/

2. Acesse a pasta do projeto:
   `cd echo`

3. Crie e ative um ambiente virtual (Recomendado):
   `python -m venv venv
   source venv/bin/activate` (Linux/Mac) ou `venv\Scripts\activate` (Windows)

4. Instale as dependências:
   pip install `requirements.txt`

5. Inicialize o servidor web:
   `reflex run`

6. Acesse o painel:
   Abra o seu navegador e acesse http://localhost:3000