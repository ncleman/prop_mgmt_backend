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
# Security: Allow the frontend to talk to the backend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚨 CHANGE THIS LINE to your exact Google Cloud Project ID 🚨
PROJECT_ID = "property-management-app-492514" 
DATASET = "property_mgmt"

# ---------------------------------------------------------------------------
# IA 8 Data Models
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    property_id: int
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
# Database Connection
# ---------------------------------------------------------------------------
def get_bq_client():
    client = bigquery.Client(project=PROJECT_ID)
    try:
        yield client
    finally:
        client.close()

# ---------------------------------------------------------------------------
# IA 10: Professional Frontend UI
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PropManager Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>body { font-family: 'Inter', sans-serif; }</style>
    </head>
    <body class="bg-gray-50 text-gray-900 h-screen flex flex-col overflow-hidden">
        
        <nav class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shrink-0">
            <div class="flex items-center gap-3">
                <div class="bg-blue-600 text-white font-black text-xl w-10 h-10 flex items-center justify-center rounded-lg shadow-md">PM</div>
                <div>
                    <h1 class="text-xl font-extrabold tracking-tight text-gray-900 leading-tight">PropManager</h1>
                    <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Admin Portal</p>
                </div>
            </div>
            <button onclick="location.reload()" class="text-sm font-medium text-gray-500 hover:text-blue-600 transition">Refresh Data</button>
        </nav>

        <div class="flex flex-1 overflow-hidden">
            
            <main class="flex-1 overflow-y-auto p-8 border-r border-gray-200 bg-gray-50">
                <div class="flex justify-between items-end mb-8 max-w-5xl mx-auto">
                    <div>
                        <h2 class="text-3xl font-bold text-gray-900 mb-1">Portfolio</h2>
                        <p class="text-gray-500">Select a property to view financial details.</p>
                    </div>
                    <button onclick="openModal('propModal')" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-5 rounded-lg shadow-sm transition flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                        Add Property
                    </button>
                </div>

                <div id="properties" class="grid grid-cols-1 lg:grid-cols-2 gap-5 max-w-5xl mx-auto">
                    <div class="col-span-full py-12 text-center text-gray-400 animate-pulse font-medium">Loading BigQuery data...</div>
                </div>
            </main>

            <aside id="detailsPanel" class="w-full md:w-[500px] bg-white hidden flex-col shrink-0 overflow-y-auto shadow-2xl md:shadow-none z-10 absolute md:relative inset-y-0 right-0">
                <div class="p-6 border-b border-gray-100 bg-white sticky top-0 z-20 flex justify-between items-start">
                    <div>
                        <p class="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">Financial Overview</p>
                        <h2 id="panelTitle" class="text-2xl font-bold text-gray-900 leading-tight"></h2>
                        <p id="panelAddress" class="text-sm text-gray-500 mt-1"></p>
                    </div>
                    <button onclick="closePanel()" class="md:hidden text-gray-400 hover:text-gray-700">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>

                <div class="p-6 space-y-8 flex-1">
                    <div id="panelSummary" class="grid grid-cols-3 gap-3"></div>

                    <section>
                        <div class="flex justify-between items-center mb-3">
                            <h3 class="font-bold text-gray-900 flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Income</h3>
                            <button onclick="toggleForm('incomeForm')" class="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md hover:bg-emerald-100 transition">+ Add</button>
                        </div>
                        <form id="incomeForm" class="hidden mb-4 bg-emerald-50 p-4 rounded-xl border border-emerald-100 space-y-3">
                            <input type="number" step="0.01" id="incAmount" placeholder="Amount ($)" required class="w-full p-2.5 text-sm border-0 rounded-lg shadow-sm focus:ring-2 focus:ring-emerald-500">
                            <div class="flex gap-3">
                                <input type="date" id="incDate" required class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                                <input type="text" id="incDesc" placeholder="Description" class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                            </div>
                            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded-lg text-sm transition">Save Income</button>
                        </form>
                        <div id="incomeList" class="space-y-2"></div>
                    </section>

                    <section>
                        <div class="flex justify-between items-center mb-3">
                            <h3 class="font-bold text-gray-900 flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-rose-500"></span> Expenses</h3>
                            <button onclick="toggleForm('expenseForm')" class="text-xs font-semibold text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md hover:bg-rose-100 transition">+ Add</button>
                        </div>
                        <form id="expenseForm" class="hidden mb-4 bg-rose-50 p-4 rounded-xl border border-rose-100 space-y-3">
                            <div class="flex gap-3">
                                <input type="number" step="0.01" id="expAmount" placeholder="Amount ($)" required class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                                <input type="text" id="expCat" placeholder="Category" required class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                            </div>
                            <div class="flex gap-3">
                                <input type="date" id="expDate" required class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                                <input type="text" id="expDesc" placeholder="Description" class="w-1/2 p-2.5 text-sm border-0 rounded-lg shadow-sm">
                            </div>
                            <button type="submit" class="w-full bg-rose-600 hover:bg-rose-700 text-white font-medium py-2 rounded-lg text-sm transition">Save Expense</button>
                        </form>
                        <div id="expenseList" class="space-y-2"></div>
                    </section>
                </div>

                <div class="p-6 border-t border-gray-100 bg-gray-50">
                    <button id="delBtn" class="w-full py-2.5 text-sm font-semibold text-rose-600 bg-rose-50 rounded-lg hover:bg-rose-100 transition">Delete Property</button>
                </div>
            </aside>
        </div>

        <div id="propModal" class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm hidden z-50 flex items-center justify-center p-4 transition-opacity">
            <div class="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
                <div class="p-6 border-b border-gray-100 flex justify-between items-center">
                    <h3 class="text-lg font-bold text-gray-900">Add New Property</h3>
                    <button onclick="closeModal('propModal')" class="text-gray-400 hover:text-gray-600">&times;</button>
                </div>
                <form id="propForm" class="p-6 space-y-4 bg-gray-50">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Property ID (Number)</label>
                        <input type="number" id="propId" required class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Property Name</label>
                        <input type="text" id="propName" required class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Address</label>
                        <input type="text" id="propAddress" required class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Tenant Name (Optional)</label>
                        <input type="text" id="propTenant" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div class="pt-4 flex gap-3">
                        <button type="button" onclick="closeModal('propModal')" class="flex-1 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">Cancel</button>
                        <button type="submit" class="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm">Save Property</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            let currentPropId = null;

            // Fetch and render properties
            async function loadProperties() {
                const container = document.getElementById('properties');
                try {
                    const res = await fetch('/properties');
                    if (!res.ok) throw new Error('API Error');
                    const props = await res.json();
                    
                    if (props.length === 0) {
                        container.innerHTML = '<div class="col-span-full py-16 text-center bg-white rounded-2xl border border-gray-200 border-dashed"><p class="text-gray-500 font-medium mb-2">No properties found.</p><p class="text-sm text-gray-400">Add your first property to get started.</p></div>';
                        return;
                    }

                    container.innerHTML = props.map(p => `
                        <div onclick="selectProperty(${p.property_id}, '${p.name}', '${p.address}')" class="group bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300 transition cursor-pointer relative overflow-hidden">
                            <div class="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-0 group-hover:opacity-100 transition"></div>
                            <h3 class="font-bold text-lg text-gray-900 mb-1">${p.name}</h3>
                            <p class="text-gray-500 text-sm mb-4 truncate">${p.address}</p>
                            <div class="flex items-center gap-2">
                                <div class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center"><span class="text-[10px] text-gray-500 font-bold">TN</span></div>
                                <span class="text-xs font-semibold text-gray-600">${p.tenant_name || 'Vacant'}</span>
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    container.innerHTML = `<div class="col-span-full p-6 bg-red-50 text-red-600 rounded-xl border border-red-100 font-medium">Error loading data. Check if your PROJECT_ID is correct in main.py.</div>`;
                }
            }

            // Open right panel and load financial data
            async function selectProperty(id, name, address) {
                currentPropId = id;
                document.getElementById('detailsPanel').style.display = 'flex';
                document.getElementById('panelTitle').innerText = name;
                document.getElementById('panelAddress').innerText = address;
                document.getElementById('delBtn').onclick = () => deleteProperty(id);

                refreshFinancials(id);
            }

            async function refreshFinancials(id) {
                try {
                    const [summary, income, expenses] = await Promise.all([
                        fetch('/properties/' + id + '/summary').then(r => r.json()),
                        fetch('/income/' + id).then(r => r.json()),
                        fetch('/expenses/' + id).then(r => r.json())
                    ]);

                    document.getElementById('panelSummary').innerHTML = `
                        <div class="bg-gray-50 p-4 rounded-xl border border-gray-100"><p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Income</p><p class="text-xl font-black text-emerald-600">$${summary.total_income || 0}</p></div>
                        <div class="bg-gray-50 p-4 rounded-xl border border-gray-100"><p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Expenses</p><p class="text-xl
