# SETUP — Rate Shopper Decolar (100% online: Supabase + GitHub + Lovable)

Nada roda no seu PC. O scraper roda no **GitHub Actions**, grava no **Supabase**, e o
**Lovable** mostra o painel. Fonte de preços: **Decolar** (tem as 3 categorias).

```
[GitHub Actions]  --escreve-->  [Supabase]  <--lê--  [Lovable: painel]
```

> Em teste: precisamos confirmar que a Decolar não bloqueia o IP do GitHub. O 1º "Run"
> responde isso. Se bloquear, partimos para proxy/API.

## FASE 1 — Supabase (banco)
1. supabase.com → New project (região São Paulo). Guarde a senha.
2. SQL Editor → cole `schema.sql` → Run. (Cria tabelas + seed dos 5 concorrentes.)
3. Project Settings → API → anote **Project URL** e **service_role**.

## FASE 2 — URLs da Decolar
4. Para cada concorrente, abra a página dele na **Decolar** com **uma data qualquer**
   (ex.: 10/10/2026), copie a URL da barra de endereço e cole na coluna `url` da tabela
   `hotels` (Table Editor). O scraper troca a data sozinho para cada dia da janela.
   - Importante: tem que ser a URL da **página do hotel** (onde aparecem os quartos),
     não a busca/listagem.

## FASE 3 — GitHub (scraper na nuvem)
5. Crie um repositório no GitHub e suba TODOS os arquivos (incl. a pasta `.github`).
   NÃO suba `.env`.
6. Settings → Secrets and variables → Actions → New repository secret. Crie dois:
   - `SUPABASE_URL` = a Project URL
   - `SUPABASE_SERVICE_ROLE_KEY` = a service_role
7. Aba **Actions** → workflow **rate-shopper-decolar** → **Run workflow**.
   - Dica: antes do 1º run, no Supabase deixe `app_settings.window_end` uns 2-3 dias
     após o início, para testar rápido. Depois volte para 2026-12-31.
8. Acompanhe o log (Actions → run → scrape → Capturar):
   - `ok ... (3/3)` = funcionou! Confira `price_observations` no Supabase.
   - muitos `ERR ... timeout/0/3` = a Decolar bloqueou o IP do GitHub → plano B (proxy/API).

## FASE 4 — Lovable (painel só leitura)
9. No Lovable, conecte o MESMO projeto Supabase (ícone de nuvem; se estiver no Lovable
   Cloud, peça no chat para conectar ao seu Supabase).
10. Peça o painel: seletor de categoria (mais barato / vista mar / suíte), grade dia-a-dia
    por hotel (do run mais recente), gráfico de evolução, em R$. Somente leitura.
11. Crie usuário: Supabase → Authentication → Add user (Auto Confirm). Para virar admin:
    ```
    insert into profiles (id, email, role)
    select id, email, 'admin' from auth.users where email = 'voce@exemplo.com'
    on conflict (id) do update set role = 'admin';
    ```

## Validar a leitura sem rede (opcional)
Se quiser conferir o parser com um HTML salvo da Decolar:
`python test_extract.py sample_Decolar2.txt` → deve listar os quartos e as 3 categorias.

## Se bloquear no GitHub
Opções: proxy residencial plugado no scraper, ou uma API de dados. Ambas pagas, mas
resolvem o IP. É só pedir que eu adapto o código.
