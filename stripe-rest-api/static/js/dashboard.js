const API_BASE_URL = "http://127.0.0.1:5000/api";

// Menü Geçişleri
function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(sec => {
        sec.style.display = 'none';
    });
    document.getElementById(sectionId).style.display = 'block';
}

// Uygulama başladığında dashboard istatistiklerini yükle
document.addEventListener("DOMContentLoaded", () => {
    loadDashboardStats();
});

function loadDashboardStats() {
    fetch(`${API_BASE_URL}/customers`).then(res => res.json()).then(data => {
        document.getElementById('stat-customers').innerText = data ? data.length : 0;
    });
    fetch(`${API_BASE_URL}/payments`).then(res => res.json()).then(data => {
        document.getElementById('stat-payments').innerText = data ? data.length : 0;
    });
    fetch(`${API_BASE_URL}/refunds`).then(res => res.json()).then(data => {
        document.getElementById('stat-refunds').innerText = data ? data.length : 0;
    });
}

// Müşterileri Getir
function loadCustomers() {
    fetch(`${API_BASE_URL}/customers`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('customers-tbody');
            tbody.innerHTML = '';
            if (data) {
                data.forEach(customer => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${customer.id}</td>
                            <td>${customer.name || 'Bilinmiyor'}</td>
                            <td>${customer.email || '-'}</td>
                        </tr>
                    `;
                });
            }
        });
}

// Müşteri Ekleme Formu Dinleyicisi
document.getElementById('add-customer-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('cust-name').value;
    const email = document.getElementById('cust-email').value;

    fetch(`${API_BASE_URL}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, email: email })
    })
    .then(response => response.json())
    .then(() => {
        alert("Müşteri başarıyla eklendi!");
        document.getElementById('add-customer-form').reset();
        loadCustomers(); // Tabloyu yenile
        loadDashboardStats(); // İstatistikleri yenile
    })
    .catch(err => console.error("Hata:", err));
});

// Ürünleri Getir
function loadProducts() {
    fetch(`${API_BASE_URL}/products`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('products-tbody');
            tbody.innerHTML = '';
            if(data) {
                data.forEach(product => {
                    const statusClass = product.active ? 'status-succeeded' : 'status-pending';
                    const statusText = product.active ? 'Aktif' : 'Pasif';
                    tbody.innerHTML += `
                        <tr>
                            <td>${product.id}</td>
                            <td>${product.name}</td>
                            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                        </tr>
                    `;
                });
            }
        });
}

// Ödemeleri Getir
function loadPayments() {
    fetch(`${API_BASE_URL}/payments`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('payments-tbody');
            tbody.innerHTML = '';
            if(data) {
                data.forEach(payment => {
                    const amount = (payment.amount / 100).toFixed(2);
                    const statusClass = payment.status === 'succeeded' ? 'status-succeeded' : 'status-pending';
                    tbody.innerHTML += `
                        <tr>
                            <td>${payment.id}</td>
                            <td>${amount}</td>
                            <td>${payment.currency.toUpperCase()}</td>
                            <td><span class="status-badge ${statusClass}">${payment.status}</span></td>
                        </tr>
                    `;
                });
            }
        });
}

// İadeleri Getir
function loadRefunds() {
    fetch(`${API_BASE_URL}/refunds`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('refunds-tbody');
            tbody.innerHTML = '';
            if(data) {
                data.forEach(refund => {
                    const amount = (refund.amount / 100).toFixed(2);
                    const statusClass = refund.status === 'succeeded' ? 'status-succeeded' : 'status-pending';
                    tbody.innerHTML += `
                        <tr>
                            <td>${refund.id}</td>
                            <td>${refund.payment_intent}</td>
                            <td>${amount}</td>
                            <td><span class="status-badge ${statusClass}">${refund.status}</span></td>
                        </tr>
                    `;
                });
            }
        });
}