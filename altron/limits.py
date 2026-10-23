import time
import streamlit as st

@st.cache_resource
def _global():
    return {'day': time.strftime('%Y-%m-%d'), 'n': 0}

def allow(session_cap=20, global_cap=500):
    g = _global()
    today = time.strftime('%Y-%m-%d')
    if g['day'] != today:
        g.update(day=today, n=0)
    used = st.session_state.setdefault('calls', 0)
    if used >= session_cap or g['n'] >= global_cap:
        return False
    st.session_state.calls += 1
    g['n'] += 1
    return True