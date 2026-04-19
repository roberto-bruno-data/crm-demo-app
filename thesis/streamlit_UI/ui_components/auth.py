import streamlit as st
import hmac

def require_auth():
  
    if st.session_state.get("authenticated", False):
        return

    st.set_page_config(page_title="Login")

    st.title("🔒 Geschützter Zugang")

    password = st.text_input("Passwort", type="password")
    if st.button("Anmelden"):
        if hmac.compare_digest(password, st.secrets["APP_PASSWORD"]):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")

    

    st.stop()
