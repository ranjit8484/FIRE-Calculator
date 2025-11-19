import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(layout="wide", page_title="Interactive FIRE Model")

def build_projection(inputs):
    start_age = inputs["projection_start_age"]
    end_age = inputs["projection_end_age"]
    ages = list(range(start_age, end_age + 1))
    rows = []
    portfolio = inputs["portfolio_at_45"]
    starting_age = inputs["starting_age"]
    for age in ages:
        row = {}
        row["Age"] = age
        row["Portfolio Start"] = portfolio
        contrib = inputs["annual_contribution"] if age < inputs["retirement_age"] else 0.0
        row["Contribution"] = contrib
        ret = inputs["pre_ret_return"] if age < inputs["retirement_age"] else inputs["post_ret_return"]
        growth = portfolio * ret
        row["Growth"] = growth
        if age < inputs["retirement_age"]:
            spend = 0.0
        else:
            years_since_start = age - starting_age
            spend = inputs["annual_spending_today"] * ((1 + inputs["inflation"]) ** years_since_start)
        row["Inflated Spending"] = spend
        ss = inputs["ss_annual_benefit"] * ((1 + inputs["inflation"]) ** max(0, age - inputs["ss_start_age"])) if age >= inputs["ss_start_age"] else 0.0
        row["Social Security"] = ss
        mortgage = inputs["mortgage_annual_payment"] if inputs["mortgage_balance"]>0 and inputs["projection_start_age"] <= age <= inputs["mortgage_end_age"] else 0.0
        row["Mortgage Payment"] = mortgage
        total_spend = spend - ss + mortgage
        row["Total Spending"] = total_spend
        end = portfolio + contrib + growth - total_spend
        row["Portfolio End"] = end
        rows.append(row)
        portfolio = end
    df = pd.DataFrame(rows)
    return df

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Projection")
        writer.save()
    processed_data = output.getvalue()
    return processed_data

st.title("Interactive FIRE Model")
st.write("Adjust assumptions on the left. The projection is year by year from projection start age to projection end age.")

with st.sidebar:
    st.header("Inputs")
    starting_age = st.number_input("Starting Age", value=41, min_value=18, max_value=100)
    projection_start_age = st.number_input("Projection Start Age", value=45, min_value=starting_age, max_value=100)
    projection_end_age = st.number_input("Projection End Age", value=100, min_value=projection_start_age, max_value=120)
    retirement_age = st.number_input("Retirement Age", value=60, min_value=projection_start_age, max_value=projection_end_age)
    annual_spending_today = st.number_input("Annual Spending Today", value=200000, step=1000)
    inflation = st.number_input("Inflation Rate", value=0.03, format="%.4f")
    annual_contribution = st.number_input("Annual Contribution", value=100000, step=1000)
    pre_ret_return = st.number_input("Pre Retirement Return", value=0.06, format="%.4f")
    post_ret_return = st.number_input("Post Retirement Return", value=0.04, format="%.4f")
    ss_start_age = st.number_input("Social Security Start Age", value=67, min_value=62, max_value=75)
    ss_annual_benefit = st.number_input("Social Security Annual Benefit Today", value=65000, step=1000)
    mortgage_balance = st.number_input("Mortgage Balance", value=250000, step=1000)
    mortgage_annual_payment = st.number_input("Mortgage Annual Payment", value=30000, step=500)
    mortgage_end_age = st.number_input("Mortgage End Age", value=55, min_value=projection_start_age, max_value=projection_end_age)
    portfolio_at_45 = st.number_input("Portfolio at Projection Start Age (age 45)", value=1550000.0, step=1000.0, format="%.2f")
    st.write("---")
    st.write("Quick scenarios")
    if st.button("Conservative"):
        inflation = 0.03
        pre_ret_return = 0.06
        post_ret_return = 0.04
        annual_contribution = 100000
        st.experimental_rerun()
    if st.button("Aggressive"):
        inflation = 0.025
        pre_ret_return = 0.08
        post_ret_return = 0.05
        annual_contribution = 150000
        st.experimental_rerun()

inputs = dict(
    starting_age = starting_age,
    projection_start_age = projection_start_age,
    projection_end_age = projection_end_age,
    retirement_age = retirement_age,
    annual_spending_today = annual_spending_today,
    inflation = inflation,
    annual_contribution = annual_contribution,
    pre_ret_return = pre_ret_return,
    post_ret_return = post_ret_return,
    ss_start_age = ss_start_age,
    ss_annual_benefit = ss_annual_benefit,
    mortgage_balance = mortgage_balance,
    mortgage_annual_payment = mortgage_annual_payment,
    mortgage_end_age = mortgage_end_age,
    portfolio_at_45 = portfolio_at_45,
)

df = build_projection(inputs)

col1, col2 = st.columns([2,1])
with col1:
    st.subheader("Projection table")
    st.dataframe(df.style.format({"Portfolio Start":"{:.0f}", "Contribution":"{:.0f}", "Growth":"{:.0f}", "Inflated Spending":"{:.0f}", "Social Security":"{:.0f}", "Mortgage Payment":"{:.0f}", "Total Spending":"{:.0f}", "Portfolio End":"{:.0f}"}), height=600)
    excel = to_excel(df)
    st.download_button("Download projection as Excel", excel, file_name="fire_projection.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col2:
    st.subheader("Charts")
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(df["Age"], df["Portfolio Start"]/1e6, marker="o")
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio Start (Millions)")
    ax.grid(True)
    st.pyplot(fig)
    st.write("Key summary")
    last_row = df.iloc[-1]
    st.metric("Portfolio at age " + str(int(df.iloc[-1]["Age"])), f"${int(last_row['Portfolio End']):,}")
    neg = df[df["Portfolio End"] < 0]
    if not neg.empty:
        st.error(f"Portfolio becomes negative at age {int(neg.iloc[0]['Age'])}")
    else:
        st.success("Portfolio stays positive through projection end age")

st.write("Model assumptions and formulas are in the app source. You can edit the code to add tax modeling bucketed accounts sequence of returns simulation Monte Carlo and Monte Carlo for spending shocks.")
