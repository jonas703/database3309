import mysql.connector
from tkinter import *
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# =========================
# DB CONFIG - EDIT THIS
# =========================
DB_CONFIG = {
    "host": "136.113.83.204",
    "user": "jon",           # <- your MySQL user
    "password": "Test-Pass1", # <- your MySQL password
    "database": "3309Grp13", # <- your DB name
}



# =========================
# DB HELPERS
# =========================

def get_conn():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", str(e))
        return None


def fetch_all(query, params=None):
    """Run SELECT and return (columns, rows)."""
    conn = get_conn()
    if not conn:
        return [], []
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return cols, rows
    except mysql.connector.Error as e:
        messagebox.showerror("SQL Error", str(e))
        return [], []
    finally:
        conn.close()


def execute_action(query, params=None):
    """Run INSERT/UPDATE/DELETE."""
    conn = get_conn()
    if not conn:
        return False
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("SQL Error", str(e))
        return False
    finally:
        conn.close()


# =========================
# MAIN APP
# =========================

class PortfolioApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("Investment Portfolio Manager")
        self.geometry("1300x780")

        self._setup_style()
        self._build_ui()

    # ---------- styling ----------
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        bg = "#222222"
        fg = "#e0e0e0"
        style.configure(".", background=bg, foreground=fg, fieldbackground="#333333")
        style.configure("Treeview", background="#333333", foreground=fg, rowheight=22)
        style.map("Treeview", background=[("selected", "#5555aa")])
        self.configure(bg=bg)

    # ---------- tabs ----------
    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

        self.tab_dashboard   = Frame(notebook, bg="#222222")
        self.tab_users       = Frame(notebook, bg="#222222")
        self.tab_portfolios  = Frame(notebook, bg="#222222")
        self.tab_transactions = Frame(notebook, bg="#222222")
        self.tab_risk        = Frame(notebook, bg="#222222")

        notebook.add(self.tab_dashboard,   text="Dashboard")
        notebook.add(self.tab_users,       text="Users")
        notebook.add(self.tab_portfolios,  text="Portfolios & Holdings")
        notebook.add(self.tab_transactions,text="Transactions")
        notebook.add(self.tab_risk,        text="Risk Analysis")

        self._build_dashboard_tab()
        self._build_users_tab()
        self._build_portfolios_tab()
        self._build_transactions_tab()
        self._build_risk_tab()

    # =========================
    # DASHBOARD TAB
    # =========================
    def _build_dashboard_tab(self):
        frm_top = Frame(self.tab_dashboard, bg="#222222")
        frm_top.pack(fill=X, pady=5)

        Label(frm_top, text="Portfolio ID:", bg="#222222", fg="#e0e0e0").pack(side=LEFT, padx=5)
        self.ent_dash_portfolio = Entry(frm_top, width=8)
        self.ent_dash_portfolio.pack(side=LEFT)

        Label(frm_top, text="Ticker (for price history):", bg="#222222", fg="#e0e0e0").pack(side=LEFT, padx=5)
        self.ent_dash_ticker = Entry(frm_top, width=10)
        self.ent_dash_ticker.pack(side=LEFT)

        ttk.Button(frm_top, text="Load Dashboard", command=self.load_dashboard).pack(side=LEFT, padx=5)

        self.lbl_dash_summary = Label(self.tab_dashboard, text="", bg="#222222",
                                      fg="#e0e0e0", justify=LEFT, font=("Segoe UI", 10))
        self.lbl_dash_summary.pack(anchor="w", padx=10, pady=5)

        # charts frame
        frm_charts = Frame(self.tab_dashboard, bg="#222222")
        frm_charts.pack(fill=BOTH, expand=True)

        # Figure: 2x2 grid
        self.fig_dash = Figure(figsize=(9, 5), dpi=100)
        self.ax_alloc = self.fig_dash.add_subplot(221)  # pie allocation
        self.ax_pl    = self.fig_dash.add_subplot(222)  # bar P/L
        self.ax_price = self.fig_dash.add_subplot(212)  # line price history

        self.canvas_dash = FigureCanvasTkAgg(self.fig_dash, master=frm_charts)
        self.canvas_dash.get_tk_widget().pack(fill=BOTH, expand=True)

    def load_dashboard(self):
        pid = self.ent_dash_portfolio.get().strip()
        ticker = self.ent_dash_ticker.get().strip()

        if not pid.isdigit():
            messagebox.showwarning("Input", "Enter a valid portfolio ID.")
            return
        pid = int(pid)

        # ---------- holdings for the portfolio ----------
        h_cols, holdings = fetch_all(
            "SELECT tickerSymbol, bookCost, marketValue, profitAndLoss "
            "FROM UserDefinedHoldingPerformance WHERE portfolioID = %s",
            (pid,)
        )
        if not holdings:
            self.lbl_dash_summary.config(text="No holdings for this portfolio.")
            self.ax_alloc.clear()
            self.ax_pl.clear()
            self.ax_price.clear()
            self.canvas_dash.draw()
            return

        # summary row
        sum_cols, summary = fetch_all(
            "SELECT portfolioID, "
            "SUM(bookCost) AS bookValue, "
            "SUM(marketValue) AS marketValue, "
            "SUM(profitAndLoss) AS profitAndLoss, "
            "(SUM(profitAndLoss)/NULLIF(SUM(bookCost),0))*100 AS totalPercentGain "
            "FROM UserDefinedHoldingPerformance "
            "WHERE portfolioID = %s GROUP BY portfolioID",
            (pid,)
        )
        if summary:
            _, book, market, pl, pct = summary[0]
            txt = (f"Portfolio {pid}\n"
                   f"Book Value: {book:.2f}\n"
                   f"Market Value: {market:.2f}\n"
                   f"Profit / Loss: {pl:.2f}\n"
                   f"Total % Gain: {pct:.2f}%")
            self.lbl_dash_summary.config(text=txt)

        # ---------- Pie chart: allocation ----------
        tickers = [r[0] for r in holdings]
        mvals   = [float(r[2]) for r in holdings]

        self.ax_alloc.clear()
        self.ax_alloc.pie(mvals, labels=tickers, autopct="%1.1f%%")
        self.ax_alloc.set_title("Allocation by Market Value")

        # ---------- Bar chart: P/L per holding ----------
        pls = [float(r[3]) for r in holdings]
        self.ax_pl.clear()
        self.ax_pl.bar(tickers, pls)
        self.ax_pl.set_title("Profit / Loss by Holding")
        self.ax_pl.set_xticklabels(tickers, rotation=45, ha="right")

        # ---------- Line chart: price history for selected ticker ----------
        self.ax_price.clear()
        if ticker:
            ph_cols, prices = fetch_all(
                "SELECT transactionDate, marketPricePerShare "
                "FROM TransactionRecord "
                "WHERE portfolioID = %s AND tickerSymbol = %s "
                "ORDER BY transactionDate",
                (pid, ticker)
            )
            if prices:
                dates = [p[0] for p in prices]
                vals  = [float(p[1]) for p in prices]
                self.ax_price.plot(dates, vals, marker="o")
                self.ax_price.set_title(f"Price History for {ticker} (portfolio {pid})")
                self.ax_price.set_xlabel("Date")
                self.ax_price.set_ylabel("Price")
                self.ax_price.tick_params(axis='x', rotation=45)
            else:
                self.ax_price.text(0.5, 0.5,
                                   f"No price history for {ticker} in portfolio {pid}.",
                                   transform=self.ax_price.transAxes,
                                   ha="center", va="center", color="white")
        else:
            self.ax_price.text(0.5, 0.5,
                               "Enter a ticker and click Load Dashboard\nto see price history.",
                               transform=self.ax_price.transAxes,
                               ha="center", va="center", color="white")
        self.fig_dash.tight_layout()
        self.canvas_dash.draw()

    # =========================
    # USERS TAB (UserProfile)
    # =========================
    def _build_users_tab(self):
        frm_top = Frame(self.tab_users, bg="#222222")
        frm_top.pack(fill=X, pady=5)

        ttk.Button(frm_top, text="Refresh Users", command=self.load_users).pack(side=LEFT, padx=5)
        ttk.Button(frm_top, text="Delete Selected User", command=self.delete_user).pack(side=LEFT, padx=5)

        self.tree_users = ttk.Treeview(self.tab_users, show="headings")
        self.tree_users.pack(fill=BOTH, expand=True, padx=5, pady=5)

        self.load_users()

    def load_users(self):
        cols, rows = fetch_all("SELECT userID, fName, lName, dateOfBirth FROM UserProfile;")
        if not cols:
            return
        self.tree_users.delete(*self.tree_users.get_children())
        self.tree_users["columns"] = cols
        self.tree_users.column("#0", width=0, stretch=NO)
        for c in cols:
            self.tree_users.heading(c, text=c)
            self.tree_users.column(c, width=120)
        for r in rows:
            self.tree_users.insert("", END, values=r)

    def delete_user(self):
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a user row.")
            return
        vals = self.tree_users.item(sel[0], "values")
        user_id = vals[0]
        if not messagebox.askyesno("Confirm", f"Delete user {user_id}? "
                                              "Ensure cascading FKs are set or cleanup manually."):
            return

        ok = execute_action("DELETE FROM UserProfile WHERE userID = %s", (user_id,))
        if ok:
            self.load_users()
            messagebox.showinfo("Deleted", f"User {user_id} deleted.")

    # =========================
    # PORTFOLIOS TAB
    # =========================
    def _build_portfolios_tab(self):
        frm_top = Frame(self.tab_portfolios, bg="#222222")
        frm_top.pack(fill=X, pady=5)

        ttk.Button(frm_top, text="Refresh Portfolios", command=self.load_portfolios).pack(side=LEFT, padx=5)
        ttk.Button(frm_top, text="Delete Selected Portfolio", command=self.delete_portfolio).pack(side=LEFT, padx=5)

        Label(frm_top, text="Portfolio ID:", bg="#222222", fg="#e0e0e0").pack(side=LEFT, padx=5)
        self.ent_portfolio_filter = Entry(frm_top, width=8)
        self.ent_portfolio_filter.pack(side=LEFT)
        ttk.Button(frm_top, text="View Holdings", command=self.show_portfolio_holdings).pack(side=LEFT, padx=5)

        frm_tables = Frame(self.tab_portfolios, bg="#222222")
        frm_tables.pack(fill=BOTH, expand=True)

        self.tree_portfolios = ttk.Treeview(frm_tables, show="headings", height=8)
        self.tree_portfolios.pack(fill=X, padx=5, pady=5)

        self.tree_holdings = ttk.Treeview(frm_tables, show="headings")
        self.tree_holdings.pack(fill=BOTH, expand=True, padx=5, pady=5)

        self.load_portfolios()

    def load_portfolios(self):
        cols, rows = fetch_all("SELECT portfolioID, baseCurrency, userID FROM Portfolio;")
        if not cols:
            return
        self.tree_portfolios.delete(*self.tree_portfolios.get_children())
        self.tree_portfolios["columns"] = cols
        self.tree_portfolios.column("#0", width=0, stretch=NO)
        for c in cols:
            self.tree_portfolios.heading(c, text=c)
            self.tree_portfolios.column(c, width=120)
        for r in rows:
            self.tree_portfolios.insert("", END, values=r)

    def delete_portfolio(self):
        sel = self.tree_portfolios.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a portfolio row.")
            return
        vals = self.tree_portfolios.item(sel[0], "values")
        pid = vals[0]
        if not messagebox.askyesno("Confirm", f"Delete portfolio {pid}? "
                                              "Ensure FKs cascade to holdings/transactions."):
            return
        ok = execute_action("DELETE FROM Portfolio WHERE portfolioID = %s", (pid,))
        if ok:
            self.load_portfolios()
            self.tree_holdings.delete(*self.tree_holdings.get_children())
            messagebox.showinfo("Deleted", f"Portfolio {pid} deleted.")

    def show_portfolio_holdings(self):
        pid = self.ent_portfolio_filter.get().strip()
        if not pid.isdigit():
            messagebox.showwarning("Input", "Enter a valid portfolio ID.")
            return
        cols, rows = fetch_all(
            "SELECT tickerSymbol, quantityOwned, bookCost, marketValue, "
            "profitAndLoss, percentGain "
            "FROM UserDefinedHoldingPerformance WHERE portfolioID = %s",
            (pid,)
        )
        if not cols:
            return
        self.tree_holdings.delete(*self.tree_holdings.get_children())
        self.tree_holdings["columns"] = cols
        self.tree_holdings.column("#0", width=0, stretch=NO)
        for c in cols:
            self.tree_holdings.heading(c, text=c)
            self.tree_holdings.column(c, width=120)
        for r in rows:
            self.tree_holdings.insert("", END, values=r)

    # =========================
    # TRANSACTIONS TAB
    # =========================
    def _build_transactions_tab(self):
        frm_form = Frame(self.tab_transactions, bg="#222222")
        frm_form.pack(fill=X, pady=10, padx=10)

        labels = ["Transaction ID", "Portfolio ID", "Ticker",
                  "Investment Type", "Market Price",
                  "Sale Price (NULL ok)", "Quantity"]
        self.ent_tx = []
        for i, lab in enumerate(labels):
            Label(frm_form, text=lab + ":", bg="#222222", fg="#e0e0e0").grid(row=i, column=0, sticky="e", pady=2)
            e = Entry(frm_form, width=20)
            e.grid(row=i, column=1, sticky="w", pady=2)
            self.ent_tx.append(e)

        ttk.Button(frm_form, text="Insert Transaction",
                   command=self.insert_transaction).grid(row=len(labels), column=0,
                                                         columnspan=2, pady=5)

        ttk.Button(self.tab_transactions, text="View Recent Transactions",
                   command=self.view_transactions).pack(pady=5)
        self.tree_tx = ttk.Treeview(self.tab_transactions, show="headings")
        self.tree_tx.pack(fill=BOTH, expand=True, padx=5, pady=5)

    def insert_transaction(self):
        tid, pid, ticker, invtype, mprice, sprice, qty = [e.get().strip() for e in self.ent_tx]
        if not (tid and pid and ticker and invtype and mprice and qty):
            messagebox.showwarning("Input", "Fill in required fields (sale price can be empty).")
            return
        sprice_val = None if sprice == "" else sprice

        query = """
        INSERT INTO TransactionRecord
        (transactionID, portfolioID, tickerSymbol, investmentType,
         marketPricePerShare, salePricePerShare, quantity, transactionDate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,CURDATE())
        """
        params = (tid, pid, ticker, invtype, mprice, sprice_val, qty)
        if execute_action(query, params):
            messagebox.showinfo("Success", "Transaction inserted.")
            self.view_transactions()

    def view_transactions(self):
        cols, rows = fetch_all(
            "SELECT transactionID, portfolioID, tickerSymbol, investmentType, "
            "marketPricePerShare, salePricePerShare, quantity, transactionDate "
            "FROM TransactionRecord "
            "ORDER BY transactionDate DESC, transactionID DESC LIMIT 100"
        )
        if not cols:
            return
        self.tree_tx.delete(*self.tree_tx.get_children())
        self.tree_tx["columns"] = cols
        self.tree_tx.column("#0", width=0, stretch=NO)
        for c in cols:
            self.tree_tx.heading(c, text=c)
            self.tree_tx.column(c, width=120)
        for r in rows:
            self.tree_tx.insert("", END, values=r)

    # =========================
    # RISK TAB (pies + table)
    # =========================
    def _build_risk_tab(self):
        frm_top = Frame(self.tab_risk, bg="#222222")
        frm_top.pack(fill=X, pady=5)

        Label(frm_top, text="User ID:", bg="#222222", fg="#e0e0e0").pack(side=LEFT, padx=5)
        self.ent_risk_user = Entry(frm_top, width=8)
        self.ent_risk_user.pack(side=LEFT)

        ttk.Button(frm_top, text="Run GetRiskAnalysis",
                   command=self.run_risk).pack(side=LEFT, padx=5)

        # table
        self.tree_risk = ttk.Treeview(self.tab_risk, show="headings", height=10)
        self.tree_risk.pack(fill=X, padx=5, pady=5)

        # charts
        frm_charts = Frame(self.tab_risk, bg="#222222")
        frm_charts.pack(fill=BOTH, expand=True)

        self.fig_risk = Figure(figsize=(8, 4), dpi=100)
        self.ax_actual = self.fig_risk.add_subplot(121)  # actual allocation pie
        self.ax_ideal  = self.fig_risk.add_subplot(122)  # ideal allocation pie

        self.canvas_risk = FigureCanvasTkAgg(self.fig_risk, master=frm_charts)
        self.canvas_risk.get_tk_widget().pack(fill=BOTH, expand=True)

    def run_risk(self):
        uid = self.ent_risk_user.get().strip()
        if not uid.isdigit():
            messagebox.showwarning("Input", "Enter a valid user ID.")
            return
        uid = int(uid)

        conn = get_conn()
        if not conn:
            return
        try:
            cur = conn.cursor()
            # assuming procedure signature: GetRiskAnalysis(IN p_userID INT)
            cur.callproc("GetRiskAnalysis", (uid,))

            all_rows = []
            all_cols = None
            for result in cur.stored_results():
                rows = result.fetchall()
                cols = [d[0] for d in result.description]
                all_rows = rows
                all_cols = cols
                break  # only first result set

            if not all_cols:
                messagebox.showinfo("Risk", "No risk data returned.")
                return

            # populate table
            self.tree_risk.delete(*self.tree_risk.get_children())
            self.tree_risk["columns"] = all_cols
            self.tree_risk.column("#0", width=0, stretch=NO)
            for c in all_cols:
                self.tree_risk.heading(c, text=c)
                self.tree_risk.column(c, width=120)
            for r in all_rows:
                self.tree_risk.insert("", END, values=r)

            # -------- build pie charts from result --------
            # we assume columns: modelRiskCategory, actualPct, idealPct
            # based on our earlier GetRiskAnalysis design
            idx_cat = all_cols.index("modelRiskCategory") if "modelRiskCategory" in all_cols else None
            idx_act = all_cols.index("actualPct") if "actualPct" in all_cols else None
            idx_ideal = all_cols.index("idealPct") if "idealPct" in all_cols else None

            if idx_cat is None or idx_act is None or idx_ideal is None:
                # can't plot if columns missing
                self.ax_actual.clear()
                self.ax_ideal.clear()
                self.ax_actual.text(0.5, 0.5, "modelRiskCategory / actualPct / idealPct\nnot found in result.",
                                    transform=self.ax_actual.transAxes,
                                    ha="center", va="center", color="white")
                self.ax_ideal.axis("off")
                self.canvas_risk.draw()
                return

            # aggregate by category
            agg_actual = {}
            agg_ideal = {}
            for row in all_rows:
                cat = row[idx_cat] or "Unknown"
                act = float(row[idx_act]) if row[idx_act] is not None else 0.0
                ideal = float(row[idx_ideal]) if row[idx_ideal] is not None else 0.0
                agg_actual[cat] = agg_actual.get(cat, 0.0) + act
                agg_ideal[cat]  = agg_ideal.get(cat, 0.0) + ideal

            labels = list(agg_actual.keys())
            actual_vals = [agg_actual[l] for l in labels]
            ideal_vals  = [agg_ideal.get(l, 0.0) for l in labels]

            self.ax_actual.clear()
            self.ax_actual.pie(actual_vals, labels=labels, autopct="%1.1f%%")
            self.ax_actual.set_title("Actual Allocation by Risk Category")

            self.ax_ideal.clear()
            self.ax_ideal.pie(ideal_vals, labels=labels, autopct="%1.1f%%")
            self.ax_ideal.set_title("Ideal Allocation by Risk Category")

            self.fig_risk.tight_layout()
            self.canvas_risk.draw()

        except mysql.connector.Error as e:
            messagebox.showerror("SQL Error", str(e))
        finally:
            conn.close()


if __name__ == "__main__":
    app = PortfolioApp()
    app.mainloop()
