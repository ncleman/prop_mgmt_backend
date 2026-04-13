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
# CORS & Configuration
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
# Pydantic Models (From your working code)
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    property_id: int
    name: str 
    address: str 
    tenant_name: str 

class IncomeCreate(BaseModel):
    amount: float 
    payment_date: date 
    description: Optional[str] = None 

class ExpenseCreate(BaseModel):
    amount: float 
    expense_date: date 
    category: str 
    description: Optional[str] = None 

class PropertyUpdate(BaseModel):
    name: str
    address: str
    tenant_name: str

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
# BEAUTIFIED FRONTEND (IA 10)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>PropManager | Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
        <style>body { font-family: 'Inter', sans-serif; }</style>
    </head>
    <body class="bg-[#f8fafc] text-[#1e293b]">
        <nav class="bg-white border-b border-slate-200 px-8 py-4 sticky top-0 z-10">
            <div class="max-w-6xl mx-auto flex justify-between items-center">
                <div class="flex items-center gap-2">
                    <div class="bg-blue-600 p-2 rounded-lg text-white font-black">PM</div>
                    <span class="text-xl font-extrabold tracking-tight text-slate-800">PropManager</span>
                </div>
                <div class="flex gap-4">
                    <button onclick="location.reload()" class="text-sm font-semibold text-slate-500 hover:text-blue-600 transition">Refresh Dashboard</button>
                </div>
            </div>
        </nav>

        <main class="max-w-6xl mx-auto p-8">
            <div class="flex justify-between items-end mb-10">
                <div>
                    <h1 class="text-4xl font-extrabold text-slate-900 mb-2">Portfolio Overview</h1>
                    <p class="text-slate-500 font-medium">Manage properties, income, and expenses in real-time.</p>
                </div>
                <button onclick="openPropertyModal()" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg shadow-blue-200 transition-all flex items-center gap-2">
                    <span>+</span> Add Property
                </button>
            </div>

            <div id="properties" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                <div class="col-span-full py-20 text-center text-slate-400 animate-pulse font-medium">
                    Loading your BigQuery data...
                </div>
            </div>
        </main>

        <div id="drawer" class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm hidden z-20 transition-opacity">
            <div class="absolute right-0 top-0 bottom-0 w-full max-w-xl bg-white shadow-2xl p-0 flex flex-col">
                <div class="p-8 border-b border-slate-100 flex justify-between items-start bg-slate-50">
                    <div>
                        <span class="text-xs font-bold text-blue-600 uppercase tracking-widest mb-1 block">Property Details</span>
                        <h2 id="drawerTitle" class="text-3xl font-black text-slate-800"></h2>
                        <p id="drawerAddress" class="text-slate-500 font-medium"></p>
                    </div>
                    <button onclick="closeDrawer()" class="text-slate-400 hover:text-slate-600 text-3xl font-light">&times;</button>
                </div>
                
                <div class="flex-1 overflow-y-auto p-8 space-y-10">
                    <div id="drawerSummary" class="grid grid-cols-2 gap-4"></div>

                    <div>
                        <div class="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
                            <h3 class="font-bold text-slate-800 flex items-center gap-2">
                                <span class="w-2 h-2 bg-green-500 rounded-full"></span> Income Records
                            </h3>
                            <button onclick="toggleForm('incomeForm')" class="text-xs bg-green-50 text-green-700 px-3 py-1.5 rounded-lg font-bold hover:bg-green-100">+ Add Rent</button>
                        </div>
                        <form id="incomeForm" class="hidden mb-4 p-4 bg-green-50 rounded-xl space-y-3 border border-green-100">
                            <input type="number" step="0.01" id="incAmount" placeholder="Amount ($)" required class="w-full p-2.5 border-0 rounded-lg shadow-sm text-sm">
                            <div class="flex gap-2">
                                <input type="date" id="incDate" required class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                                <input type="text" id="incDesc" placeholder="Description" class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                            </div>
                            <button type="submit" class="w-full bg-green-600 text-white font-bold py-2.5 rounded-lg text-sm shadow-sm">Save Income</button>
                        </form>
                        <div id="incomeList" class="space-y-3"></div>
                    </div>

                    <div>
                        <div class="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
                            <h3 class="font-bold text-slate-800 flex items-center gap-2">
                                <span class="w-2 h-2 bg-red-500 rounded-full"></span> Expense Records
                            </h3>
                            <button onclick="toggleForm('expenseForm')" class="text-xs bg-red-50 text-red-700 px-3 py-1.5 rounded-lg font-bold hover:bg-red-100">+ Add Expense</button>
                        </div>
                        <form id="expenseForm" class="hidden mb-4 p-4 bg-red-50 rounded-xl space-y-3 border border-red-100">
                            <div class="flex gap-2">
                                <input type="number" step="0.01" id="expAmount" placeholder="Amount ($)" required class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                                <input type="text" id="expCat" placeholder="Category" required class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                            </div>
                            <div class="flex gap-2">
                                <input type="date" id="expDate" required class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                                <input type="text" id="expDesc" placeholder="Description" class="w-1/2 p-2.5 border-0 rounded-lg shadow-sm text-sm">
                            </div>
                            <button type="submit" class="w-full bg-red-600 text-white font-bold py-2.5 rounded-lg text-sm shadow-sm">Save Expense</button>
                        </form>
                        <div id="expenseList" class="space-y-3"></div>
                    </div>
                    
                    <div class="pt-6 border-t border-slate-100 mt-10">
                        <button id="delBtn" class="w-full py-3 text-sm font-bold text-red-500 bg-red-50 rounded-xl hover:bg-red-100 transition">Delete Property Record</button>
                    </div>
                </div>
            </div>
        </div>

        <div id="propModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm hidden z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
                <div class="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                    <h3 class="text-xl font-black text-slate-800">Add New Property</h3>
                    <button onclick="closePropertyModal()" class="text-slate-400 hover:text-slate-600 text-2xl">&times;</button>
                </div>
                <form id="propForm" class="p-8 space-y-5">
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Property ID (Number)</label>
                        <input type="number" id="propId" required class="w-full p-3 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white outline-none focus:ring-2 focus:ring-blue-500 transition">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Property Name</label>
                        <input type="text" id="propName" required class="w-full p-3 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white outline-none focus:ring-2 focus:ring-blue-500 transition">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Address</label>
                        <input type="text" id="propAddress" required class="w-full p-3 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white outline-none focus:ring-2 focus:ring-blue-500 transition">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Tenant Name</label>
                        <input type="text" id="propTenant" required class="w-full p-3 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white outline-none focus:ring-2 focus:ring-blue-500 transition">
                    </div>
                    <div class="flex gap-3 pt-4">
                        <button type="button" onclick="closePropertyModal()" class="flex-1 py-3 text-slate-500 font-bold bg-slate-100 hover:bg-slate-200 rounded-xl transition">Cancel</button>
                        <button type="submit" class="flex-1 py-3 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition">Save</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            let currentPropId = null;

            async function loadProperties() {
                try {
                    const res = await fetch('/properties');
                    const props = await res.json();
                    const container = document.getElementById('properties');
                    
                    if (props.length === 0) {
                        container.innerHTML = `<div class="col-span-full p-20 text-center bg-white rounded-3xl border border-slate-200 text-slate-400 font-medium">No properties found.</div>`;
                        return;
                    }

                    container.innerHTML = props.map(p => `
                        <div class="group bg-white p-8 rounded-3xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-100 transition-all cursor-pointer" onclick="openDrawer(${p.property_id}, '${p.name}', '${p.address}')">
                            <div class="flex justify-between items-start mb-6">
                                <div class="bg-blue-50 p-3 rounded-2xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                                </div>
                                <span class="px-3 py-1 bg-slate-100 rounded-full text-[10px] font-black uppercase tracking-wider text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">Details</span>
                            </div>
                            <h3 class="text-2xl font-black text-slate-800 mb-1 group-hover:text-blue-600 transition-colors">${p.name}</h3>
                            <p class="text-slate-400 font-medium mb-4 text-sm">${p.address}</p>
                            <div class="flex items-center gap-2 mt-4 pt-4 border-t border-slate-50">
                                <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500">TN</div>
                                <span class="text-xs font-bold text-slate-600">${p.tenant_name || 'Vacant'}</span>
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error(e);
                }
            }

            async function openDrawer(id, name, address) {
                currentPropId = id;
                document.getElementById('drawer').classList.remove('hidden');
                document.getElementById('drawerTitle').innerText = name;
                document.getElementById('drawerAddress').innerText = address;
                document.getElementById('delBtn').onclick = () => deleteProperty(id);
                
                try {
                    const [summary, income, expenses] = await Promise.all([
                        fetch('/properties/' + id + '/summary').then(r => r.json()),
                        fetch('/income/' + id).then(r => r.json()),
                        fetch('/expenses/' + id).then(r => r.json())
                    ]);

                    document.getElementById('drawerSummary').innerHTML = `
                        <div class="p-4 bg-green-50 rounded-2xl border border-green-100">
                            <span class="text-[10px] font-black text-green-600 uppercase tracking-widest">Income</span>
                            <p class="text-2xl font-black text-green-700">$${summary.total_income || 0}</p>
                        </div>
                        <div class="p-4 bg-red-50 rounded-2xl border border-red-100">
                            <span class="text-[10px] font-black text-red-600 uppercase tracking-widest">Expenses</span>
                            <p class="text-2xl font-black text-red-700">$${summary.total_expenses || 0}</p>
                        </div>
                        <div class="col-span-2 p-4 bg-blue-50 rounded-2xl border border-blue-100 flex justify-between items-center">
                            <span class="text-xs font-black text-blue-500 uppercase tracking-widest">Net Profit</span>
                            <p class="text-2xl font-black text-blue-700">$${(summary.net_profit || 0).toFixed(2)}</p>
                        </div>
                    `;

                    document.getElementById('incomeList').innerHTML = income.map(i => `
                        <div class="flex justify-between items-center p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <div><p class="font-bold text-slate-700">Rent Payment</p><p class="text-xs text-slate-400 font-medium">${i.payment_date}</p></div>
                            <span class="font-black text-green-600">+$${i.amount}</span>
                        </div>
                    `).join('') || '<p class="text-slate-400 text-sm italic">No income records found.</p>';

                    document.getElementById('expenseList').innerHTML = expenses.map(e => `
                        <div class="flex justify-between items-center p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <div><p class="font-bold text-slate-700">${e.category}</p><p class="text-xs text-slate-400 font-medium">${e.expense_date}</p></div>
                            <span class="font-black text-red-600">-$${e.amount}</span>
                        </div>
                    `).join('') || '<p class="text-slate-400 text-sm italic">No expense records found.</p>';

                } catch (e) { console.error(e); }
            }

            // Form Submissions
            document.getElementById('propForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = {
                    property_id: parseInt(document.getElementById('propId').value),
                    name: document.getElementById('propName').value,
                    address: document.getElementById('propAddress').value,
                    tenant_name: document.getElementById('propTenant').value
                };
                const res = await fetch('/properties', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
                if (res.ok) { closePropertyModal(); loadProperties(); } else { alert("Make sure Property ID is unique!"); }
            };

            document.getElementById('incomeForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = { amount: parseFloat(document.getElementById('incAmount').value), payment_date: document.getElementById('incDate').value, description: document.getElementById('incDesc').value };
                await fetch('/income/' + currentPropId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
                toggleForm('incomeForm'); openDrawer(currentPropId, document.getElementById('drawerTitle').innerText, document.getElementById('drawerAddress').innerText);
            };

            document.getElementById('expenseForm').onsubmit = async (e) => {
                e.preventDefault();
                const body = { amount: parseFloat(document.getElementById('expAmount').value), expense_date: document.getElementById('expDate').value, category: document.getElementById('expCat').value, description: document.getElementById('expDesc').value };
                await fetch('/expenses/' + currentPropId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
                toggleForm('expenseForm'); openDrawer(currentPropId, document.getElementById('drawerTitle').innerText, document.getElementById('drawerAddress').innerText);
            };

            async function deleteProperty(id) {
                if (confirm("Are you sure? This will delete the property record.")) {
                    await fetch('/properties/' + id, { method: 'DELETE' });
                    closeDrawer(); loadProperties();
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
# Python API Logic (From your working code!)
# ---------------------------------------------------------------------------

@app.get("/properties")
def get_all_properties(client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` ORDER BY property_id DESC"
    job = client.query(query)
    return [dict(row) for row in job]

@app.get("/properties/{property_id}")
def get_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    job = client.query(query)
    results = [dict(row) for row in job]
    if not results: raise HTTPException(status_code=404, detail="Property not found")
    return results[0]

@app.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(prop: PropertyCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"INSERT INTO `{PROJECT_ID}.{DATASET}.properties` (property_id, name, address, tenant_name) VALUES ({prop.property_id}, '{prop.name}', '{prop.address}', '{prop.tenant_name}')"
    client.query(query).result()
    return {"message": "Success"}

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
    return {"message": "Success"}

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
    return {"error": "Failed"}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
