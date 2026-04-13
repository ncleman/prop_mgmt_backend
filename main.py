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
# CORS Setup
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
# IA 8 Models [cite: 143, 145, 146]
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    property_id: int
    name: str
    address: str
    tenant_name: Optional[str] = None

class PropertyUpdate(BaseModel):
    name: str
    address: str
    tenant_name: Optional[str] = None

class IncomeCreate(BaseModel):
    amount: float
    payment_date: date
    description: Optional[str] = None

class ExpenseCreate(BaseModel):
    amount: float
    expense_date: date
    category: str
    description: Optional[str] = None

# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
def get_bq_client():
    client = bigquery.Client()
    try:
        yield client
    finally:
        client.close()

# ---------------------------------------------------------------------------
# IA 10 BEAUTIFIED FRONTEND [cite: 83, 117]
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>PropManager MVP</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
        <style>body { font-family: 'Inter', sans-serif; }</style>
    </head>
    <body class="bg-slate-50 text-slate-900">
        <nav class="bg-blue-700 text-white p-6 shadow-md mb-8">
            <div class="max-w-6xl mx-auto flex justify-between items-center">
                <h1 class="text-2xl font-extrabold tracking-tight">PropManager <span class="font-normal opacity-75">MVP</span></h1>
            </div>
        </nav>

        <main class="max-w-6xl mx-auto px-6 pb-20">
            <div class="flex justify-between items-center mb-8">
                <h2 class="text-3xl font-bold">Properties</h2>
                <button onclick="openPropertyModal()" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg shadow-sm transition">
                    + Add Property
                </button>
            </div>

            <div id="properties" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <p class="text-slate-500 animate-pulse">Loading data...</p>
            </div>
        </main>

        <div id="propModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm hidden flex items-center justify-center p-4 z-20">
            <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-8">
                <h3 id="modalTitle" class="text-2xl font-bold mb-6 text-slate-800 underline decoration-blue-500">Add Property</h3>
                <form id="propForm" class="space-y-4">
                    <input type="hidden" id="editId">
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-400 mb-1">Property ID</label>
                        <input type="number" id="propId" required class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-400 mb-1">Property Name</label>
                        <input type="text" id="propName" required class="w-full p-3 border rounded-lg">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-400 mb-1">Address</label>
                        <input type="text" id="propAddress" required class="w-full p-3 border rounded-lg">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-400 mb-1">Tenant Name</label>
                        <input type="text" id="propTenant" class="w-full p-3 border rounded-lg">
                    </div>
                    <div class="flex gap-3 pt-4">
                        <button type="button" onclick="closePropertyModal()" class="flex-1 py-3 text-slate-500 font-bold hover:bg-slate-100 rounded-lg">Cancel</button>
                        <button type="submit" class="flex-1 py-3 bg-blue-600 text-white font-bold rounded-lg shadow-blue-200">Save</button>
                    </div>
                </form>
            </div>
        </div>

        <div id="drawer" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm hidden z-30">
            <div class="absolute right-0 top-0 bottom-0 w-full max-w-lg bg-white shadow-2xl overflow-y-auto p-8">
                <div class="flex justify-between items-center mb-8">
                    <h2 id="drawerTitle" class="text-3xl font-black text-slate-800"></h2>
                    <button onclick="closeDrawer()" class="text-3xl text-slate-300 hover:text-slate-600">&times;</button>
                </div>

                <div id="drawerSummary" class="grid grid-cols-3 gap-3 mb-10"></div>

                <div class="mb-10">
                    <div class="flex justify-between items-center mb-4 border-b pb-2">
                        <h4 class="font-bold text-green-600">Income Records</h4>
                        <button onclick="toggleForm('incomeForm')" class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded font-bold">+ Record Rent</button>
                    </div>
                    <form id="incomeForm" class="hidden mb-4 p-4 bg-green-50 rounded-lg space-y-3">
                        <input type="number" step="0.01" id="incAmount" placeholder="Amount" required class="w-full p-2 border rounded">
                        <input type="date" id="incDate" required class="w-full p-2 border rounded">
                        <input type="text" id="incDesc" placeholder="Description" class="w-full p-2 border rounded">
                        <button type="submit" class="w-full bg-green-600 text-white font-bold py-2 rounded">Save Income</button>
                    </form>
                    <div id="incomeList" class="space-y-2 text-sm"></div>
                </div>

                <div>
                    <div class="flex justify-between items-center mb-4 border-b pb-2">
                        <h4 class="font-bold text-red-600">Expense Records</h4>
                        <button onclick="toggleForm('expenseForm')" class="text-xs bg-red-50 text-red-700 px-2 py-1 rounded font-bold">+ Record Cost</button>
                    </div>
                    <form id="expenseForm" class="hidden mb-4 p-4 bg-red-50 rounded-lg space-y-3">
                        <input type="number" step="0.01" id="expAmount" placeholder="Amount" required class="w-full p-2 border rounded">
                        <input type="date" id="expDate" required class="w-full p-2 border rounded">
                        <input type="text" id="expCat" placeholder="Category (e.g. Repairs)" required class="w-full p-2 border rounded">
                        <input type="text" id="expDesc" placeholder="Description" class="w-full p-2 border rounded">
                        <button type="submit" class="w-full bg-red-600 text-white font-bold py-2 rounded">Save Expense</button>
                    </form>
                    <div id="expenseList" class="space-y-2 text-sm"></div>
                </div>
                
                <div class="mt-12 pt-8 border-t">
                    <button id="delBtn" class="w-full text-red-400 hover:text-red-600 font-bold text-sm py-2">Delete This Property</button>
                </div>
            </div>
        </div>

        <script>
            let currentPropId = null;

            async function loadProperties() {
                const res = await fetch('/properties');
                const props = await res.json();
                const container = document.getElementById('properties');
                
                if (props.length === 0) {
                    container.innerHTML = '<div class="col-span-full p-12 text-center bg-white rounded-xl border border-dashed text-slate-400">No properties found.</div>';
                    return;
                }

                container.innerHTML = props.map(p => `
                    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 hover:shadow-lg transition cursor-pointer" onclick="openDrawer(\${p.property_id}, '\${p.name}', '\${p.address}')">
                        <h3 class="font-bold text-xl text-blue-800 mb-1">\${p.name}</h3>
                        <p class="text-slate-400 text-sm mb-4 font-medium">\${p.address}</p>
                        <div class="flex justify-between items-center pt-4 border-t">
                            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest">Tenant: \${p.tenant_name || 'Vacant'}</span>
                            <span class="text-blue-500 font-bold text-xs hover:underline">Manage &rarr;</span>
                        </div>
                    </div>
                `).join('');
            }

            // [cite: 70, 72, 75]
            async function openDrawer(id, name, address) {
                currentPropId = id;
                document.getElementById('drawer').classList.remove('hidden');
                document.getElementById('drawerTitle').innerText = name;
                
                // Set up Delete button [cite: 69]
                document.getElementById('delBtn').onclick = () => deleteProperty(id);

                refreshDrawerData(id);
            }

            async function refreshDrawerData(id) {
                const [summary, income, expenses] = await Promise.all([
                    fetch(\`/properties/\${id}/summary\`).then(r => r.json()),
                    fetch(\`/income/\${id}\`).then(r => r.json()),
                    fetch(\`/expenses/\${id}\`).then(r => r.json())
                ]);

                document.getElementById('drawerSummary').innerHTML = `
                    <div class="p-3 bg-green-50 rounded-lg text-center"><p class="text-[10px] font-bold text-green-600 uppercase">In</p><p class="font-black text-green-700">$\${summary.total_income}</p></div>
                    <div class="p-3 bg-red-50 rounded-lg text-center"><p class="text-[10px] font-bold text-red-600 uppercase">Out</p><p class="font-black text-red-700">$\${summary.total_expenses}</p></div>
                    <div class="p-3 bg-blue-50 rounded-lg text-center"><p class="text-[10px] font-bold text-blue-600 uppercase">Net</p><p class="font-black text-blue-700">$\${summary.net_profit}</p></div>
                `;

                document.getElementById('incomeList').innerHTML = income.map(i => `
                    <div class="flex justify-between p-3 bg-slate-50 rounded border border-slate-100">
                        <div><p class="font-bold">$\${i.amount}</p><p class="text-[10px] text-slate-400 uppercase">\${i.payment_date}</p></div>
                        <p class="text-[10px] text-slate-400 italic font-medium">\${i.description || ''}</p>
                    </div>
                `).join('') || '<p class="text-slate-300 italic py-4">No income records.</p>';

                document.getElementById('expenseList').innerHTML = expenses.map(e => `
                    <div class="flex justify-between p-3 bg-slate-50 rounded border border-slate-100">
                        <div><p class="font-bold">$\${e.amount}</p><p class="text-[10px] text-red-400 uppercase font-black">\${e.category}</p></div>
                        <div class="text-right"><p class="text-[10px] text-slate-400 uppercase">\${e.expense_date}</p><p class="text-[10px] text-slate-400 italic">\${e.description || ''}</p></div>
                    </div>
                `).join('') || '<p class="text-slate-300 italic py-4">No expense records.</p>';
            }

            // [cite: 68]
            document.getElementById('propForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = {
                    property_id: parseInt(document.getElementById('propId').value),
                    name: document.getElementById('propName').value,
                    address: document.getElementById('propAddress').value,
                    tenant_name: document.getElementById('propTenant').value
                };
                const res = await fetch('/properties', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                if (res.ok) { closePropertyModal(); loadProperties(); }
                else { alert("Error: Make sure the Property ID is unique!"); }
            };

            // [cite: 71]
            document.getElementById('incomeForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = {
                    amount: parseFloat(document.getElementById('incAmount').value),
                    payment_date: document.getElementById('incDate').value,
                    description: document.getElementById('incDesc').value
                };
                await fetch(\`/income/\${currentPropId}\`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                toggleForm('incomeForm');
                refreshDrawerData(currentPropId);
            };

            // [cite: 73]
            document.getElementById('expenseForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = {
                    amount: parseFloat(document.getElementById('expAmount').value),
                    expense_date: document.getElementById('expDate').value,
                    category: document.getElementById('expCat').value,
                    description: document.getElementById('expDesc').value
                };
                await fetch(\`/expenses/\${currentPropId}\`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                toggleForm('expenseForm');
                refreshDrawerData(currentPropId);
            };

            // [cite: 69]
            async function deleteProperty(id) {
                if (confirm("Are you sure? This will delete the property record.")) {
                    await fetch(\`/properties/\${id}\`, { method: 'DELETE' });
                    closeDrawer();
                    loadProperties();
                }
            }

            function openPropertyModal() { document.getElementById('propModal').classList.remove('hidden'); }
            function closePropertyModal() { document.getElementById('propModal').classList.add('hidden'); document.getElementById('propForm').reset(); }
            function closeDrawer() { document.getElementById('drawer').classList.add('hidden'); }
            function toggleForm(id) { document.getElementById(id).classList.toggle('hidden'); }

            loadProperties();
        </script>
    </body>
    </html>
    """

# ---------------------------------------------------------------------------
# API LOGIC (IA 8 Endpoints) [cite: 150]
# ---------------------------------------------------------------------------
@app.get("/properties")
def get_all_properties(client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` ORDER BY property_id DESC"
    return [dict(row) for row in client.query(query)]

@app.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(prop: PropertyCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.properties` (property_id, name, address, tenant_name)
        VALUES ({prop.property_id}, '{prop.name}', '{prop.address}', '{prop.tenant_name}')
    """
    client.query(query).result()
    return {"message": "Created"}

@app.delete("/properties/{property_id}")
def delete_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    client.query(query).result()
    return {"message": "Deleted"}

@app.get("/income/{property_id}")
def get_property_income(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id} ORDER BY payment_date DESC"
    return [dict(row) for row in client.query(query)]

@app.post("/income/{property_id}")
def create_income(property_id: int, income: IncomeCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.income` (income_id, property_id, amount, payment_date, description)
        VALUES ((SELECT COALESCE(MAX(income_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.income`), {property_id}, {income.amount}, '{income.payment_date}', '{income.description or ""}')
    """
    client.query(query).result()
    return {"message": "Success"}

@app.get("/expenses/{property_id}")
def get_property_expenses(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id} ORDER BY expense_date DESC"
    return [dict(row) for row in client.query(query)]

@app.post("/expenses/{property_id}")
def create_expense(property_id: int, expense: ExpenseCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.expenses` (expense_id, property_id, amount, expense_date, category, description)
        VALUES ((SELECT COALESCE(MAX(expense_id), 0) + 1 FROM `{PROJECT_ID}.{DATASET}.expenses`), {property_id}, {expense.amount}, '{expense.expense_date}', '{expense.category}', '{expense.description or ""}')
    """
    client.query(query).result()
    return {"message": "Success"}

@app.get("/properties/{property_id}/summary")
def get_property_summary(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}) as total_income,
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}) as total_expenses
    """
    results = [dict(row) for row in client.query(query)]
    summary = results[0]
    summary['net_profit'] = summary['total_income'] - summary['total_expenses']
    return summary

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
