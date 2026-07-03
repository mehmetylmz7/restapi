const API_BASE_URL = "http://127.0.0.1:5000/api";

// --- Yardımcı: Inline mesaj göster ---
function showMessage(elementId, text, type = 'success') {
    const el = document.getElementById(elementId);
    el.textContent = text;
    el.className = `form-message ${type}`;
    setTimeout(() => {
        el.className = 'form-message';
        el.textContent = '';
    }, 4000);
}

// --- Yardımcı: Status badge class ---
function statusClass(status) {
    if (!status) return '';
    const s = status.toLowerCase();
    if (s === 'succeeded') return 'status-succeeded';
    if (s === 'canceled' || s === 'cancelled') return 'status-canceled';
    return 'status-pending';
}

// Menü Geçişleri
function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(sec => {
        sec.style.display = 'none';
    });
    document.getElementById(sectionId).style.display = 'block';
}

// =====================
// PAGINATİON STATE
// Her kaynak için cursor geçmişi tutulur (geri gidebilmek için)
// =====================
const paginationState = {
    customers: { cursorHistory: [null], currentPage: 0, limit: 10 },
    products:  { cursorHistory: [null], currentPage: 0, limit: 10 },
    payments:  { cursorHistory: [null], currentPage: 0, limit: 10 },
    refunds:   { cursorHistory: [null], currentPage: 0, limit: 10 }
};

function updatePaginationUI(resource, hasMore) {
    const state = paginationState[resource];
    const prevBtn = document.getElementById(`${resource}-prev-btn`);
    const nextBtn = document.getElementById(`${resource}-next-btn`);
    const pageInfo = document.getElementById(`${resource}-page-info`);

    if (prevBtn) prevBtn.disabled = state.currentPage === 0;
    if (nextBtn) nextBtn.disabled = !hasMore;
    if (pageInfo) pageInfo.textContent = `Sayfa ${state.currentPage + 1}`;
}

// Uygulama başladığında dashboard istatistiklerini yükle
document.addEventListener("DOMContentLoaded", () => {
    loadDashboardStats();
});

function loadDashboardStats() {
    fetch(`${API_BASE_URL}/customers`).then(res => res.json()).then(data => {
        document.getElementById('stat-customers').innerText = data && data.data ? data.data.length : 0;
    });
    fetch(`${API_BASE_URL}/payments`).then(res => res.json()).then(data => {
        document.getElementById('stat-payments').innerText = data && data.data ? data.data.length : 0;
    });
    fetch(`${API_BASE_URL}/refunds`).then(res => res.json()).then(data => {
        document.getElementById('stat-refunds').innerText = data && data.data ? data.data.length : 0;
    });
}

// =====================
// MÜŞTERİLER
// =====================
function loadCustomers() {
    const state = paginationState.customers;
    const cursor = state.cursorHistory[state.currentPage];
    let url = `${API_BASE_URL}/customers?limit=${state.limit}`;
    if (cursor) url += `&starting_after=${cursor}`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            const tbody = document.getElementById('customers-tbody');
            tbody.innerHTML = '';

            if (result && result.data) {
                result.data.forEach(customer => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${customer.id}</td>
                            <td>${customer.name || 'Bilinmiyor'}</td>
                            <td>${customer.email || '-'}</td>
                        </tr>
                    `;
                });

                // Bir sonraki sayfa için cursor'ı geçmişe ekle
                if (result.has_more && result.data.length > 0) {
                    const lastId = result.data[result.data.length - 1].id;
                    // Sadece yeni sayfa yükleniyorsa cursor geçmişini güncelle
                    if (state.cursorHistory.length === state.currentPage + 1) {
                        state.cursorHistory.push(lastId);
                    }
                }
            }
            updatePaginationUI('customers', result ? result.has_more : false);
        });
}

function nextPage(resource) {
    const state = paginationState[resource];
    state.currentPage++;
    loadByResource(resource);
}

function prevPage(resource) {
    const state = paginationState[resource];
    if (state.currentPage > 0) {
        state.currentPage--;
        loadByResource(resource);
    }
}

function loadByResource(resource) {
    if (resource === 'customers') loadCustomers();
    else if (resource === 'products') loadProducts();
    else if (resource === 'payments') loadPayments();
    else if (resource === 'refunds') loadRefunds();
}

document.getElementById('add-customer-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('cust-name').value;
    const email = document.getElementById('cust-email').value;

    fetch(`${API_BASE_URL}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email })
    })
    .then(response => {
        if (!response.ok) throw new Error('Sunucu hatası');
        return response.json();
    })
    .then(data => {
        showMessage('customer-msg', `✅ Müşteri eklendi: ${data.id}`);
        document.getElementById('add-customer-form').reset();
        // Sıfırdan yükle (ilk sayfaya dön)
        paginationState.customers = { cursorHistory: [null], currentPage: 0, limit: 10 };
        loadCustomers();
        loadDashboardStats();
    })
    .catch(() => showMessage('customer-msg', '❌ Müşteri eklenirken hata oluştu.', 'error'));
});

// =====================
// ÜRÜNLER
// =====================
function loadProducts() {
    const state = paginationState.products;
    const cursor = state.cursorHistory[state.currentPage];
    let url = `${API_BASE_URL}/products?limit=${state.limit}`;
    if (cursor) url += `&starting_after=${cursor}`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            const tbody = document.getElementById('products-tbody');
            tbody.innerHTML = '';

            if (result && result.data) {
                result.data.forEach(product => {
                    const sc = product.active ? 'status-succeeded' : 'status-canceled';
                    const st = product.active ? 'Aktif' : 'Pasif';
                    tbody.innerHTML += `
                        <tr>
                            <td>${product.id}</td>
                            <td>${product.name}</td>
                            <td>${product.description || '-'}</td>
                            <td><span class="status-badge ${sc}">${st}</span></td>
                        </tr>
                    `;
                });

                if (result.has_more && result.data.length > 0) {
                    const lastId = result.data[result.data.length - 1].id;
                    if (state.cursorHistory.length === state.currentPage + 1) {
                        state.cursorHistory.push(lastId);
                    }
                }
            }
            updatePaginationUI('products', result ? result.has_more : false);
        });
}

document.getElementById('add-product-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('prod-name').value;
    const description = document.getElementById('prod-desc').value;

    fetch(`${API_BASE_URL}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
    })
    .then(response => {
        if (!response.ok) throw new Error('Sunucu hatası');
        return response.json();
    })
    .then(data => {
        showMessage('product-msg', `✅ Ürün eklendi: ${data.id}`);
        document.getElementById('add-product-form').reset();
        paginationState.products = { cursorHistory: [null], currentPage: 0, limit: 10 };
        loadProducts();
    })
    .catch(() => showMessage('product-msg', '❌ Ürün eklenirken hata oluştu.', 'error'));
});

// =====================
// ÖDEMELER
// =====================
function loadPayments() {
    const state = paginationState.payments;
    const cursor = state.cursorHistory[state.currentPage];
    let url = `${API_BASE_URL}/payments?limit=${state.limit}`;
    if (cursor) url += `&starting_after=${cursor}`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            const tbody = document.getElementById('payments-tbody');
            tbody.innerHTML = '';

            if (result && result.data) {
                result.data.forEach(payment => {
                    const amount = (payment.amount / 100).toFixed(2);
                    const sc = statusClass(payment.status);
                    tbody.innerHTML += `
                        <tr>
                            <td>${payment.id}</td>
                            <td>${payment.customer || '-'}</td>
                            <td>${amount}</td>
                            <td>${payment.currency.toUpperCase()}</td>
                            <td><span class="status-badge ${sc}">${payment.status}</span></td>
                        </tr>
                    `;
                });

                if (result.has_more && result.data.length > 0) {
                    const lastId = result.data[result.data.length - 1].id;
                    if (state.cursorHistory.length === state.currentPage + 1) {
                        state.cursorHistory.push(lastId);
                    }
                }
            }
            updatePaginationUI('payments', result ? result.has_more : false);
        });
}

document.getElementById('add-payment-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const customer_id = document.getElementById('pay-customer-id').value.trim();
    const amount      = document.getElementById('pay-amount').value;
    const currency    = document.getElementById('pay-currency').value;
    const order_id    = document.getElementById('pay-order-id').value.trim() || null;

    fetch(`${API_BASE_URL}/payments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id, amount, currency, order_id })
    })
    .then(response => {
        if (!response.ok) throw new Error('Sunucu hatası');
        return response.json();
    })
    .then(data => {
        showMessage('payment-msg', `✅ Ödeme oluşturuldu: ${data.id} — Durum: ${data.status}`);
        document.getElementById('add-payment-form').reset();
        paginationState.payments = { cursorHistory: [null], currentPage: 0, limit: 10 };
        loadPayments();
        loadDashboardStats();
    })
    .catch(() => showMessage('payment-msg', "❌ Ödeme oluşturulurken hata oluştu. Müşteri ID'yi kontrol et.", 'error'));
});

// =====================
// İADELER
// =====================
function loadRefunds() {
    const state = paginationState.refunds;
    const cursor = state.cursorHistory[state.currentPage];
    let url = `${API_BASE_URL}/refunds?limit=${state.limit}`;
    if (cursor) url += `&starting_after=${cursor}`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            const tbody = document.getElementById('refunds-tbody');
            tbody.innerHTML = '';

            if (result && result.data) {
                result.data.forEach(refund => {
                    const amount = (refund.amount / 100).toFixed(2);
                    const sc = statusClass(refund.status);
                    tbody.innerHTML += `
                        <tr>
                            <td>${refund.id}</td>
                            <td>${refund.payment_intent}</td>
                            <td>${amount}</td>
                            <td><span class="status-badge ${sc}">${refund.status}</span></td>
                        </tr>
                    `;
                });

                if (result.has_more && result.data.length > 0) {
                    const lastId = result.data[result.data.length - 1].id;
                    if (state.cursorHistory.length === state.currentPage + 1) {
                        state.cursorHistory.push(lastId);
                    }
                }
            }
            updatePaginationUI('refunds', result ? result.has_more : false);
        });
}