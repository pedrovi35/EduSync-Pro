import streamlit as st
import os
import time
import ollama
from datetime import date, datetime
from streamlit_calendar import calendar
import psycopg2
import bcrypt

# --- 1. CONFIGURAÇÕES GERAIS E ESTILO ---
st.set_page_config(page_title="EduSync Pro", page_icon="🚀", layout="wide")


def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #0f1116; }
        .card { background-color: #1c1f2b; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); border: 1px solid #2a2f45; }
        div[data-testid="stMetric"] { background-color: #2a2f45; border-radius: 8px; padding: 15px; text-align: center; }
        div[data-testid="stMetric"] > div:nth-child(2) > div { font-size: 2.5rem; }
    </style>
    """, unsafe_allow_html=True)


# --- 2. LÓGICA DE GAMIFICAÇÃO ---
XP_PER_LEVEL = [100, 250, 500, 1000, 2000]
LEVEL_NAMES = ["Noviço do Saber", "Aprendiz Focado", "Estudante Mestre", "Sábio Produtivo", "Lenda do Conhecimento"]


# --- 3. FUNÇÕES DE BANCO DE DADOS E SERVIÇOS ---

@st.cache_resource
def get_db_connection():
    try:
        conn = psycopg2.connect(**st.secrets["database"])
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        st.stop()


def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
              id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL,
              xp INT DEFAULT 0, nivel INT DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
              id SERIAL PRIMARY KEY, id_usuario INT REFERENCES usuarios(id) ON DELETE CASCADE,
              conteudo TEXT NOT NULL, status TEXT NOT NULL, data_criacao TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
              id SERIAL PRIMARY KEY, id_usuario INT REFERENCES usuarios(id) ON DELETE CASCADE,
              frente TEXT NOT NULL, verso TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()


def hash_password(password): return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, hashed): return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def login(email, password):
    conn = get_db_connection()
    user_info = None
    with conn.cursor() as cur:
        cur.execute("SELECT id, nome, senha FROM usuarios WHERE email = %s", (email,))
        result = cur.fetchone()
        if result and check_password(password, result[2]):
            user_info = {"id": result[0], "name": result[1], "email": email}
    return user_info


def logout():
    for key in list(st.session_state.keys()):
        if key != 'page': del st.session_state[key]
    st.session_state.logged_in = False
    st.rerun()


def load_user_data():
    user_id = st.session_state.user_id
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT xp, nivel FROM usuarios WHERE id = %s", (user_id,))
        st.session_state.user_xp, st.session_state.user_level = cur.fetchone()

        cur.execute("SELECT id, conteudo, status FROM tarefas WHERE id_usuario = %s ORDER BY data_criacao DESC",
                    (user_id,))
        st.session_state.tasks = [{'id': r[0], 'content': r[1], 'status': r[2]} for r in cur.fetchall()]

        cur.execute("SELECT id, frente, verso FROM flashcards WHERE id_usuario = %s ORDER BY created_at DESC",
                    (user_id,))
        st.session_state.flashcards = [{'id': r[0], 'frente': r[1], 'verso': r[2]} for r in cur.fetchall()]


# --- Funções CRUD (Create, Read, Update, Delete) ---

def db_add_task(content):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO tarefas (id_usuario, conteudo, status) VALUES (%s, %s, %s)",
                    (st.session_state.user_id, content, 'A Fazer'))
        conn.commit()


def db_update_task_status(task_id, new_status):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE tarefas SET status = %s WHERE id = %s AND id_usuario = %s",
                    (new_status, task_id, st.session_state.user_id))
        conn.commit()


def db_delete_task(task_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tarefas WHERE id = %s AND id_usuario = %s", (task_id, st.session_state.user_id))
        conn.commit()


def db_add_flashcard(frente, verso):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO flashcards (id_usuario, frente, verso) VALUES (%s, %s, %s)",
                    (st.session_state.user_id, frente, verso))
        conn.commit()


def db_delete_flashcard(card_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM flashcards WHERE id = %s AND id_usuario = %s", (card_id, st.session_state.user_id))
        conn.commit()


def db_update_gamification():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE usuarios SET xp = %s, nivel = %s WHERE id = %s",
                    (st.session_state.user_xp, st.session_state.user_level, st.session_state.user_id))
        conn.commit()


# --- 4. FUNÇÕES DE CADA PÁGINA ---

def show_dashboard():
    # ... (código do dashboard, sem alterações) ...
    st.title(f"🚀 Hub de Estudos, {st.session_state.user_name}!")

    tasks_by_status = {'A Fazer': [], 'Fazendo': [], 'Feito': []}
    for task in st.session_state.get('tasks', []):
        tasks_by_status[task['status']].append(task)

    col1, col2, col3 = st.columns(3)
    col1.metric("🔵 A Fazer", len(tasks_by_status['A Fazer']))
    col2.metric("🟡 Fazendo", len(tasks_by_status['Fazendo']))
    col3.metric("🟢 Feito", len(tasks_by_status['Feito']))

    with st.form("quick_add_task_form", clear_on_submit=True):
        new_task = st.text_input("Qual a sua próxima tarefa?", placeholder="Ex: Estudar sobre SQL Injection")
        if st.form_submit_button("Adicionar Tarefa", type="primary", use_container_width=True):
            if new_task:
                db_add_task(new_task)
                st.toast(f"Tarefa '{new_task}' adicionada!", icon="✅")
                st.rerun()


def show_tarefas():
    # ... (código das tarefas, sem alterações) ...
    st.title("🗂️ Gerenciador de Tarefas Kanban")

    tasks_by_status = {'A Fazer': [], 'Fazendo': [], 'Feito': []}
    for task in st.session_state.get('tasks', []):
        tasks_by_status[task['status']].append(task)

    list_names = ['A Fazer', 'Fazendo', 'Feito']
    cols = st.columns(len(list_names))

    for i, list_name in enumerate(list_names):
        with cols[i]:
            st.markdown(f'<div class="card" style="min-height: 400px;"><h4>{list_name}</h4><hr>',
                        unsafe_allow_html=True)
            for task in tasks_by_status[list_name]:
                st.markdown(f"**{task['content']}**")

                c1, c2 = st.columns(2)
                new_status = c1.selectbox("Mover para:", list_names, index=i, key=f"select_{task['id']}",
                                          label_visibility="collapsed")

                if c2.button("🗑️", key=f"del_{task['id']}", help="Excluir tarefa"):
                    db_delete_task(task['id'])
                    st.toast("Tarefa excluída!", icon="♻️")
                    st.rerun()

                if new_status != list_name:
                    db_update_task_status(task['id'], new_status)
                    if new_status == 'Feito':
                        st.session_state.user_xp += 10
                        st.toast("+10 XP! ✨")
                        db_update_gamification()
                    st.rerun()
                st.markdown("---")
            st.markdown('</div>', unsafe_allow_html=True)


def show_ferramentas():
    st.title("🛠️ Ferramentas de Estudo")
    tab1, tab2, tab3 = st.tabs(["🍅 Cronômetro Pomodoro", "🗂️ Flashcards", "📝 Anotações"])

    with tab1:
        st.subheader("Técnica Pomodoro")
        # (A lógica do pomodoro continua temporária, pois não a salvamos no DB)
        # ... (código do Pomodoro omitido para brevidade, mas pode ser colado aqui) ...

    with tab2:
        st.subheader("Meus Flashcards")

        with st.expander("➕ Adicionar Novo Cartão"):
            with st.form("new_card_form", clear_on_submit=True):
                front = st.text_input("Frente do cartão")
                back = st.text_area("Verso do cartão")
                if st.form_submit_button("Adicionar Cartão"):
                    if front and back:
                        db_add_flashcard(front, back)
                        st.toast("Flashcard adicionado com sucesso!", icon="✨")
                        st.rerun()
                    else:
                        st.warning("Preencha a frente и o verso do cartão.")

        if not st.session_state.flashcards:
            st.info("Você ainda não tem flashcards. Crie um acima!")
        else:
            if 'flashcard_idx' not in st.session_state or st.session_state.flashcard_idx >= len(
                    st.session_state.flashcards):
                st.session_state.flashcard_idx = 0
            if 'flipped' not in st.session_state:
                st.session_state.flipped = False

            total = len(st.session_state.flashcards)
            st.write(f"Cartão {st.session_state.flashcard_idx + 1} de {total}")

            card = st.session_state.flashcards[st.session_state.flashcard_idx]

            card_content = card['verso'] if st.session_state.flipped else card['frente']
            st.markdown(f"""
                <div class='card' style='text-align: center; min-height: 200px; display: flex; justify-content: center; align-items: center; font-size: 1.5rem;'>
                    <p>{card_content}</p>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            if c1.button("⬅️ Anterior", use_container_width=True):
                st.session_state.flashcard_idx = (st.session_state.flashcard_idx - 1) % total
                st.session_state.flipped = False
                st.rerun()
            if c2.button("↩️ Virar Cartão", use_container_width=True, type="primary"):
                st.session_state.flipped = not st.session_state.flipped
                st.rerun()
            if c3.button("Próximo ➡️", use_container_width=True):
                st.session_state.flashcard_idx = (st.session_state.flashcard_idx + 1) % total
                st.session_state.flipped = False
                st.rerun()
            if c4.button("🗑️", use_container_width=True, help="Excluir este cartão"):
                db_delete_flashcard(card['id'])
                st.toast("Cartão excluído!")
                st.session_state.flashcard_idx = 0
                st.rerun()

    with tab3:
        st.subheader("Anotações Rápidas")
        # (Anotações também são temporárias. Precisariam de uma tabela `notas` no DB)
        st.session_state.notes = st.text_area("Suas Anotações", value=st.session_state.get('notes', ""), height=300,
                                              label_visibility="collapsed")


# --- 5. LÓGICA PRINCIPAL DO APP ---
inject_custom_css()
init_db()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("`🚀 EduSync Pro`")
    st.subheader("Sua plataforma de estudos inteligente e integrada.")

    login_tab, signup_tab = st.tabs(["Entrar", "Cadastrar-se"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                user_info = login(email, password)
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_info['id']
                    st.session_state.user_name = user_info['name']
                    st.session_state.user_email = user_info['email']
                    st.rerun()
                else:
                    st.error("Email ou senha inválidos.")
    with signup_tab:
        with st.form("signup_form", clear_on_submit=True):
            name = st.text_input("Nome completo", key="signup_name")
            email = st.text_input("Seu melhor email", key="signup_email")
            password = st.text_input("Crie uma senha segura", type="password", key="signup_password")
            if st.form_submit_button("Criar Conta", use_container_width=True):
                if name and email and password:
                    hashed_pass = hash_password(password)
                    conn = get_db_connection()
                    try:
                        with conn.cursor() as cur:
                            cur.execute("INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
                                        (name, email, hashed_pass))
                            conn.commit()
                        st.success("Conta criada com sucesso! Volte para a aba 'Entrar' para fazer o login.")
                    except psycopg2.errors.UniqueViolation:
                        st.error("Este email já está cadastrado.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")
                else:
                    st.warning("Por favor, preencha todos os campos.")
else:
    load_user_data()

    with st.sidebar:
        st.title(f"Olá, {st.session_state.user_name}!")
        st.markdown(f"**Nível {st.session_state.user_level}: {LEVEL_NAMES[st.session_state.user_level]}**")
        if st.session_state.user_level < len(XP_PER_LEVEL):
            xp_needed = XP_PER_LEVEL[st.session_state.user_level]
            xp_prev = XP_PER_LEVEL[st.session_state.user_level - 1] if st.session_state.user_level > 0 else 0
            if (xp_needed - xp_prev) > 0:
                progress_val = (st.session_state.user_xp - xp_prev) / (xp_needed - xp_prev)
                st.progress(min(1.0, progress_val))
            else:
                st.progress(1.0)
            st.caption(f"{st.session_state.user_xp} / {xp_needed} XP")
        else:
            st.success("Nível Máximo Atingido! 🏆")

        st.markdown("---")
        pages = {"Dashboard": "🏠", "Tarefas": "🗂️", "Ferramentas": "🛠️"}
        if 'page' not in st.session_state:
            st.session_state.page = "Dashboard"
        st.session_state.page = st.radio("Menu", options=pages.keys(), format_func=lambda p: f"{pages[p]} {p}")
        st.markdown("---")
        st.info("EduSync Pro v5.0 (Flashcard Ed.)")
        if st.button("Logout", use_container_width=True):
            logout()

    if st.session_state.page == "Dashboard":
        show_dashboard()
    elif st.session_state.page == "Tarefas":
        show_tarefas()
    elif st.session_state.page == "Ferramentas":
        show_ferramentas()