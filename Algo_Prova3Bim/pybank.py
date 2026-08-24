import json
import os
from datetime import datetime

ARQUIVO_CONTA = "conta_completa.json"
ARQUIVO_LOG = "pybank.log"

def registrar_log(mensagem):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{agora}] {mensagem}"
    try:
        with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
    except OSError as erro:
        print(f"⚠ Não foi possível escrever no log: {erro}")

def existe_conta_salva():
    return os.path.exists(ARQUIVO_CONTA)


def abrir_conta():
    if not existe_conta_salva():
        return None
    try:
        with open(ARQUIVO_CONTA, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        registrar_log("Conta carregada do disco.")
        return dados
    except (json.JSONDecodeError, OSError) as erro:
        print(f"⚠ Não foi possível ler a conta guardada: {erro}")
        registrar_log(f"ERRO ao carregar conta: {erro}")
        return None


def gravar_conta(conta):
    try:
        with open(ARQUIVO_CONTA, "w", encoding="utf-8") as arquivo:
            json.dump(conta, arquivo, ensure_ascii=False, indent=4)
        registrar_log("Conta guardada em disco.")
        return True
    except OSError as erro:
        print(f"⚠ Falha ao gravar a conta: {erro}")
        registrar_log(f"ERRO ao guardar conta: {erro}")
        return False


def pedir_campo(mensagem, obrigatorio=True):
    valor = input(mensagem).strip()
    while obrigatorio and valor == "":
        valor = input(f"Este campo é obrigatório. {mensagem}").strip()
    return valor


def criar_conta_nova():
    print("\n--- ABERTURA DE NOVA CONTA ---")
    nome = pedir_campo("Nome completo: ")
    cpf = pedir_campo("CPF: ")
    email = pedir_campo("E-mail: ")
    endereco = pedir_campo("Endereço: ")
    agencia = pedir_campo("Agência: ")
    numero_conta = pedir_campo("Número da conta (ex: 4894354853): ")

    conta = {
        "titular": {
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "endereco": endereco,
        },
        "agencia": agencia,
        "conta": numero_conta,
        "saldo": 0.0,
        "historico": [],
    }
    registrar_log(f"Nova conta criada — titular: {nome}, agência: {agencia}, conta: {numero_conta}")
    return conta


def registrar_movimento(conta, tipo, valor):
    movimento = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo,
        "valor": valor,
        "agencia": conta["agencia"],
    }
    conta["historico"].append(movimento)


def fazer_deposito(conta, valor):
    if valor <= 0:
        print("⚠ Depósitos devem ser de valor positivo.")
        registrar_log(f"Tentativa de depósito inválido: R$ {valor:.2f}")
        return False
    conta["saldo"] += valor
    registrar_movimento(conta, "Depósito", valor)
    print(f"Depósito concluído. Novo saldo: R$ {conta['saldo']:.2f}")
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
    conta["saldo"] -= valor
    registrar_movimento(conta, "Levantamento", valor)
    print(f"Levantamento concluído. Novo saldo: R$ {conta['saldo']:.2f}")
    registrar_log(f"Levantamento de R$ {valor:.2f} na conta {conta['conta']}. Novo saldo: R$ {conta['saldo']:.2f}")
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
    print("=" * largura)


def mostrar_extrato(conta):
    largura = 60
    print("=" * largura)
    print(f"EXTRATO — {conta['titular']['nome']}  |  Ag: {conta['agencia']}  Conta: {conta['conta']}")
    print("=" * largura)

    movimentos = conta["historico"]
    if len(movimentos) == 0:
        print("(sem movimentações registadas)")
    else:
        print(f"{'Data':<20}{'Tipo':<15}{'Valor (R$)':<15}{'Agência'}")
        print("-" * largura)
        for movimento in movimentos:
            print(
                f"{movimento['data']:<20}"
                f"{movimento['tipo']:<15}"
                f"{movimento['valor']:<15.2f}"
                f"{movimento['agencia']}"
            )

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


def exibir_menu(conta):
    print(f"\nOlá, {conta['titular']['nome']} — saldo: R$ {conta['saldo']:.2f}")
    print("1) Depositar")
    print("2) Levantar")
    print("3) Ver extrato")
    print("4) Ver dados da conta")
    print("5) Ver log do sistema")
    print("6) Guardar e sair")


def executar_pybank():
    print("### PYBANK — Sistema Bancário de Terminal ###\n")
    registrar_log("--- Sessão iniciada ---")

    conta = abrir_conta()
    if conta is None:
        print("Nenhuma conta encontrada em disco.")
        conta = criar_conta_nova()
    else:
        print(f"Conta de {conta['titular']['nome']} carregada com sucesso.")

    ativo = True
    while ativo:
        exibir_menu(conta)
        escolha = input("Escolha uma opção: ").strip()

        if escolha == "1":
            valor = pedir_valor("Valor a depositar: R$ ")
            if valor is not None:
                fazer_deposito(conta, valor)

        elif escolha == "2":
            valor = pedir_valor("Valor a levantar: R$ ")
            if valor is not None:
                fazer_levantamento(conta, valor)

        elif escolha == "3":
            mostrar_extrato(conta)

        elif escolha == "4":
            mostrar_dados_titular(conta)

        elif escolha == "5":
            mostrar_log()

        elif escolha == "6":
            if gravar_conta(conta):
                print("Conta guardada. Até à próxima!")
            registrar_log("--- Sessão encerrada ---")
            ativo = False

        else:
            print("⚠ Opção inválida — escolha entre 1 e 6.")
            registrar_log(f"Opção de menu inválida digitada: '{escolha}'")


if __name__ == "__main__":
    executar_pybank()
