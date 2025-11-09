import streamlit as st
from main import run_query

st.set_page_config(page_title="RAG MySQL Explorer", layout="wide")

st.title("RAG + MySQL Explorer")
st.write("Ask questions about the `people_info` table. The app will either run SQL or retrieve and summarize records using the LLM.")

query = st.text_input("Enter your query", placeholder="e.g. who is Asmi? or just list names")
if st.button("Run") and query:
    with st.spinner("Running..."):
        result = run_query(query)

    if result.get("error"):
        st.error(f"Error: {result['error']}")
    else:
        if result.get("generated_sql"):
            st.subheader("Generated / Executed SQL")
            st.code(result["generated_sql"])

        if result.get("sql_result") is not None:
            st.subheader("SQL Result")
            st.write(result["sql_result"])

        if result.get("retrieved_context"):
            st.subheader("Retrieved Rows")
            rows = result["retrieved_context"]
            # display as simple table if rows present
            try:
                import pandas as pd
                # attempt to map columns: id, name, age, height, weight, company, role, background
                cols = ["id", "name", "age", "height", "weight", "company", "role", "background"]
                df_rows = []
                for r in rows:
                    rowdict = {cols[i]: r[i] if i < len(r) else None for i in range(len(cols))}
                    df_rows.append(rowdict)
                df = pd.DataFrame(df_rows)
                st.dataframe(df)
            except Exception:
                for r in rows:
                    st.write(r)

        if result.get("model_answer"):
            st.subheader("Model Answer")
            st.write(result["model_answer"]) 

st.markdown("---")
st.caption("Note: make sure your `.env` is configured and the virtualenv has the required packages. Run with: `streamlit run streamlit_app.py`")