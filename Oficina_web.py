import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Navatork - Gestão", page_icon="⚙️", layout="wide")
DB_PATH = "oficina_web.db"

def inicializar_banco():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # Tabelas originais
    cur.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, veiculo TEXT, placa TEXT, telefone TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS os (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, cliente_id INTEGER, servico_id INTEGER, status TEXT, valor REAL)''')
    
    # Novas tabelas: Estoque e Despesas
    cur.execute('''CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, quantidade INTEGER, valor_custo REAL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descricao TEXT, valor REAL)''')
    
    cur.execute("SELECT COUNT(*) FROM servicos")
    if cur.fetchone()[0] == 0:
        servs = [("Revisão da Caixa de Direção", 350.0), ("Troca de Amortecedores (Par)", 180.0), ("Alinhamento e Balanceamento", 120.0), ("Manutenção na Coluna de Direção", 250.0)]
        cur.executemany("INSERT INTO servicos (descricao, valor) VALUES (?, ?)", servs)
    con.commit()
    con.close()

def run_query(query, parameters=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(query, parameters)
    con.commit()
    con.close()

def get_data(query, parameters=()):
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, con, params=parameters)
    con.close()
    return df

inicializar_banco()

# ==========================================
# FUNÇÃO: GERAR PDF DA OS
# ==========================================
def gerar_pdf_os(os_id):
    query = '''
        SELECT os.id, os.data, c.nome, c.veiculo, c.placa, c.telefone, s.descricao, os.valor, os.status 
        FROM os JOIN clientes c ON os.cliente_id = c.id JOIN servicos s ON os.servico_id = s.id
        WHERE os.id = ?
    '''
    df_os = get_data(query, (os_id,))
    if df_os.empty: return None
    
    dados = df_os.iloc[0]
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4
    
    # Cabeçalho
    c.setFillColor(HexColor("#1E1E1E"))
    c.rect(0, altura - 80, largura, 80, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, altura - 45, "NAVATORK AUTO - ORDEM DE SERVIÇO")
    c.setFont("Helvetica", 12)
    c.drawString(40, altura - 65, "Especializada em Suspensão e Direção")
    
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, altura - 120, f"OS Nº: {dados['id']:04d}  |  Data: {datetime.strptime(dados['data'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
    
    # Dados do Cliente
    c.setFont("Helvetica-Bold", 12); c.drawString(40, altura - 160, "DADOS DO CLIENTE / VEÍCULO:")
    c.line(40, altura - 165, largura - 40, altura - 165)
    c.setFont("Helvetica", 11)
    c.drawString(40, altura - 185, f"Cliente: {dados['nome']}")
    c.drawString(350, altura - 185, f"Telefone: {dados['telefone']}")
    c.drawString(40, altura - 205, f"Veículo: {dados['veiculo']}")
    c.drawString(350, altura - 205, f"Placa: {dados['placa']}")
    
    # Dados do Serviço
    c.setFont("Helvetica-Bold", 12); c.drawString(40, altura - 250, "DESCRIÇÃO DO SERVIÇO:")
    c.line(40, altura - 255, largura - 40, altura - 255)
    c.setFont("Helvetica", 11)
    c.drawString(40, altura - 275, f"Serviço Realizado: {dados['descricao']}")
    c.drawString(40, altura - 295, f"Status Atual: {dados['status']}")
    
    # Valores
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, altura - 340, f"VALOR TOTAL: R$ {dados['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Rodapé / Assinatura
    c.setFont("Helvetica", 10)
    c.drawCentredString(largura / 2, 100, "___________________________________________________")
    c.drawCentredString(largura / 2, 85, "Assinatura do Cliente")
    c.drawCentredString(largura / 2, 40, "Navatork Auto - Garantia de Qualidade e Segurança")
    
    c.save()
    buffer.seek(0)
    return buffer

# ==========================================
# MENU LATERAL (SIDEBAR)
# ==========================================
st.sidebar.title("⚙️ Navatork Auto")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegação", [
    "📊 Dashboard", 
    "📝 Ordens de Serviço", 
    "📦 Controle de Estoque", 
    "💰 Financeiro", 
    "👥 Clientes & Veículos", 
    "🔧 Tabela de Serviços"
])

# ==========================================
# TELA 1: DASHBOARD
# ==========================================
if menu == "📊 Dashboard":
    st.title("📊 Painel de Controle")
    
    df_os = get_data("SELECT status, valor FROM os")
    faturamento_total = df_os[df_os['status'] == 'Concluído']['valor'].sum() if not df_os.empty else 0
    os_pendentes = len(df_os[df_os['status'] != 'Concluído']) if not df_os.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("OS Concluídas", len(df_os[df_os['status'] == 'Concluído']) if not df_os.empty else 0)
    col2.metric("Faturamento (Concluídas)", f"R$ {faturamento_total:,.2f}")
    col3.metric("Veículos na Oficina", os_pendentes)
    
    st.markdown("---")
    st.subheader("Últimas Ordens de Serviço")
    query_ultimas = '''SELECT os.id as OS, os.data as Data, c.nome as Cliente, c.veiculo as Veículo, 
                       s.descricao as Serviço, os.status as Status, os.valor as Valor 
                       FROM os JOIN clientes c ON os.cliente_id = c.id JOIN servicos s ON os.servico_id = s.id
                       ORDER BY os.id DESC LIMIT 10'''
    st.dataframe(get_data(query_ultimas), use_container_width=True, hide_index=True)

# ==========================================
# TELA 2: ORDENS DE SERVIÇO & PDF
# ==========================================
elif menu == "📝 Ordens de Serviço":
    st.title("📝 Gerenciar Ordens de Serviço")
    
    with st.expander("➕ Abrir Nova OS", expanded=False):
        df_clientes = get_data("SELECT id, nome, veiculo, placa FROM clientes")
        df_servicos = get_data("SELECT id, descricao, valor FROM servicos")
        
        if df_clientes.empty or df_servicos.empty:
            st.warning("Cadastre clientes e serviços primeiro!")
        else:
            with st.form("form_nova_os"):
                lista_clientes = df_clientes.apply(lambda x: f"{x['id']} - {x['nome']} ({x['placa']})", axis=1).tolist()
                lista_servicos = df_servicos.apply(lambda x: f"{x['id']} - {x['descricao']}", axis=1).tolist()
                
                cliente_sel = st.selectbox("Selecione o Cliente", lista_clientes)
                servico_sel = st.selectbox("Selecione o Serviço Padrão", lista_servicos)
                
                col1, col2 = st.columns(2)
                data_os = col1.date_input("Data de Entrada")
                status_os = col2.selectbox("Status", ["Pendente", "Em Andamento", "Aguardando Peça", "Concluído"])
                valor_final = st.number_input("Valor Final (R$)", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("Salvar Ordem de Serviço", type="primary"):
                    c_id = int(cliente_sel.split(" - ")[0]); s_id = int(servico_sel.split(" - ")[0])
                    run_query("INSERT INTO os (data, cliente_id, servico_id, status, valor) VALUES (?, ?, ?, ?, ?)", 
                              (data_os.strftime("%Y-%m-%d"), c_id, s_id, status_os, valor_final))
                    st.success("OS salva com sucesso!")
                    st.rerun()

    st.markdown("### 🖨️ Gerar OS em PDF (WhatsApp)")
    df_todas_os = get_data('''SELECT os.id, c.nome, c.veiculo FROM os JOIN clientes c ON os.cliente_id = c.id ORDER BY os.id DESC''')
    if not df_todas_os.empty:
        colA, colB = st.columns([3, 1])
        lista_os_pdf = df_todas_os.apply(lambda x: f"OS {x['id']:04d} - {x['nome']} ({x['veiculo']})", axis=1).tolist()
        os_selecionada = colA.selectbox("Selecione a OS para gerar o recibo/documento", lista_os_pdf)
        
        if os_selecionada:
            id_selecionado = int(os_selecionada.split(" ")[1])
            pdf_bytes = gerar_pdf_os(id_selecionado)
            if pdf_bytes:
                colB.markdown("<br>", unsafe_allow_html=True) # Espaçamento
                colB.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name=f"OS_{id_selecionado:04d}_Navatork.pdf", mime="application/pdf", type="primary")

    st.markdown("---")
    st.markdown("### 📋 Histórico de OS")
    st.dataframe(get_data('''SELECT os.id as OS, os.data as Data, c.nome as Cliente, c.placa as Placa, s.descricao as Serviço, os.status as Status, os.valor as Valor FROM os JOIN clientes c ON os.cliente_id = c.id JOIN servicos s ON os.servico_id = s.id ORDER BY os.id DESC'''), use_container_width=True, hide_index=True)

# ==========================================
# TELA 3: ESTOQUE DE PEÇAS
# ==========================================
elif menu == "📦 Controle de Estoque":
    st.title("📦 Controle de Estoque")
    
    with st.form("form_estoque"):
        st.subheader("Dar Entrada em Peças")
        col1, col2, col3 = st.columns([2, 1, 1])
        peca = col1.text_input("Nome da Peça (Ex: Amortecedor Dianteiro Gol)")
        qtd = col2.number_input("Quantidade", min_value=1, step=1)
        custo = col3.number_input("Custo Unitário (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Adicionar ao Estoque", type="primary"):
            if peca:
                # Verifica se a peça já existe para somar, ou cria nova
                df_existe = get_data("SELECT id, quantidade FROM estoque WHERE peca = ?", (peca.upper(),))
                if not df_existe.empty:
                    nova_qtd = int(df_existe.iloc[0]['quantidade']) + qtd
                    run_query("UPDATE estoque SET quantidade = ?, valor_custo = ? WHERE id = ?", (nova_qtd, custo, int(df_existe.iloc[0]['id'])))
                else:
                    run_query("INSERT INTO estoque (peca, quantidade, valor_custo) VALUES (?, ?, ?)", (peca.upper(), qtd, custo))
                st.success("Estoque atualizado com sucesso!")
                st.rerun()
            else:
                st.error("Digite o nome da peça.")
                
    st.markdown("---")
    st.subheader("📦 Inventário Atual")
    df_estoque = get_data("SELECT id as Código, peca as Peça, quantidade as Qtd_Atual, valor_custo as Custo_Unitário FROM estoque ORDER BY peca")
    
    if not df_estoque.empty:
        # Pinta de vermelho se a quantidade for menor que 3 (Estoque Baixo)
        st.dataframe(df_estoque.style.apply(lambda x: ['background-color: #ffcccc' if x['Qtd_Atual'] <= 2 else '' for i in x], axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("O estoque está vazio no momento.")

# ==========================================
# TELA 4: FINANCEIRO AVANÇADO
# ==========================================
elif menu == "💰 Financeiro":
    st.title("💰 Controle Financeiro")
    
    # Calcular Totais
    df_receitas = get_data("SELECT valor FROM os WHERE status = 'Concluído'")
    df_despesas = get_data("SELECT valor FROM despesas")
    
    receita_total = df_receitas['valor'].sum() if not df_receitas.empty else 0.0
    despesa_total = df_despesas['valor'].sum() if not df_despesas.empty else 0.0
    lucro = receita_total - despesa_total
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Entradas (OS Concluídas)", f"R$ {receita_total:,.2f}")
    col2.metric("🔴 Saídas (Despesas)", f"R$ {despesa_total:,.2f}")
    col3.metric("🔵 Saldo / Lucro Real", f"R$ {lucro:,.2f}")
    
    st.markdown("---")
    
    with st.expander("💸 Lançar Nova Despesa (Água, Luz, Compra de Peças, etc.)", expanded=False):
        with st.form("form_despesa"):
            colA, colB, colC = st.columns([1, 2, 1])
            data_desp = colA.date_input("Data da Despesa")
            desc_desp = colB.text_input("Descrição (Ex: Conta de Luz)")
            valor_desp = colC.number_input("Valor (R$)", min_value=0.01, format="%.2f")
            
            if st.form_submit_button("Lançar Despesa", type="primary"):
                if desc_desp:
                    run_query("INSERT INTO despesas (data, descricao, valor) VALUES (?, ?, ?)", (data_desp.strftime("%Y-%m-%d"), desc_desp, valor_desp))
                    st.success("Despesa registrada!")
                    st.rerun()
                else:
                    st.error("Preencha a descrição.")
                    
    st.subheader("Histórico de Despesas")
    df_historico_desp = get_data("SELECT data as Data, descricao as Descrição, valor as Valor FROM despesas ORDER BY id DESC")
    st.dataframe(df_historico_desp, use_container_width=True, hide_index=True)

# ==========================================
# TELAS 5 e 6: CLIENTES E SERVIÇOS (Inalterados)
# ==========================================
elif menu == "👥 Clientes & Veículos":
    st.title("👥 Cadastro de Clientes")
    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Cliente")
        telefone = col2.text_input("Telefone (WhatsApp)")
        col3, col4 = st.columns(2)
        veiculo = col3.text_input("Modelo do Veículo (ex: Gol 1.6)")
        placa = col4.text_input("Placa (ex: ABC-1234)")
        if st.form_submit_button("Cadastrar Cliente", type="primary"):
            if nome and veiculo and placa:
                run_query("INSERT INTO clientes (nome, veiculo, placa, telefone) VALUES (?, ?, ?, ?)", (nome, veiculo, placa.upper(), telefone))
                st.success("Cliente cadastrado!"); st.rerun()
            else: st.error("Preencha Nome, Veículo e Placa.")
    st.markdown("---")
    st.dataframe(get_data("SELECT id as ID, nome as Nome, telefone as Contato, veiculo as Veículo, placa as Placa FROM clientes"), use_container_width=True, hide_index=True)

elif menu == "🔧 Tabela de Serviços":
    st.title("🔧 Tabela de Mão de Obra e Serviços")
    with st.form("form_servico"):
        col1, col2 = st.columns([3, 1])
        desc = col1.text_input("Descrição do Serviço")
        val = col2.number_input("Valor Padrão (R$)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Adicionar Serviço", type="primary"):
            if desc:
                run_query("INSERT INTO servicos (descricao, valor) VALUES (?, ?)", (desc, val))
                st.success("Serviço adicionado!"); st.rerun()
            else: st.error("Preencha a descrição.")
    st.markdown("---")
    st.dataframe(get_data("SELECT id as Código, descricao as Serviço, valor as Valor_Base FROM servicos"), use_container_width=True, hide_index=True)