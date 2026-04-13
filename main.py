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
# Pydantic Models (Aligned with IA 8 Specs)
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    property_id: int
    name: str # 
    address: str # 
    tenant_name: Optional[str] = None # 

class IncomeCreate(BaseModel):
    amount: float # 
    payment_date: date # 
    description: Optional[str] = None # 

class ExpenseCreate(BaseModel):
    amount: float # 
    expense_date: date # 
    category: str # 
    description: Optional[str] = None # 

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
# BEAUTIFIED FRONTEND (IA 8 Scope)
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
                <button class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg shadow-blue-200 transition-all flex items-center gap-2">
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
                        </div>
                        <div id="incomeList" class="space-y-3"></div>
                    </div>

                    <div>
                        <div class="flex justify-between items-center border-b border-slate-100 pb-3 mb-4">
                            <h3 class="font-bold text-slate-800 flex items-center gap-2">
                                <span class="w-2 h-2 bg-red-500 rounded-full"></span> Expense Records
                            </h3>
                        </div>
                        <div id="expenseList" class="space-y-3"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
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
                        <div class="group bg-white p-8 rounded-3xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-100 transition-all cursor-pointer" onclick="openDrawer(\${p.property_id}, '\${p.name}', '\${p.address}', '\${p.tenant_name || 'No Active Tenant'}')">
                            <div class="flex justify-between items-start mb-6">
                                <div class="bg-blue-50 p-3 rounded-2xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                                </div>
                                <span class="px-3 py-1 bg-slate-100 rounded-full text-[10px] font-black uppercase tracking-wider text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">Details</span>
                            </div>
                            <h3 class="text-2xl font-black text-slate-800 mb-1 group-hover:text-blue-600 transition-colors">\${p.name}</h3>
                            <p class="text-slate-400 font-medium mb-4 text-sm">\${p.address}</p>
                            <div class="flex items-center gap-2 mt-4 pt-4 border-t border-slate-50">
                                <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500">TN</div>
                                <span class="text-xs font-bold text-slate-600">\${p.tenant_name || 'Vacant'}</span>
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error(e);
                }
            }

            async function openDrawer(id, name, address, tenant) {
                document.getElementById('drawer').classList.remove('hidden');
                document.getElementById('drawerTitle').innerText = name;
                document.getElementById('drawerAddress').innerText = address;
                
                try {
                    const [summary, income, expenses] = await Promise.all([
                        fetch(\`/properties/\${id}/summary\`).then(r => r.json()),
                        fetch(\`/income/\${id}\`).then(r => r.json()),
                        fetch(\`/expenses/\${id}\`).then(r => r.json())
                    ]);

                    document.getElementById('drawerSummary').innerHTML = `
                        <div class="p-4 bg-green-50 rounded-2xl border border-green-100">
                            <span class="text-[10px] font-black text-green-600 uppercase tracking-widest">Income</span>
                            <p class="text-2xl font-black text-green-700">$\${summary.total_income}</p>
                        </div>
                        <div class="p-4 bg-red-50 rounded-2xl border border-red-100">
                            <span class="text-[10px] font-black text-red-600 uppercase tracking-widest">Expenses</span>
                            <p class="text-2xl font-black text-red-700">$\${summary.total_expenses}</p>
                        </div>
                    `;

                    document.getElementById('incomeList').innerHTML = income.map(i => `
                        <div class="flex justify-between items-center p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <div><p class="font-bold text-slate-700">Rent Payment</p><p class="text-xs text-slate-400 font-medium">\${i.payment_date}</p></div>
                            <span class="font-black text-green-600">+\$\${i.amount}</span>
                        </div>
                    `).join('') || '<p class="text-slate-400 text-sm italic">No income records found.</p>';

                    document.getElementById('expenseList').innerHTML = expenses.map(e => `
                        <div class="flex justify-between items-center p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <div><p class="font-bold text-slate-700">\${e.category}</p><p class="text-xs text-slate-400 font-medium">\${e.expense_date}</p></div>
                            <span class="font-black text-red-600">-\$\${e.amount}</span>
                        </div>
                    `).join('') || '<p class="text-slate-400 text-sm italic">No expense records found.</p>';

                } catch (e) { console.error(e); }
            }

            function closeDrawer() { document.getElementById('drawer').classList.add('hidden'); }
            loadProperties();
        </script>
    </body>
    </html>
    """

# ---------------------------------------------------------------------------
# Python API Logic (IA 8 Endpoints)
# ---------------------------------------------------------------------------

@app.get("/properties")
def get_all_properties(client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` ORDER BY property_id DESC"
    return [dict(row) for row in client.query(query)]

@app.get("/properties/{property_id}")
def get_property(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.properties` WHERE property_id = {property_id}"
    results = [dict(row) for row in client.query(query)]
    if not results: raise HTTPException(status_code=404, detail="Property not found")
    return results[0]

@app.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(prop: PropertyCreate, client: bigquery.Client = Depends(get_bq_client)):
    query = f"INSERT INTO `{PROJECT_ID}.{DATASET}.properties` (property_id, name, address, tenant_name) VALUES ({prop.property_id}, '{prop.name}', '{prop.address}', '{prop.tenant_name}')"
    client.query(query).result()
    return {"message": "Success"}

@app.get("/income/{property_id}")
def get_property_income(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}"
    return [dict(row) for row in client.query(query)]

@app.get("/expenses/{property_id}")
def get_property_expenses(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}"
    return [dict(row) for row in client.query(query)]

@app.get("/properties/{property_id}/summary")
def get_property_summary(property_id: int, client: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.income` WHERE property_id = {property_id}) as total_income,
            (SELECT COALESCE(SUM(amount), 0) FROM `{PROJECT_ID}.{DATASET}.expenses` WHERE property_id = {property_id}) as total_expenses
    """
    results = [dict(row) for row in client.query(query)]
    if results:
        summary = results[0]
        summary['net_profit'] = summary['total_income'] - summary['total_expenses']
        return summary
    return {"error": "Failed"}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
