import streamlit as st
import time
import ollama
from datetime import date, datetime
from streamlit_calendar import calendar
import json # <--- Módulo para trabalhar com JSON
import os   # <--- Módulo para verificar se o arquivo existe

# --- CONFIGURAÇÕES GERAIS E PERSISTÊNCIA ---
st.set_page_config(
    page_title="EduSync Pro (Com Memória)",
    page_icon="🧠",
    layout="wide",
)

# Nome do arquivo que guardará o estado da aplicação
STATE_FILE = "user_data.json"

# --- FUNÇÕES DE PERSISTÊNCIA DE DADOS (NOVO) ---

def save_state():
    """Salva o estado relevante da sessão em um arquivo JSON."""
    keys_to_save = [
        'user_name', 'user_xp', 'user_level', 'achievements', 
        'pomodoro_sessions_done', 'task_lists', 'calendar_events', 
        'flashcards', 'notes'
    ]
    
    state_to_save = {key: st.session_state[key] for key in keys_to_save if key in st.session_state}
    
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        # Em um app real, logaríamos esse erro
        print(f"Erro ao salvar estado: {e}")

def load_state():
    """Carrega o estado do arquivo JSON, se ele existir."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Se o arquivo estiver corrompido ou for removido durante a execução
            return {}
    return {}

def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #0f1116; }
        .card { background-color: #1c1f2b; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); border: 1px solid #2a2f45; }
        div[data-testid="stMetric"] { background-color: #2a2f45; border-radius: 8px; padding: 15px; text-align: center; }
        div[data-testid="stMetric"] > div:nth-child(2) > div { font-size: 2.5rem; }
        .achievement-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 20px; }
        .achievement-card { text-align: center; padding: 10px; border-radius: 8px; background-color: #2a2f45; }
        .achievement-card.unlocked { border: 2px solid #4ECDC4; }
        .achievement-icon { font-size: 3rem; filter: grayscale(80%); opacity: 0.5; transition: all 0.3s ease-in-out; }
        .unlocked .achievement-icon { filter: grayscale(0%); opacity: 1; transform: scale(1.1); }
    </style>
    """, unsafe_allow_html=True)


# --- 2. LÓGICA DE GAMIFICAÇÃO (com chamadas para save_state) ---
XP_PER_LEVEL = [100, 250, 500, 1000, 2000]
LEVEL_NAMES = ["Noviço do Saber", "Aprendiz Focado", "Estudante Mestre", "Sábio Produtivo", "Lenda do Conhecimento"]

ACHIEVEMENTS = {
    "first_task": {"name": "Primeiro Passo", "icon": "✅", "desc": "Conclua sua primeira tarefa.", "unlocked": False},
    "ten_tasks": {"name": "Maratonista", "icon": "🏃", "desc": "Conclua 10 tarefas.", "unlocked": False},
    "pomodoro_pro": {"name": "Foco Absoluto", "icon": "🎯", "desc": "Complete 5 sessões Pomodoro.", "unlocked": False},
    "night_owl": {"name": "Coruja da Madrugada", "icon": "🦉", "desc": "Complete uma tarefa entre 00h e 04h.", "unlocked": False},
    "card_creator": {"name": "Criador de Conteúdo", "icon": "🧠", "desc": "Crie 10 flashcards.", "unlocked": False},
}

def add_xp(points):
    st.session_state.user_xp += points
    st.toast(f"+{points} XP! ✨")
    check_level_up() # check_level_up já chama save_state

def check_level_up():
    current_level = st.session_state.user_level
    if current_level < len(XP_PER_LEVEL) and st.session_state.user_xp >= XP_PER_LEVEL[current_level]:
        st.session_state.user_level += 1
        st.balloons()
        st.toast(f"Você subiu de nível! Agora é um {LEVEL_NAMES[st.session_state.user_level]}!", icon="🎉")
        save_state() # Salva o novo nível

def check_achievements(event):
    achievements = st.session_state.achievements
    unlocked_new = False

    if event == "task_completed":
        # ... (lógica de conquistas) ...
        if not achievements["first_task"]["unlocked"]:
            achievements["first_task"]["unlocked"] = True; unlocked_new = True
        if len(st.session_state.task_lists['Feito']) >= 10 and not achievements["ten_tasks"]["unlocked"]:
            achievements["ten_tasks"]["unlocked"] = True; unlocked_new = True
        if 0 <= datetime.now().hour < 4 and not achievements["night_owl"]["unlocked"]:
            achievements["night_owl"]["unlocked"] = True; unlocked_new = True
            
    elif event == "pomodoro_completed":
        st.session_state.pomodoro_sessions_done += 1
        if st.session_state.pomodoro_sessions_done >= 5 and not achievements["pomodoro_pro"]["unlocked"]:
            achievements["pomodoro_pro"]["unlocked"] = True; unlocked_new = True

    elif event == "flashcard_created":
        if len(st.session_state.flashcards) >= 10 and not achievements["card_creator"]["unlocked"]:
            achievements["card_creator"]["unlocked"] = True; unlocked_new = True

    if unlocked_new:
        st.toast("Nova Conquista Desbloqueada!", icon="🏆")
        st.balloons()
        save_state() # Salva o estado com a nova conquista


# --- 3. FUNÇÕES DE SERVIÇO (IA) ---
def get_local_ai_response(prompt):
    try:
        response = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        st.error(f"Falha ao conectar com o Ollama: {e}", icon="🔌")
        return f"Ocorreu um erro ao acessar o modelo local."

# As funções de login/logout não são mais necessárias da mesma forma.
# O "logout" pode ser reimaginado como "resetar progresso".
def reset_progress():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    # Limpa a sessão atual para forçar a reinicialização
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 4. FUNÇÕES DE CADA PÁGINA (com chamadas para save_state) ---

def show_dashboard():
    # ... (código do dashboard igual) ...
    st.title(f"🚀 Hub de Estudos, {st.session_state.user_name}!")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="🔵 A Fazer", value=len(st.session_state.task_lists['A Fazer']))
    col2.metric(label="🟡 Fazendo", value=len(st.session_state.task_lists['Fazendo']))
    col3.metric(label="🟢 Feito", value=len(st.session_state.task_lists['Feito']))
    st.markdown("---")
    
    st.subheader("⚡ Adicionar Nova Tarefa Rápida")
    with st.form("quick_add_task_form", clear_on_submit=True):
        new_task = st.text_input("Qual a sua próxima tarefa?", placeholder="Ex: Pesquisar sobre a Revolução Francesa")
        if st.form_submit_button("Adicionar em 'A Fazer'", type="primary", use_container_width=True) and new_task:
            st.session_state.task_lists['A Fazer'].append(new_task)
            save_state() # <--- Salva o estado
            st.toast(f"Tarefa '{new_task}' adicionada!", icon="✅");
            st.rerun()

def show_tarefas():
    # ... (código das tarefas igual) ...
    st.title("🗂️ Gerenciador de Tarefas Kanban")
    
    list_names = ['A Fazer', 'Fazendo', 'Feito']
    cols = st.columns(len(list_names))
    for i, list_name in enumerate(list_names):
        with cols[i]:
            st.markdown(f'<div class="card" style="min-height: 400px;"><h4>{list_name}</h4><hr>', unsafe_allow_html=True)
            for task_index, task in enumerate(st.session_state.task_lists[list_name][:]):
                st.markdown(f"<div style='padding: 10px;'>{task}</div>", unsafe_allow_html=True)
                new_status = st.selectbox(f"status_{list_name}_{task_index}", options=list_names, index=i, label_visibility="collapsed", key=f"select_{list_name}_{task_index}")
                
                if st.button("🗑️ Excluir", key=f"del_{list_name}_{task_index}", help="Excluir tarefa", use_container_width=True):
                    st.session_state.task_lists[list_name].pop(task_index)
                    save_state() # <--- Salva o estado
                    st.toast("Tarefa removida!", icon="♻️")
                    st.rerun()

                if new_status != list_name:
                    task_to_move = st.session_state.task_lists[list_name].pop(task_index)
                    st.session_state.task_lists[new_status].append(task_to_move)
                    if new_status == 'Feito':
                        add_xp(10)
                        check_achievements("task_completed")
                    else:
                        save_state() # <--- Salva o estado (add_xp/check_achievements já salvam)
                    st.rerun()
                st.markdown("---")
            st.markdown('</div>', unsafe_allow_html=True)

def show_ferramentas():
    st.title("🛠️ Ferramentas de Estudo")
    tab1, tab2, tab3 = st.tabs(["🍅 Cronômetro Pomodoro", "🗂️ Flashcards", "📝 Anotações"])
    
    # ... (Lógica do Pomodoro igual) ...

    with tab2:
        # ... (Lógica dos Flashcards) ...
        with st.expander("➕ Adicionar Novo Cartão"):
            with st.form("new_card_form", clear_on_submit=True):
                front = st.text_input("Frente do cartão")
                back = st.text_area("Verso do cartão")
                if st.form_submit_button("Adicionar"):
                    if front and back:
                        st.session_state.flashcards.append({"frente": front, "verso": back})
                        check_achievements("flashcard_created")
                        save_state() # <--- Salva o estado
                        st.toast("Cartão adicionado!", icon="✨")
                        st.rerun()
    with tab3:
        st.subheader("Anotações Rápidas")
        st.session_state.notes = st.text_area("Suas Anotações", value=st.session_state.get('notes', ""), height=300, label_visibility="collapsed", on_change=save_state) # <--- Salva ao mudar

# ... (outras funções de página não foram incluídas para brevidade, mas o padrão é o mesmo)

# --- 5. LÓGICA PRINCIPAL DO APP (MODIFICADA) ---
inject_custom_css()

# Lógica de inicialização: Carregar estado ou definir padrões
if 'state_loaded' not in st.session_state:
    loaded_data = load_state()
    
    # Se carregou dados, usa-os
    if loaded_data:
        for key, value in loaded_data.items():
            st.session_state[key] = value
    # Se não, é a primeira vez. Define os padrões.
    else:
        st.session_state.user_name = "" # Será pedido na tela de boas-vindas
        st.session_state.user_xp = 0
        st.session_state.user_level = 0
        st.session_state.achievements = {k: v.copy() for k, v in ACHIEVEMENTS.items()}
        st.session_state.pomodoro_sessions_done = 0
        st.session_state.task_lists = {'A Fazer': ['Configurar ambiente local', 'Estudar Streamlit'], 'Fazendo': [], 'Feito': []}
        st.session_state.calendar_events = []
        st.session_state.flashcards = [{"frente": "Capital da França", "verso": "Paris"}]
        st.session_state.notes = "Escreva aqui suas anotações..."

    st.session_state.state_loaded = True

# Se não houver nome de usuário, mostra a tela de boas-vindas/criação de perfil
if not st.session_state.user_name:
    st.title("👋 Bem-vindo ao `EduSync Pro`!")
    st.subheader("Sua plataforma de estudos inteligente e com memória.")
    
    with st.form("profile_form"):
        name = st.text_input("Para começar, qual é o seu nome?")
        if st.form_submit_button("Salvar e Iniciar Jornada", type="primary"):
            if name:
                st.session_state.user_name = name
                save_state() # Salva o perfil recém-criado
                st.rerun()
            else:
                st.warning("Por favor, insira seu nome.")
else:
    # --- APLICAÇÃO PRINCIPAL ---
    with st.sidebar:
        st.title(f"Olá, {st.session_state.user_name}!")
        st.markdown(f"**Nível {st.session_state.user_level}: {LEVEL_NAMES[st.session_state.user_level]}**")
        if st.session_state.user_level < len(XP_PER_LEVEL):
            xp_needed = XP_PER_LEVEL[st.session_state.user_level]
            xp_prev = XP_PER_LEVEL[st.session_state.user_level - 1] if st.session_state.user_level > 0 else 0
            # Evita divisão por zero se xp_needed == xp_prev
            denominator = (xp_needed - xp_prev)
            if denominator > 0:
                progress_val = (st.session_state.user_xp - xp_prev) / denominator
                st.progress(progress_val)
            else: # Nível máximo atingido ou configuração estranha
                st.progress(1.0)
            st.caption(f"{st.session_state.user_xp} / {xp_needed} XP")
        else:
            st.success("Nível Máximo Atingido! 🏆")
        st.markdown("---")

        pages = {"Dashboard": "🏠", "Tarefas": "🗂️", "Ferramentas": "🛠️"}
        if 'page' not in st.session_state: st.session_state.page = "Dashboard"
        st.session_state.page = st.radio("Menu", options=pages.keys(), format_func=lambda page: f"{pages[page]} {page}")
        st.markdown("---")
        st.info("EduSync Pro (Com Memória)")
        if st.button("🗑️ Resetar Progresso", use_container_width=True, help="Apaga todos os dados e recomeça."):
            reset_progress()

    # Executa a função da página selecionada
    if st.session_state.page == "Dashboard":
        show_dashboard()
    elif st.session_state.page == "Tarefas":
        show_tarefas()
    elif st.session_state.page == "Ferramentas":
        show_ferramentas()
