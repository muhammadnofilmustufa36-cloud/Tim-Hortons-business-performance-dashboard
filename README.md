# ☕ Tim Hortons Business Performance Dashboard (Python ETL & Power BI)

An end-to-end Data Engineering and Business Intelligence project analyzing sales, profitability, customer behavior, and store performance for a simulated Tim Hortons retail network across Canada — featuring automated Python ETL preprocessing and an interactive multi-page Power BI dashboard.

---

## 📌 Project Overview

This project simulates a full end-to-end Data Analyst & Data Engineering workflow: ingesting raw transactional data, cleaning and transforming it through a custom **Python (Pandas) ETL script**, modeling it into a clean star schema, and building an interactive multi-page Power BI dashboard that surfaces revenue, profitability, customer, and geographic insights for stakeholders.

**Business questions this dashboard answers:**
- How is revenue and profit trending over time, and which stores/categories drive it?
- Which products are the top revenue and profit generators?
- How do new vs. returning customers behave, and what drives retention?
- Which regions, provinces, and cities are the strongest and weakest performers?
- When (day of week / time of day) do customers order the most?

---

## 🛠️ Data Engineering & Python Workflow

Unlike standard reporting pipelines, this project includes a robust programmatic **ETL (Extract, Transform, Load)** stage:
1. **Extraction & Inspection:** Raw multi-column sales files were loaded into Python (`pandas`) to analyze data grain, identify missing foreign keys, and audit data types.
2. **Transformation & Cleansing:** Cleaned null fields, standardized date formats, and programmatically split flat transactions into structured dimension tables.
3. **Staging & Integration:** Exported normalized staging files (`FactSales`, `DimStore`, `DimLocation`, `DimDate`, `DimProduct`) for flawless Power BI ingestion.

---

## 📊 Dataset

- **File:** `Tim_Hortons_Portfolio_Dataset.xlsx` (and processed staging CSVs)
- **Rows:** ~17,445 transactions
- **Grain:** One row per order line item

| Field | Description |
| :--- | :--- |
| `OrderID`, `OrderDate`, `OrderTime` | Transaction identifiers and timestamps |
| `Year`, `Quarter`, `Month`, `Day`, `DayName`, `Hour` | Date/time breakdowns for time-based analysis |
| `Store`, `City` | Store location details |
| `Category`, `Product`, `Size` | Product hierarchy |
| `Quantity`, `UnitPrice`, `Discount` | Order line details |
| `Revenue`, `Cost`, `Profit` | Financial metrics |
| `PaymentMethod` | Credit Card / Cash / Debit Card |
| `CustomerType` | New / Returning |

*The dataset spans stores in Toronto (Downtown & North), Montreal, Vancouver, Ottawa, and Calgary, across five product categories: **Coffee, Sandwich, Bakery, Tea, and Desserts**.*

---

## 📐 Data Model & Architecture

A star schema was built in Power Query / Power BI to support efficient, scalable analysis:

<img width="858" height="445" alt="Data Model" src="https://github.com/user-attachments/assets/08c2d6bc-7c7b-4b10-a376-e8381eb0b8bb" />

- **`SalesData`** (fact table) — transaction-level revenue, cost, profit, and discount.
- **`DimDate`** — full date hierarchy (day, day name, month, weekend flag) for time intelligence.
- **`DimStore`** — store and city reference.
- **`DimLocation`** — city, province, and region mapping for geographic rollups.
- **`DimProduct`** — category and product reference.

*This structure enables clean, reusable relationships across all report pages and supports DAX measures like profit margin, retention %, and average order value.*

## 🧮 Key DAX Measures

1) AOV = DIVIDE([Total Revenue], [Total Orders], 0)
2) Average Price = DIVIDE([Total Revenue], [Total Units Sold], 0)
3) Avg Cust Spend = AVERAGE('FactSales'[Revenue])
4) Avg Order per Customer = 
DIVIDE(
    COUNT('FactSales'[OrderID]), 
    DISTINCTCOUNT('FactSales'[OrderID]), 
    1
)
5) New Customer Rev % = 
DIVIDE(
    CALCULATE([Total Revenue], 'FactSales'[CustomerType] = "New"),
    [Total Revenue],
    0
)
6) Profit Margin % = DIVIDE([Total Profit], [Total Revenue], 0)
7) Returning Customer Rev % = 
DIVIDE(
    CALCULATE([Total Revenue], 'FactSales'[CustomerType] = "Returning"),
    [Total Revenue],
    0
)
8) Top Store Name = 
TOPN(
    1, 
    VALUES('DimStore'[Store]), 
    [Total Revenue], 
    DESC
)
9) Top Store Sales = 
CALCULATE(
    [Total Revenue],
    TOPN(1, VALUES(DimStore[Store]), [Total Revenue], DESC)
)
10) Total Orders = DISTINCTCOUNT(FactSales[OrderID])
11) Total Profit = SUM(FactSales[Profit])
12) Total Revenue = SUM(FactSales[Revenue])
13) Total Units Sold = SUM(FactSales[Quantity])

DIVIDE() is used instead of the / operator throughout to avoid divide-by-zero errors when slicers filter data down to nothing.

DISTINCTCOUNT is used for Total Orders (rather than a simple row count) because a single order can span multiple line items — one row per product, not per order.

🖥️ Dashboard Page Architecture & Visuals

1. Performance Summary (Executive Overview)
KPI Cards: Total Revenue ($254.58K), Total Profit ($95.61K), Total Orders (17.44K), Units Sold (43.53K), and Profit Margin (37.6%).

Visuals:

Revenue vs Profit Trend: Dual-line chart showing monthly performance trajectories over time.

Top Performing Outlets: Bar chart highlighting top stores like Toronto Downtown ($89K) and North.

Category Revenue Split: Horizontal bar chart mapping revenue distribution across product categories.

Best Selling Products: Horizontal ranking chart for top-performing menu items (Cappuccino, Cold Brew, etc.).

2. Product & Category Insights
KPI Cards: Total Revenue, Total Profit, Total Orders, Average Order Value (AOV), and Average Price ($5.85).

Visuals:

Category Profit Split: Horizontal bar chart comparing profit generation per product.

Category Contribution: Donut chart showing percentage share of revenue by category (Coffee leading at 51.7%).

Category Sales & Profit: Clustered column/bar comparison breakdown.

Category Performance Matrix: Detailed tabular matrix breaking down Revenue, Profit, Orders, Avg Price, and Profit Margin%.

3. Customer Insights & Behavior
KPI Cards: Total Customers (17.44K), Retained Customers (11.29K), Acquired Customers (6,151), Purchase Frequency, and Average Patron Spend ($14.59).

Visuals:

Weekly Sales Pattern: Area/line chart tracking sales flow from Saturday down to Tuesday.

Customer Segment Mix: Donut chart comparing Returning vs. New customer ratios (64.62% vs 35.38%).

Retention vs Acquisition Trend: Line chart analyzing periodic customer retention cycles.

Payment Gateway Profitability: Stacked comparative bars tracking performance across Credit Card, Debit Card, and Cash.

4. Store Footprint & Geo Analytics
KPI Cards: Total Stores (6), Total Revenue, Total Orders, AOV, and Top Performing Store.

Visuals:

Regional Performance Split: Horizontal bar chart comparing Central vs. West regions ($201.4K vs $53.18K).

Store-wise Revenue & Profit Margin: 100% Stacked column chart analyzing outlet-level margin efficiencies.

Regional Store Share: Donut chart showing store distribution split (33.3% vs 66.7%).

Revenue Contribution by City: Detailed multi-slice donut chart mapping Toronto, Montreal, Vancouver, and Ottawa.

🚀 Key Insights
Total Revenue: $254.58K | Total Profit: $95.61K | Profit Margin: 37.6%

Coffee is the dominant category, generating $131.62K in revenue — more than 2x the next closest category (Sandwich, $45.40K).

Toronto Downtown is the top-performing store at $89K revenue, nearly double the next store.

Returning customers drive the majority of revenue ($164.51K vs. $90.07K from new customers).

Saturday is the highest-revenue day; afternoon (12 PM–3 PM) is the peak ordering window.

Central region (Toronto/Montreal/Ottawa) contributes $201.40K vs. $53.18K from the West (Vancouver/Calgary).

🛠️ Tools & Skills
Python (Pandas): Automated data extraction, cleaning, and dimension table splitting (ETL pipeline).

Power BI Desktop: Data modeling, DAX measures, interactive report design, and custom page navigation.

Power Query: Data transformation and schema mapping.

Excel: Source data structuring.

Dashboard UI/UX design: Custom-branded color styling, high-contrast active button states, and layout architecture.


