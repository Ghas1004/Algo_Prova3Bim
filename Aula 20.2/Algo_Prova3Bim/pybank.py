import json
import os
from datetime import datetime, timedelta

ARQUIVO_CONTAS = "contas.json"        
ARQUIVO_CONTA_ANTIGA = "conta_completa.json" 
ARQUIVO_LOG = "pybank.log"

FORMATO_DATA = "%Y-%m-%d %H:%M:%S"
DIAS_POR_PERIODO = 30
TAXA_JUROS = 0.005     
LIMITE_DIARIO_SAQUE = 2000.0  


def registrar_log(mensagem):
    agora = datetime.now().strftime(FORMATO_DATA)
    linha = f"[{agora}] {mensagem}"
    try:
        with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
    except OSError as erro:
        print(f"⚠ Não foi possível escrever no log: {erro}")


def carregar_contas():
    """Carrega o dicionário de contas (chave = número da conta) do disco."""
    if not os.path.exists(ARQUIVO_CONTAS):
        return {}
    try:
        with open(ARQUIVO_CONTAS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        registrar_log("Contas carregadas do disco.")
        return dados
    except (json.JSONDecodeError, OSError) as erro:
        print(f"⚠ Não foi possível ler o ficheiro de contas: {erro}")
        registrar_log(f"ERRO ao carregar contas: {erro}")
        return {}


def gravar_contas(contas):
    try:
        with open(ARQUIVO_CONTAS, "w", encoding="utf-8") as arquivo:
            json.dump(contas, arquivo, ensure_ascii=False, indent=4)
        registrar_log("Contas guardadas em disco.")
        return True
    except OSError as erro:
        print(f"⚠ Falha ao gravar as contas: {erro}")
        registrar_log(f"ERRO ao guardar contas: {erro}")
        return False


def migrar_conta_antiga(contas):
    """Se existir o ficheiro do formato antigo (uma única conta) e a conta ainda
    não tiver sido importada para o novo formato, faz a migração automaticamente."""
    if not os.path.exists(ARQUIVO_CONTA_ANTIGA):
        return
    try:
        with open(ARQUIVO_CONTA_ANTIGA, "r", encoding="utf-8") as arquivo:
            conta_antiga = json.load(arquivo)
    except (json.JSONDecodeError, OSError) as erro:
        registrar_log(f"ERRO ao tentar migrar conta antiga: {erro}")
        return

    numero = conta_antiga.get("conta")
    if numero and numero not in contas:
        contas[numero] = conta_antiga
        gravar_contas(contas)
        print(f"ℹ Conta antiga '{numero}' foi migrada automaticamente para o novo formato multi-conta.")
        registrar_log(f"Conta {numero} migrada do formato antigo ({ARQUIVO_CONTA_ANTIGA}).")


def pedir_campo(mensagem, obrigatorio=True):
    valor = input(mensagem).strip()
    while obrigatorio and valor == "":
        valor = input(f"Este campo é obrigatório. {mensagem}").strip()
    return valor


def pedir_senha_nova(mensagem):
    while True:
        senha = input(mensagem).strip()
        if senha.isdigit() and len(senha) == 4:
            return senha
        print("⚠ A senha deve conter exatamente 4 dígitos numéricos. Tente novamente.")


def criar_conta_nova(contas):
    print("\n--- ABERTURA DE NOVA CONTA ---")
    nome = pedir_campo("Nome completo: ")
    cpf = pedir_campo("CPF: ")
    email = pedir_campo("E-mail: ")
    endereco = pedir_campo("Endereço: ")
    agencia = pedir_campo("Agência: ")

    numero_conta = pedir_campo("Número da conta (ex: 4894354853): ")
    while numero_conta in contas:
        print("⚠ Já existe uma conta com esse número.")
        numero_conta = pedir_campo("Digite outro número de conta: ")

    password = pedir_senha_nova("Digite a sua senha contendo 4 dígitos (ex: 9858): ")

    conta = {
        "titular": {
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "endereco": endereco,
        },
        "agencia": agencia,
        "conta": numero_conta,
        "password": password,
        "saldo": 0.0,
        "historico": [],
        "data_ultimo_juros": datetime.now().strftime(FORMATO_DATA),
    }
    registrar_log(f"Nova conta criada — titular: {nome}, agência: {agencia}, conta: {numero_conta}")
    return conta


def registrar_movimento(conta, tipo, valor, detalhe=None):
    movimento = {
        "data": datetime.now().strftime(FORMATO_DATA),
        "tipo": tipo,
        "valor": valor,
        "agencia": conta["agencia"],
    }
    if detalhe:
        movimento["detalhe"] = detalhe
    conta["historico"].append(movimento)


def valor_movimentado_hoje(conta, tipos):
    """Soma o valor de todos os movimentos de hoje cujo tipo esteja em `tipos`."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    for movimento in conta["historico"]:
        if movimento["tipo"] in tipos and movimento["data"].startswith(hoje):
            total += movimento["valor"]
    return total


def fazer_deposito(conta, valor):
    if valor <= 0:
        print("⚠ Depósitos devem ser de valor positivo.")
        registrar_log(f"Tentativa de depósito inválido: R$ {valor:.2f}")
        return False
    conta["saldo"] += valor
    registrar_movimento(conta, "Depósito", valor)
    print(f"Depósito concluído. Guarde e salve a conta para ver o novo saldo de: R$ {conta['saldo']:.2f}")
    registrar_log(f"Depósito de R$ {valor:.2f} na conta {conta['conta']}. Novo saldo: R$ {conta['saldo']:.2f}")
    return True


def fazer_levantamento(conta, valor):
    if valor <= 0:
        print("⚠ Levantamentos devem ser de valor positivo.")
        registrar_log(f"Tentativa de levantamento inválido: R$ {valor:.2f}")
        return False
    if valor > conta["saldo"]:
        print(f"⚠ Saldo insuficiente (disponível: R$ {conta['saldo']:.2f}).")
        registrar_log(f"Levantamento recusado por saldo insuficiente: R$ {valor:.2f}")
        return False

    
    ja_movimentado_hoje = valor_movimentado_hoje(conta, ("Levantamento", "Transferência enviada"))
    if ja_movimentado_hoje + valor > LIMITE_DIARIO_SAQUE:
        disponivel_hoje = max(LIMITE_DIARIO_SAQUE - ja_movimentado_hoje, 0)
        print(f"⚠ Limite diário de saque excedido (limite: R$ {LIMITE_DIARIO_SAQUE:.2f}).")
        print(f"   Já movimentado hoje: R$ {ja_movimentado_hoje:.2f} — disponível: R$ {disponivel_hoje:.2f}.")
        registrar_log(
            f"Levantamento recusado por limite diário — conta {conta['conta']}: "
            f"tentativa R$ {valor:.2f}, já movimentado hoje R$ {ja_movimentado_hoje:.2f}."
        )
        return False

    conta["saldo"] -= valor
    registrar_movimento(conta, "Levantamento", valor)
    print(f"Levantamento concluído. Novo saldo: R$ {conta['saldo']:.2f}")
    registrar_log(f"Levantamento de R$ {valor:.2f} na conta {conta['conta']}. Novo saldo: R$ {conta['saldo']:.2f}")
    return True


def transferir(contas, conta_origem):
    print("\n--- TRANSFERÊNCIA ENTRE CONTAS ---")
    numero_destino = pedir_campo("Número da conta de destino: ")

    if numero_destino == conta_origem["conta"]:
        print("⚠ Não é possível transferir para a própria conta.")
        return False

    if numero_destino not in contas:
        print("⚠ Conta de destino não encontrada.")
        registrar_log(
            f"Transferência falhou: conta destino '{numero_destino}' não encontrada "
            f"(origem {conta_origem['conta']})."
        )
        return False

    conta_destino = contas[numero_destino]

    valor = pedir_valor("Valor a transferir: R$ ")
    if valor is None:
        return False
    if valor <= 0:
        print("⚠ O valor deve ser positivo.")
        return False
    if valor > conta_origem["saldo"]:
        print(f"⚠ Saldo insuficiente (disponível: R$ {conta_origem['saldo']:.2f}).")
        return False

    
    ja_movimentado_hoje = valor_movimentado_hoje(conta_origem, ("Levantamento", "Transferência enviada"))
    if ja_movimentado_hoje + valor > LIMITE_DIARIO_SAQUE:
        disponivel_hoje = max(LIMITE_DIARIO_SAQUE - ja_movimentado_hoje, 0)
        print(f"⚠ Limite diário de saídas excedido (limite: R$ {LIMITE_DIARIO_SAQUE:.2f}).")
        print(f"   Já movimentado hoje: R$ {ja_movimentado_hoje:.2f} — disponível: R$ {disponivel_hoje:.2f}.")
        registrar_log(
            f"Transferência recusada por limite diário — conta {conta_origem['conta']}: "
            f"tentativa R$ {valor:.2f}, já movimentado hoje R$ {ja_movimentado_hoje:.2f}."
        )
        return False

    conta_origem["saldo"] -= valor
    conta_destino["saldo"] += valor

    registrar_movimento(conta_origem, "Transferência enviada", valor, detalhe=f"para conta {numero_destino}")
    registrar_movimento(conta_destino, "Transferência recebida", valor, detalhe=f"de conta {conta_origem['conta']}")

    print(f"✔ Transferência de R$ {valor:.2f} para {conta_destino['titular']['nome']} (conta {numero_destino}) concluída.")
    registrar_log(
        f"Transferência de R$ {valor:.2f}: conta {conta_origem['conta']} -> conta {numero_destino}."
    )
    gravar_contas(contas)
    return True


def aplicar_juros(conta):
    if "data_ultimo_juros" not in conta:
        conta["data_ultimo_juros"] = datetime.now().strftime(FORMATO_DATA)
        return False

    try:
        data_ultimo = datetime.strptime(conta["data_ultimo_juros"], FORMATO_DATA)
    except ValueError:
        conta["data_ultimo_juros"] = datetime.now().strftime(FORMATO_DATA)
        return False

    dias_passados = (datetime.now() - data_ultimo).days
    periodos = dias_passados // DIAS_POR_PERIODO

    if periodos <= 0:
        return False

    saldo_antes = conta["saldo"]
    for _ in range(periodos):
        juros = conta["saldo"] * TAXA_JUROS
        conta["saldo"] += juros
        registrar_movimento(conta, "Juros (0,5%)", juros)

    conta["data_ultimo_juros"] = (data_ultimo + timedelta(days=periodos * DIAS_POR_PERIODO)).strftime(FORMATO_DATA)

    print(f"💰 Rendimento aplicado: {periodos} período(s) de 30 dias (0,5% ao mês).")
    print(f"   Saldo: R$ {saldo_antes:.2f} → R$ {conta['saldo']:.2f}")
    registrar_log(
        f"Juros aplicados na conta {conta['conta']}: {periodos} período(s), "
        f"saldo {saldo_antes:.2f} -> {conta['saldo']:.2f}"
    )
    return True


def mostrar_dados_titular(conta):
    titular = conta["titular"]
    largura = 44
    print("=" * largura)
    print("DADOS DA CONTA")
    print("=" * largura)
    print(f"Nome:      {titular['nome']}")
    print(f"CPF:       {titular['cpf']}")
    print(f"E-mail:    {titular['email']}")
    print(f"Endereço:  {titular['endereco']}")
    print(f"Agência:   {conta['agencia']}")
    print(f"Conta:     {conta['conta']}")
    print(f"Senha:     ****")
    print("=" * largura)


def trocar_senha(contas, conta):
    print("\n--- TROCAR SENHA ---")
    senha_atual = pedir_campo("Digite a senha atual: ")

    if senha_atual != conta["password"]:
        print("⚠ Senha atual incorreta. Operação cancelada.")
        registrar_log(f"Tentativa de troca de senha falhou (senha atual incorreta) — conta {conta['conta']}.")
        return False

    nova_senha = pedir_senha_nova("Digite a nova senha (4 dígitos): ")
    confirmar_senha = pedir_campo("Confirme a nova senha: ")

    if nova_senha != confirmar_senha:
        print("⚠ As senhas não coincidem. Operação cancelada.")
        registrar_log(f"Tentativa de troca de senha falhou (confirmação não coincide) — conta {conta['conta']}.")
        return False

    if nova_senha == senha_atual:
        print("⚠ A nova senha deve ser diferente da atual.")
        registrar_log(f"Tentativa de troca de senha falhou (nova senha igual à atual) — conta {conta['conta']}.")
        return False

    conta["password"] = nova_senha
    if gravar_contas(contas):
        print("✔ Senha alterada e guardada com sucesso!")
        registrar_log(f"Senha alterada com sucesso — conta {conta['conta']}.")
        return True
    else:
        print("⚠ A senha foi alterada em memória, mas houve um erro ao guardar no ficheiro.")
        return False


def mostrar_extrato(conta):
    largura = 60
    print("=" * largura)
    print(f"EXTRATO — {conta['titular']['nome']}  |  Ag: {conta['agencia']}  Conta: {conta['conta']}")
    print("=" * largura)

    movimentos = conta["historico"]
    if len(movimentos) == 0:
        print("(sem movimentações registadas)")
    else:
        print(f"{'Data':<20}{'Tipo':<22}{'Valor (R$)':<15}{'Agência'}")
        print("-" * largura)
        for movimento in movimentos:
            print(
                f"{movimento['data']:<20}"
                f"{movimento['tipo']:<22}"
                f"{movimento['valor']:<15.2f}"
                f"{movimento['agencia']}"
            )
            if movimento.get("detalhe"):
                print(f"    ↳ {movimento['detalhe']}")

    print("-" * largura)
    print(f"Saldo atual: R$ {conta['saldo']:.2f}")
    print("=" * largura)


def mostrar_log():
    if not os.path.exists(ARQUIVO_LOG):
        print("(nenhum log registado ainda)")
        return
    print("\n--- LOG DE ALTERAÇÕES DO SISTEMA ---")
    with open(ARQUIVO_LOG, "r", encoding="utf-8") as arquivo:
        conteudo = arquivo.read()
    print(conteudo if conteudo.strip() else "(log vazio)")


def pedir_valor(mensagem):
    entrada = input(mensagem)
    try:
        return float(entrada)
    except ValueError:
        print("⚠ Isso não é um número válido.")
        return None


def fazer_login(conta):
    tentativas = 0
    while True:
        print(f"\n--- LOGIN — conta {conta['conta']} ({conta['titular']['nome']}) ---")
        senha_digitada = input("Senha: ").strip()
        if senha_digitada == conta["password"]:
            registrar_log(f"Login bem-sucedido — conta {conta['conta']}.")
            return True
        tentativas += 1
        print("⚠ Senha incorreta. Tente novamente.")
        registrar_log(f"Tentativa de login com senha incorreta (tentativa {tentativas}) — conta {conta['conta']}.")


def selecionar_conta(contas):
    print("\n--- ALTERNÂNCIA DE CONTAS ---")
    if contas:
        print("Contas disponíveis:")
        for numero, c in contas.items():
            print(f"  {numero} — {c['titular']['nome']}")
    else:
        print("  (nenhuma conta cadastrada ainda)")

    escolha = pedir_campo("Número da conta para entrar, ou 'N' para criar uma nova: ")

    if escolha.upper() == "N":
        nova = criar_conta_nova(contas)
        contas[nova["conta"]] = nova
        gravar_contas(contas)
        return nova

    if escolha not in contas:
        print("⚠ Conta não encontrada.")
        return None

    return contas[escolha]


def exibir_menu(conta):
    print(f"\nOlá, {conta['titular']['nome']} — conta {conta['conta']} — saldo: R$ {conta['saldo']:.2f} --- HOUVE UM ACRÉSCIMO DE 0.05% DE JUROS COMPOSTOS EM TODAS AS CONTAS EXISTENTES")
    print("2) Depositar")
    print("3) Levantar")
    print("4) Ver extrato")
    print("5) Ver dados da conta")
    print("6) Ver log do sistema")
    print("7) Trocar senha")
    print("8) Guardar e sair")
    print("9) Transferir para outra conta")
    print("0) Trocar de conta")


def executar_pybank():
    print("### PYBANK — Sistema Bancário de Terminal ###\n")
    registrar_log("--- Sessão iniciada ---")

    contas = carregar_contas()
    migrar_conta_antiga(contas)

    programa_ativo = True
    while programa_ativo:
        
        conta = None
        while conta is None:
            conta = selecionar_conta(contas)

        if aplicar_juros(conta):
            gravar_contas(contas)

        fazer_login(conta)

        sessao_ativa = True
        while sessao_ativa:
            exibir_menu(conta)
            escolha = input("Escolha uma opção: ").strip()

            if escolha == "2":
                valor = pedir_valor("Valor a depositar: R$ ")
                if valor is not None:
                    fazer_deposito(conta, valor)

            elif escolha == "3":
                valor = pedir_valor("Valor a levantar: R$ ")
                if valor is not None:
                    fazer_levantamento(conta, valor)

            elif escolha == "4":
                mostrar_extrato(conta)

            elif escolha == "5":
                mostrar_dados_titular(conta)

            elif escolha == "6":
                mostrar_log()

            elif escolha == "7":
                trocar_senha(contas, conta)

            elif escolha == "8":
                if gravar_contas(contas):
                    print("Contas guardadas. Até à próxima!")
                registrar_log("--- Sessão encerrada ---")
                sessao_ativa = False
                programa_ativo = False

            elif escolha == "9":
                transferir(contas, conta)

            elif escolha == "0":
                gravar_contas(contas)
                print("Voltando à seleção de contas...")
                registrar_log(f"Logout da conta {conta['conta']} — alternância de conta.")
                sessao_ativa = False

            else:
                print("⚠ Opção inválida.")
                registrar_log(f"Opção de menu inválida digitada: '{escolha}'")


if __name__ == "__main__":
    executar_pybank()