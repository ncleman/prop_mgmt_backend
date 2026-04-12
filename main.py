import os
import uvicorn
from datetime import date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from google.cloud import bigquery
from pydantic import BaseModel

app = FastAPI()

# ---------------------------------------------------------------------------
# CORS Setup (Crucial for the frontend to talk to the backend)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = "property-management-app-492514"
DATASET = "property_mgmt"

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class IncomeCreate(BaseModel):
    amount: float
    payment_date: date
    description: Optional[str] = None

class ExpenseCreate(BaseModel):
    amount: float
    expense_date: date
    category: str
    description: Optional[str] = None

class PropertyCreate(BaseModel):
    property_id: int
    name: str
    address: str
    tenant_name: str

class PropertyUpdate(BaseModel):
    name: str
    address: str
    tenant_name: str

# ---------------------------------------------------------------------------
# Dependency: BigQuery client
# ---------------------------------------------------------------------------
def get_bq_client():
    client = bigquery.Client()
    try:
        yield client
    finally:
        client.close()

# ---------------------------------------------------------------------------
# 1. FRONTEND DASHBOARD (The UI)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_items():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Property Management</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-gray-800">Property Dashboard</h1>
            <div id="properties" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <p class="text-gray-500">Loading properties from BigQuery...</p>
            </div>
        </div>

        <script>
            async function loadProps() {
                try {
                    const res = await fetch('/properties');
                    const data = await res.json();
                    const container = document.getElementById('properties');
                    
                    if (data.length === 0) {
                        container.innerHTML = '<p class="text-gray-500">No properties found.</p>';
                        return;
                    }

                    container.innerHTML = data.map(p => `
                        <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-blue-500">
                            <h2 class="font-bold text-xl text-gray-900">${p.name}</h2>
                            <p class="text-gray-600">${p.address}</p>
                            <div class="mt-4 flex justify-between items-center">
                                <span class="text-sm font-semibold text-gray-400">TENANT</span>
                                <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded font-bold">
                                    ${p.tenant_name || 'VACANT'}
                                </span>
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    document.getElementById('properties').innerHTML = '<p class="text-red-500">Error loading data.</p>';
                }
            }
            loadProps();
        </script>
    </body>
    </html>
    """

# ---------------------------------------------------------------------------
# 2. PROPERTY ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/properties")
def get_all_properties(client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` ORDER BY property_id"
    job = client.query(query)
    return [dict(row) for row in job]

@app.get("/properties/{property_id}")
def get_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    job = client.query(query)
    results = [dict(row) for row in job]
    if not results:
        raise HTTPException(status_code=404, detail="Property not found")
    return results[0]

@app.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(prop: PropertyCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.properties` (property_id, name, address, tenant_name)
        VALUES ({prop.property_id}, '{prop.name}', '{prop.address}', '{prop.tenant_name}')
    """
    client.query(query).result()
    return {"message": f"Property {prop.property_id} created!"}

@app.put("/properties/{property_id}")
def update_property(property_id: int, prop: PropertyUpdate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        UPDATE `{PROJECT_ID}.{DATASET}.properties`
        SET name = '{prop.name}', address = '{prop.address}', tenant_name = '{prop.tenant_name}'
        WHERE property_id = {property_id}
    """
    client.query(query).result()
    return {"message": f"Property {property_id} updated!"}

@app.delete("/properties/{property_id}")
def delete_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    client.query(query).result()
    return {"message": f"Property {property_id} deleted!"}

# ---------------------------------------------------------------------------
# 3. INCOME & EXPENSE ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/income/{property_id}")
def get_property_income(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}"
    job = client.query(query)
    return [dict(row) for row in job]

@app.post("/income/{property_id}", status_code=status.HTTP_201_CREATED)
def create_income(property_id: int, income: IncomeCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.income` (income_id, property_id, amount, payment_date, description)
        VALUES (
            (SELECT COALESCE(MAX(income_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.income`),
            {property_id}, {income.amount}, '{income.payment_date}', '{income.description or ""}'
        )
    """
    client.query(query).result()
    return {"message": "Income record created"}

@app.get("/expenses/{property_id}")
def get_property_expenses(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}"
    job = client.query(query)
    return [dict(row) for row in job]

@app.post("/expenses/{property_id}", status_code=status.HTTP_201_CREATED)
def create_expense(property_id: int, expense: ExpenseCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.expenses` (expense_id, property_id, amount, expense_date, category, description)
        VALUES (
            (SELECT COALESCE(MAX(expense_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.expenses`),
            {property_id}, {expense.amount}, '{expense.expense_date}', '{expense.category}', '{expense.description or ""}'
        )
    """
    client.query(query).result()
    return {"message": "Expense record created"}

# ---------------------------------------------------------------------------
# 4. SUMMARY ENDPOINT
# ---------------------------------------------------------------------------
@app.get("/properties/{property_id}/summary")
def get_property_summary(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}) as total_income,
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}) as total_expenses
    """
    job = client.query(query)
    results = [dict(row) for row in job]
    if results:
        summary = results[0]
        summary['net_profit'] = summary['total_income'] - summary['total_expenses']
        return summary
    return {"error": "Calculation failed"}

# ---------------------------------------------------------------------------
# 5. SERVER RUNNER
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
