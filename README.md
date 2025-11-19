Interactive FIRE Model

This is a lightweight Streamlit app that produces a year by year projection for a household FIRE plan.

How to run locally

1. Create a Python environment python 3.10+ recommended
2. Install requirements
   pip install -r requirements.txt
3. Run the app
   streamlit run app.py

Deployment options

Option A Streamlit Cloud
Push this folder to a GitHub repo and connect it to Streamlit Cloud

Option B Docker or VPS
Create a simple Dockerfile that exposes port 8501 and run in any container host

What the app includes

Inputs sidebar to change retirement age inflation returns contributions social security mortgage and starting portfolio
Year by year table
Downloadable Excel
Simple chart of portfolio over time
Validation indicator that flags if portfolio goes negative

Next steps

I can add
Tax aware withdrawals
Separate account buckets Roth traditional brokerage
Sequence of returns stress tests and Monte Carlo simulations
College outflows and home downsize scenarios


