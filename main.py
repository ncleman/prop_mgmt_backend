from fastapi import FastAPI, Depends, HTTPException, status
from google.cloud import bigquery

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This tells the guard to let everyone in for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = "property-management-app-492514"
DATASET = "property_mgmt"


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
# Properties
# ---------------------------------------------------------------------------

@app.get("/properties")
def get_properties(bq: bigquery.Client = Depends(get_bq_client)):
    """
    Returns all properties in the database.
    """
    query = f"""
        SELECT
            property_id,
            name,
            address,
            city,
            state,
            postal_code,
            property_type,
            tenant_name,
            monthly_rent
        FROM `{PROJECT_ID}.{DATASET}.properties`
        ORDER BY property_id
    """

    try:
        results = bq.query(query).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

    properties = [dict(row) for row in results]
    return properties

from fastapi import FastAPI, Depends, HTTPException, status
from google.cloud import bigquery
from pydantic import BaseModel
from typing import Optional
from datetime import date

# Add these below your app and BQ client setup
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

# ==========================================
# REQUIRED BASE ENDPOINTS
# ==========================================

# 1. GET all properties
@app.get("/properties")
def get_all_properties(client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties`"
    job = client.query(query)
    return [dict(row) for row in job]

# 2. GET a single property by ID
@app.get("/properties/{property_id}")
def get_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    job = client.query(query)
    results = [dict(row) for row in job]
    
    if not results:
        raise HTTPException(status_code=404, detail="Property not found")
    return results[0]

# 3. GET all income for a property
@app.get("/income/{property_id}")
def get_property_income(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}"
    job = client.query(query)
    return [dict(row) for row in job]

# 4. POST a new income record for a property
@app.post("/income/{property_id}", status_code=status.HTTP_201_CREATED)
def create_income(property_id: int, income: IncomeCreate, client: bigquery.Client = Depends(get_bq_client)):
    # This query automatically finds the highest income_id and adds 1 to create a new unique ID
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.income` (income_id, property_id, amount, payment_date, description)
        VALUES (
            (SELECT COALESCE(MAX(income_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.income`),
            {property_id}, {income.amount}, '{income.payment_date}', '{income.description or ""}'
        )
    """
    job = client.query(query)
    job.result()
    return {"message": "Income record successfully created"}

# 5. GET all expenses for a property
@app.get("/expenses/{property_id}")
def get_property_expenses(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}"
    job = client.query(query)
    return [dict(row) for row in job]

# 6. POST a new expense record for a property
@app.post("/expenses/{property_id}", status_code=status.HTTP_201_CREATED)
def create_expense(property_id: int, expense: ExpenseCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.expenses` (expense_id, property_id, amount, expense_date, category, description)
        VALUES (
            (SELECT COALESCE(MAX(expense_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.expenses`),
            {property_id}, {expense.amount}, '{expense.expense_date}', '{expense.category}', '{expense.description or ""}'
        )
    """
    job = client.query(query)
    job.result()
    return {"message": "Expense record successfully created"}
# -------------------------------------------------------------
# ADDITIONAL ENDPOINT 1: Create a new property
# -------------------------------------------------------------
@app.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(prop: PropertyCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.properties` (property_id, name, address, tenant_name)
        VALUES ({prop.property_id}, '{prop.name}', '{prop.address}', '{prop.tenant_name}')
    """
    job = client.query(query)
    job.result() # Waits for the query to finish executing
    return {"message": f"Property {prop.property_id} successfully created!"}

# -------------------------------------------------------------
# ADDITIONAL ENDPOINT 2: Update an existing property
# -------------------------------------------------------------
@app.put("/properties/{property_id}")
def update_property(property_id: int, prop: PropertyUpdate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        UPDATE `{PROJECT_ID}.{DATASET}.properties`
        SET name = '{prop.name}', address = '{prop.address}', tenant_name = '{prop.tenant_name}'
        WHERE property_id = {property_id}
    """
    job = client.query(query)
    job.result()
    return {"message": f"Property {property_id} successfully updated!"}

# -------------------------------------------------------------
# ADDITIONAL ENDPOINT 3: Delete a property
# -------------------------------------------------------------
@app.delete("/properties/{property_id}")
def delete_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        DELETE FROM `{PROJECT_ID}.{DATASET}.properties`
        WHERE property_id = {property_id}
    """
    job = client.query(query)
    job.result()
    return {"message": f"Property {property_id} successfully deleted!"}

# -------------------------------------------------------------
# ADDITIONAL ENDPOINT 4: Get a financial summary for a property
# -------------------------------------------------------------
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
        # Calculate the net profit based on the two sums!
        summary['net_profit'] = summary['total_income'] - summary['total_expenses']
        return summary
    else:
        return {"error": "Property not found or calculation failed."}

import os
import uvicorn

# ... (all your other code stays the same) ...

if __name__ == "__main__":
    # Grab the port from the environment, or default to 8080
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
