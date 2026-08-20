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


