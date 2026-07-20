# ECHO

![https://www.python.org/](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![https://reflex.dev/](https://img.shields.io/badge/Reflex-6E56CF?style=flat-square&logo=reflex&logoColor=white)

## O que o Echo faz
- **Monitoramento em Tempo Real:** Dispara testes de ping simultâneos para verificar a conectividade e a latência de dispositivos na rede.

- **Dashboard Dinâmico:** Exibe um painel visual atualizado automaticamente, organizado por grupos, com gráficos de histórico que só carregam quando expandidos para economizar memória.

- **Alertas e Segurança:** Possui sistema de login seguro para administradores e dispara alertas automáticos por e-mail quando equipamentos críticos ficam offline.

## Como gerenciar os ativos
- **Pela Interface Web:** Adicione, edite ou remova equipamentos individualmente direto no painel, sem precisar mexer no código.

- **Importação em Massa (CSV):** Suba um arquivo .csv com a lista dos seus IPs, nomes, locais e grupos, e o sistema faz a validação e o cadastro de todos os equipamentos de uma só vez no banco de dados.

## Como rodar o webapp
Após clonar o repositório, instalar as dependências e criar as tabelas do banco de dados, execute:

```bash
pip install -r requirements.txt
reflex db migrate
reflex run --env prod
```

Feito isso, basta acessar http://localhost:3000 no seu navegador. Na primeira execução, o sistema guiará você automaticamente para a tela de setup para criar a conta de administrador e iniciar o monitoramento.