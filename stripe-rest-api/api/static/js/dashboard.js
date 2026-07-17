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
    fetch(`${API_BASE_URL}/stats`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('stat-customers').innerText = data.customers || 0;
            document.getElementById('stat-payments').innerText = data.payments || 0;
            document.getElementById('stat-products').innerText = data.products || 0;
            document.getElementById('stat-refunds').innerText = data.refunds || 0;
        })
        .catch(err => console.error("Stats fetch error:", err));
}

// =====================
// MÜŞTERİLER
// =====================
function loadCustomers() {
    const state = paginationState.customers;
    const cursor = state.cursorHistory[state.currentPage];
    let url = `${API_BASE_URL}/customers?limit=${state.limit}`;
    if (cursor) url += `&starting_after=${cursor}`;

    const startDate = document.getElementById('cust-filter-start').value;
    const endDate = document.getElementById('cust-filter-end').value;

    if (startDate) {
        const startTimestamp = Math.floor(new Date(startDate).getTime() / 1000);
        url += `&created_gte=${startTimestamp}`;
    }
    if (endDate) {
        const endTimestamp = Math.floor(new Date(endDate + 'T23:59:59').getTime() / 1000);
        url += `&created_lte=${endTimestamp}`;
    }

    fetch(url)
        .then(response => response.json())
        .then(result => {
            const tbody = document.getElementById('customers-tbody');
            tbody.innerHTML = '';

            if (result && result.data) {
                result.data.forEach(customer => {
                    const date = customer.created ? new Date(customer.created * 1000).toLocaleString('tr-TR') : '-';
                    tbody.innerHTML += `
                        <tr>
                            <td>${customer.id}</td>
                            <td>${customer.name || 'Bilinmiyor'}</td>
                            <td>${customer.email || '-'}</td>
                            <td>${date}</td>
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

function filterCustomers() {
    // Filtre değişince sayfalamayı sıfırlıyoruz
    paginationState.customers = { cursorHistory: [null], currentPage: 0, limit: 10 };
    loadCustomers();
}

function clearCustomerFilter() {
    document.getElementById('cust-filter-start').value = '';
    document.getElementById('cust-filter-end').value = '';
    paginationState.customers = { cursorHistory: [null], currentPage: 0, limit: 10 };
    loadCustomers();
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
                    
                    let priceText = '-';
                    if (product.default_price) {
                        const amount = (product.default_price.unit_amount / 100).toFixed(2);
                        const currency = product.default_price.currency.toUpperCase();
                        priceText = `${amount} ${currency}`;
                    }

                    const date = product.created ? new Date(product.created * 1000).toLocaleString('tr-TR') : '-';

                    tbody.innerHTML += `
                        <tr>
                            <td>${product.id}</td>
                            <td>${product.name}</td>
                            <td>${product.description || '-'}</td>
                            <td>${priceText}</td>
                            <td><span class="status-badge ${sc}">${st}</span></td>
                            <td>${date}</td>
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
    const price = document.getElementById('prod-price').value;

    fetch(`${API_BASE_URL}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, price })
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
                    const date = payment.created ? new Date(payment.created * 1000).toLocaleString('tr-TR') : '-';
                    tbody.innerHTML += `
                        <tr>
                            <td>${payment.id}</td>
                            <td>${payment.customer || '-'}</td>
                            <td>${amount}</td>
                            <td>${payment.currency.toUpperCase()}</td>
                            <td><span class="status-badge ${sc}">${payment.status}</span></td>
                            <td>${date}</td>
                            <td class="action-cell">
                                <button class="btn btn-sm btn-pdf" onclick="createPdf('${payment.id}')" title="PDF Oluştur">
                                    <i class="fas fa-file-pdf"></i> PDF Oluştur
                                </button>
                                <button class="btn btn-sm btn-view" onclick="viewPdf('${payment.id}')" title="PDF Görüntüle">
                                    <i class="fas fa-eye"></i> Görüntüle
                                </button>
                            </td>
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

// =====================
// PDF İşLEMLERİ
// =====================

// PDF yeniden oluşturma için mevcut payment ID'yi tutar
let _pendingPdfPaymentId = null;

/**
 * PDF Oluştur: POST /api/payments/<id>/pdf
 * - PDF daha önce oluşturulmuşsa → onay modalı açılır.
 * - force=true ile çağrılırsa → üzerine yazılır.
 */
async function createPdf(paymentId, force = false) {
    const btn = event ? event.currentTarget : null;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Oluşturuluyor...';
    }

    try {
        const url = `${API_BASE_URL}/payments/${paymentId}/pdf${force ? '?force=true' : ''}`;
        const res = await fetch(url, { method: 'POST' });

        // PDF zaten mevcut → modal göster
        if (res.status === 409) {
            _pendingPdfPaymentId = paymentId;
            document.getElementById('pdf-confirm-modal').style.display = 'flex';
            return;
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(`PDF oluşturulamadı: ${err.error || res.status}`);
            return;
        }

        const blob = await res.blob();
        const objUrl = URL.createObjectURL(blob);
        window.open(objUrl, '_blank');
    } catch (e) {
        alert('❌ Sunucu hatası: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-file-pdf"></i> PDF Oluştur';
        }
    }
}

/** Modal — Evet: Yeni PDF oluştur (üzerine yaz) */
async function pdfConfirmYes() {
    closePdfModal();
    if (!_pendingPdfPaymentId) return;
    const paymentId = _pendingPdfPaymentId;
    _pendingPdfPaymentId = null;

    try {
        const res = await fetch(`${API_BASE_URL}/payments/${paymentId}/pdf?force=true`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(`PDF oluşturulamadı: ${err.error || res.status}`);
            return;
        }
        const blob = await res.blob();
        const url  = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (e) {
        alert('❌ Sunucu hatası: ' + e.message);
    }
}

/** Modal — Hayır: Mevcut PDF'i görüntüle */
function pdfConfirmNo() {
    closePdfModal();
    if (!_pendingPdfPaymentId) return;
    const paymentId = _pendingPdfPaymentId;
    _pendingPdfPaymentId = null;
    window.open(`${API_BASE_URL}/payments/${paymentId}/pdf`, '_blank');
}

function closePdfModal() {
    document.getElementById('pdf-confirm-modal').style.display = 'none';
}

/**
 * PDF Görüntüle: GET /api/payments/<id>/pdf
 * DB'deki mevcut PDF yeni sekmede açılır.
 */
function viewPdf(paymentId) {
    window.open(`${API_BASE_URL}/payments/${paymentId}/pdf`, '_blank');
}

// =====================
// İTİRAZ BELGESİ (DİSPUTE)
// =====================

// Dosya seçince adını göster
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('dispute-file');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const nameEl = document.getElementById('dispute-filename');
            nameEl.textContent = fileInput.files[0]?.name || 'Dosya seçilmedi';
        });
    }
});

// Dispute form submit
document.getElementById('upload-dispute-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const paymentId = document.getElementById('dispute-payment-id').value.trim();
    const fileInput = document.getElementById('dispute-file');

    if (!fileInput.files[0]) {
        showMessage('dispute-msg', '❌ Lütfen bir PDF dosyası seçin.', 'error');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Yükleniyor...';

    const formData = new FormData();
    formData.append('payment_intent_id', paymentId);
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(`${API_BASE_URL}/files/upload`, {
            method: 'POST',
            body: formData
            // NOT: Content-Type header'i set ETMEYİN — FormData otomatik ayarlar
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('dispute-msg',
                `✅ Stripe'a yüklendi! File ID: ${data.id}`, 'success');
            document.getElementById('upload-dispute-form').reset();
            document.getElementById('dispute-filename').textContent = 'Dosya seçilmedi';
            loadUploadedFiles();
        } else {
            showMessage('dispute-msg', `❌ Hata: ${data.error || 'Bilinmeyen hata'}`, 'error');
        }
    } catch (err) {
        showMessage('dispute-msg', `❌ Sunucu hatası: ${err.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Stripe\'a Yükle';
    }
});

/**
 * Yüklenen dosyaları DB'den çekip tabloya yazar.
 */
function loadUploadedFiles() {
    fetch(`${API_BASE_URL}/files`)
        .then(r => r.json())
        .then(result => {
            const tbody  = document.getElementById('files-tbody');
            const emptyP = document.getElementById('files-empty-msg');
            tbody.innerHTML = '';

            const files = result.data || [];
            if (files.length === 0) {
                emptyP.style.display = 'block';
                return;
            }
            emptyP.style.display = 'none';

            files.forEach(f => {
                const sizeKb = f.file_size ? (f.file_size / 1024).toFixed(1) + ' KB' : '-';
                const date   = f.olusturma_tarihi
                    ? new Date(f.olusturma_tarihi).toLocaleString('tr-TR')
                    : '-';
                tbody.innerHTML += `
                    <tr>
                        <td style="font-size:0.8rem;">${f.stripe_file_id}</td>
                        <td>${f.filename || '-'}</td>
                        <td><span class="status-badge status-pending">dispute_evidence</span></td>
                        <td>${sizeKb}</td>
                        <td style="font-size:0.8rem;">${f.payment_intent_stripe_id || '-'}</td>
                        <td style="font-size:0.8rem;">${date}</td>
                    </tr>
                `;
            });
        })
        .catch(() => {
            console.error('Dosyalar yüklenemedi.');
        });
}

// =====================
// DOSYA İŞLEMLERİ — EXPORT
// =====================

/**
 * Seçilen kaynak(lar)ı, seçilen format ve limit ile Stripe'tan çekip
 * tarayıcıya dosya olarak indirir.
 * Her kategori için ayrı POST /api/export isteği gönderilir.
 */
async function runExport() {
    const formatEl = document.querySelector('input[name="export-format"]:checked');
    const limitEl  = document.querySelector('input[name="export-limit"]:checked');
    const selectEl = document.getElementById('export-select');

    if (!formatEl || !limitEl || !selectEl) return;

    const format    = formatEl.value;            // 'json' veya 'csv'
    const limitVal  = limitEl.value;             // '100' veya 'all'
    const resources = Array.from(selectEl.selectedOptions).map(opt => opt.value).filter(val => val !== "");

    if (resources.length === 0) {
        showMessage('export-msg', '⚠️ En az bir veri kategorisi seçin.', 'error');
        return;
    }

    const btn = document.getElementById('export-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İndiriliyor...';

    let successCount = 0;

    for (const resource of resources) {
        try {
            const res = await fetch(`${API_BASE_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resource, format, limit: limitVal })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                showMessage('export-msg', `❌ ${resource} export başarısız: ${err.error || res.status}`, 'error');
                continue;
            }

            // Dosyayı blob olarak al ve tarayıcıya indir
            const blob     = await res.blob();
            const url      = URL.createObjectURL(blob);
            const a        = document.createElement('a');
            a.href         = url;
            a.download     = `${resource}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            successCount++;

            // Tarayıcının birden fazla indirmeyi bloklaması olasılığına karşı kısa bekleme
            if (resources.length > 1) {
                await new Promise(r => setTimeout(r, 600));
            }
        } catch (err) {
            showMessage('export-msg', `❌ Sunucu hatası: ${err.message}`, 'error');
        }
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-download"></i> Dışa Aktar';

    if (successCount > 0) {
        showMessage('export-msg',
            `✅ ${successCount} dosya indirildi (${format.toUpperCase()}, ${limitVal === 'all' ? 'Tüm kayıtlar' : 'Son 100'}).`,
            'success'
        );
    }
}

// Export ve Import sayfasındaki radio/checkbox kartlarına seçili görünüm efekti
document.addEventListener('DOMContentLoaded', () => {
    // Radio kartlar için
    document.querySelectorAll('.radio-card input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const group = radio.closest('.export-format-group');
            if (!group) return;
            group.querySelectorAll('.radio-card').forEach(c => c.classList.remove('selected'));
            radio.closest('.radio-card').classList.add('selected');
        });
        // Sayfa yüklendiğinde başlangıç durumu
        if (radio.checked) radio.closest('.radio-card').classList.add('selected');
    });
});

// =====================
// İÇE AKTARMA SİHİRBAZI (IMPORT WIZARD) JS MANTIĞI
// =====================
let wizardFile = null;
let wizardColumns = [];
let wizardInferredTypes = {};
let wizardPreviewData = [];
let activeImportResource = null; // 'customers', 'products', 'payments', 'prices' veya null

const wizardModelFields = {
    customers: [
        { key: "name", label: "Müşteri Adı (name)", required: true, desc: "Müşterinin tam adı" },
        { key: "email", label: "E-posta (email)", required: true, desc: "Müşteri e-posta adresi" }
    ],
    products: [
        { key: "name", label: "Ürün Adı (name)", required: true, desc: "Ürünün adı" },
        { key: "price", label: "Fiyat (price)", required: false, desc: "Ürün birim fiyatı (Sayısal)" },
        { key: "description", label: "Açıklama (description)", required: false, desc: "Ürün açıklaması" }
    ],
    payments: [
        { key: "customer_id", label: "Müşteri ID (customer_id)", required: true, desc: "Stripe Müşteri ID'si (cus_...)" },
        { key: "amount", label: "Tutar (amount)", required: true, desc: "Ödeme tutarı (Sayısal)" },
        { key: "currency", label: "Para Birimi (currency)", required: false, desc: "Varsayılan 'usd' (usd, eur, try vb.)" },
        { key: "order_id", label: "Sipariş ID (order_id)", required: false, desc: "İlgili Sipariş ID" }
    ],
    prices: [
        { key: "product_id", label: "Ürün ID (product_id)", required: true, desc: "Stripe Ürün ID'si (prod_...)" },
        { key: "amount", label: "Tutar (amount)", required: true, desc: "Fiyat tutarı (Sayısal)" },
        { key: "currency", label: "Para Birimi (currency)", required: false, desc: "Varsayılan 'usd' (usd, eur, try vb.)" }
    ]
};

function openImportModal(resource) {
    activeImportResource = resource;
    resetWizard();

    // Modalı aç
    document.getElementById("custom-import-modal").style.display = "flex";

    const titleEl = document.getElementById("import-modal-title");
    const modelGroup = document.getElementById("wizard-target-model-group");
    const modelSelect = document.getElementById("wizard-target-model");

    if (resource === "customers") {
        titleEl.innerHTML = `<i class="fas fa-magic" style="color: var(--accent-color); margin-right: 0.5rem;"></i> Müşteri İçe Aktarma Sihirbazı`;
        modelSelect.value = "customers";
        modelGroup.style.display = "none"; // Hedef model seçimini gizle
    } else if (resource === "products") {
        titleEl.innerHTML = `<i class="fas fa-magic" style="color: var(--accent-color); margin-right: 0.5rem;"></i> Ürün İçe Aktarma Sihirbazı`;
        modelSelect.value = "products";
        modelGroup.style.display = "none";
    } else if (resource === "payments") {
        titleEl.innerHTML = `<i class="fas fa-magic" style="color: var(--accent-color); margin-right: 0.5rem;"></i> Ödeme İçe Aktarma Sihirbazı`;
        modelSelect.value = "payments";
        modelGroup.style.display = "none";
    } else {
        titleEl.innerHTML = `<i class="fas fa-magic" style="color: var(--accent-color); margin-right: 0.5rem;"></i> İçe Aktarma Sihirbazı`;
        modelSelect.value = "customers";
        modelGroup.style.display = "block"; // Seçimi göster
    }
}

function closeImportModal() {
    document.getElementById("custom-import-modal").style.display = "none";
}

function onWizardFileSelected() {
    const fileInput = document.getElementById("wizard-file");
    const nameEl = document.getElementById("wizard-filename");
    wizardFile = fileInput.files[0] || null;
    nameEl.textContent = wizardFile ? wizardFile.name : "Dosya seçilmedi";
}

function changeWizardStep(step) {
    // Tüm adımları gizle
    document.getElementById("import-wizard-step-1").style.display = "none";
    document.getElementById("import-wizard-step-2").style.display = "none";
    document.getElementById("import-wizard-step-3").style.display = "none";
    document.getElementById("import-wizard-step-4").style.display = "none";

    // Badgeleri sıfırla
    for (let i = 1; i <= 4; i++) {
        const badge = document.getElementById(`wizard-badge-${i}`);
        if (i === step) {
            badge.style.color = "var(--accent-color)";
            badge.style.borderBottom = "3px solid var(--accent-color)";
            badge.querySelector("span").style.background = "var(--accent-color)";
            badge.querySelector("span").style.color = "#fff";
        } else {
            badge.style.color = "var(--text-muted)";
            badge.style.borderBottom = "3px solid transparent";
            badge.querySelector("span").style.background = "var(--border-color)";
            badge.querySelector("span").style.color = "var(--text-muted)";
        }
    }

    // Seçilen adımı göster
    document.getElementById(`import-wizard-step-${step}`).style.display = "block";
}

async function wizardAnalyzeFile() {
    const msgEl = document.getElementById("wizard-step1-msg");
    msgEl.textContent = "";

    if (!wizardFile) {
        msgEl.textContent = "❌ Lütfen bir dosya seçin.";
        msgEl.className = "form-message error";
        return;
    }

    const formData = new FormData();
    formData.append("file", wizardFile);

    try {
        const res = await fetch(`${API_BASE_URL}/import/analyze`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (!res.ok) {
            msgEl.textContent = `❌ Hata: ${data.error || "Dosya analiz edilemedi."}`;
            msgEl.className = "form-message error";
            return;
        }

        wizardColumns = data.columns || [];
        wizardInferredTypes = data.inferred_types || {};
        wizardPreviewData = data.preview || [];

        // Adım 2'ye geç ve mapping formunu oluştur
        onWizardModelChanged();
        changeWizardStep(2);
    } catch (err) {
        msgEl.textContent = `❌ Sunucu hatası: ${err.message}`;
        msgEl.className = "form-message error";
    }
}

function onWizardModelChanged() {
    const model = document.getElementById("wizard-target-model").value;
    const fields = wizardModelFields[model] || [];
    const container = document.getElementById("wizard-mapping-container");
    container.innerHTML = "";

    fields.forEach(field => {
        // En iyi eşleşen sütunu bulmaya çalışalım (isim benzerliğine göre)
        let bestMatch = "";
        const fKey = field.key.toLowerCase();
        
        wizardColumns.forEach(col => {
            const cLower = col.toLowerCase();
            if (cLower === fKey || cLower.includes(fKey) || fKey.includes(cLower)) {
                bestMatch = col;
            }
        });

        // Dropdown seçeneklerini oluştur
        let options = `<option value="">-- Alanı Eşleştirme (Boş Bırak) --</option>`;
        wizardColumns.forEach(col => {
            const isSelected = col === bestMatch ? "selected" : "";
            const inferred = wizardInferredTypes[col] ? ` (${wizardInferredTypes[col]})` : "";
            
            // Örnek veri gösterimi
            let sampleText = "";
            if (wizardPreviewData.length > 0 && wizardPreviewData[0][col] !== undefined) {
                const rawVal = wizardPreviewData[0][col];
                sampleText = ` (Örn: "${rawVal}")`;
            }

            options += `<option value="${col}" ${isSelected}>${col}${inferred}${sampleText}</option>`;
        });

        const reqBadge = field.required ? `<span style="color:var(--warning);">* Zorunlu</span>` : `<span style="color:var(--text-muted); font-size:0.8rem;">İsteğe Bağlı</span>`;

        container.innerHTML += `
            <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                <div style="flex: 1; min-width: 200px;">
                    <strong style="display: block; font-size: 0.95rem; color: #fff;">${field.label}</strong>
                    <small style="color: var(--text-muted); font-size: 0.8rem; display: block; margin-top: 2px;">${field.desc} ${reqBadge}</small>
                </div>
                <div style="flex: 1; min-width: 200px;">
                    <select class="form-select wizard-field-select" data-field="${field.key}" style="width: 100%;">
                        ${options}
                    </select>
                </div>
            </div>
        `;
    });
}

async function wizardPreviewMapping() {
    const msgEl = document.getElementById("wizard-step2-msg");
    msgEl.textContent = "";

    const model = document.getElementById("wizard-target-model").value;
    const mapping = {};
    let hasError = false;

    // Eşleştirmeleri oku
    document.querySelectorAll(".wizard-field-select").forEach(select => {
        const fieldKey = select.getAttribute("data-field");
        const mappedCol = select.value;
        mapping[fieldKey] = mappedCol;

        // Zorunlu alan kontrolü
        const fieldSpec = wizardModelFields[model].find(f => f.key === fieldKey);
        if (fieldSpec && fieldSpec.required && !mappedCol) {
            hasError = true;
        }
    });

    if (hasError) {
        msgEl.textContent = "❌ Lütfen tüm zorunlu (*) alanları dosyanızdaki sütunlarla eşleştirin.";
        msgEl.className = "form-message error";
        return;
    }

    const formData = new FormData();
    formData.append("file", wizardFile);
    formData.append("model", model);
    formData.append("mapping", JSON.stringify(mapping));

    try {
        const res = await fetch(`${API_BASE_URL}/import/preview`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (!res.ok) {
            msgEl.textContent = `❌ Hata: ${data.error || "Önizleme oluşturulamadı."}`;
            msgEl.className = "form-message error";
            return;
        }

        // Önizleme ekranını güncelle
        document.getElementById("wizard-preview-valid-count").textContent = data.valid_count;
        document.getElementById("wizard-preview-existing-count").textContent = data.existing_count;
        document.getElementById("wizard-preview-invalid-count").textContent = data.invalid_count;

        // Geçerli tabloyu çiz
        renderWizardPreviewValid(model, data.valid);
        
        // Mevcut tabloyu çiz
        renderWizardPreviewExisting(model, data.existing);

        // Geçersiz tabloyu çiz
        renderWizardPreviewInvalid(data.invalid);

        // İçe Aktar butonunu durumu
        const execBtn = document.getElementById("wizard-execute-btn");
        execBtn.disabled = data.valid_count === 0;

        toggleWizardPreviewTab('valid');
        changeWizardStep(3);
    } catch (err) {
        msgEl.textContent = `❌ Sunucu hatası: ${err.message}`;
        msgEl.className = "form-message error";
    }
}

function renderWizardPreviewValid(model, validRecords) {
    const thead = document.getElementById("wizard-preview-valid-thead");
    const tbody = document.getElementById("wizard-preview-valid-tbody");
    
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (!validRecords || validRecords.length === 0) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align: center; color: var(--text-muted);">Hiç geçerli kayıt bulunamadı.</td></tr>`;
        return;
    }

    // Başlıkları oluştur
    const fields = wizardModelFields[model].map(f => f.key);
    let headHtml = `<tr><th>Satır No</th>`;
    fields.forEach(f => {
        headHtml += `<th>${f}</th>`;
    });
    headHtml += `</tr>`;
    thead.innerHTML = headHtml;

    // Satırları oluştur
    validRecords.forEach(record => {
        let rowHtml = `<tr><td>${record.row_index}</td>`;
        fields.forEach(f => {
            const val = record.mapped[f];
            rowHtml += `<td>${val !== null ? val : "-"}</td>`;
        });
        rowHtml += `</tr>`;
        tbody.innerHTML += rowHtml;
    });
}

function renderWizardPreviewExisting(model, existingRecords) {
    const thead = document.getElementById("wizard-preview-existing-thead");
    const tbody = document.getElementById("wizard-preview-existing-tbody");
    
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (!existingRecords || existingRecords.length === 0) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align: center; color: var(--text-muted);">Hiç mevcut kayıt bulunamadı.</td></tr>`;
        return;
    }

    // Başlıkları oluştur
    const fields = wizardModelFields[model].map(f => f.key);
    let headHtml = `<tr><th>Satır No</th>`;
    fields.forEach(f => {
        headHtml += `<th>${f}</th>`;
    });
    headHtml += `</tr>`;
    thead.innerHTML = headHtml;

    // Satırları oluştur
    existingRecords.forEach(record => {
        let rowHtml = `<tr><td>${record.row_index}</td>`;
        fields.forEach(f => {
            const val = record.mapped[f];
            rowHtml += `<td>${val !== null ? val : "-"}</td>`;
        });
        rowHtml += `</tr>`;
        tbody.innerHTML += rowHtml;
    });
}

function renderWizardPreviewInvalid(invalidRecords) {
    const tbody = document.getElementById("wizard-preview-invalid-tbody");
    tbody.innerHTML = "";

    if (!invalidRecords || invalidRecords.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--success);">Hatalı kayıt bulunmuyor.</td></tr>`;
        return;
    }

    invalidRecords.forEach(record => {
        tbody.innerHTML += `
            <tr>
                <td>${record.row_index}</td>
                <td style="color: var(--warning); font-weight: bold;">${record.reason}</td>
                <td style="font-size: 0.8rem; font-family: monospace; max-width: 300px; white-space: normal;">${JSON.stringify(record.raw)}</td>
            </tr>
        `;
    });
}

function toggleWizardPreviewTab(tabType) {
    const validBtn = document.getElementById("wizard-tab-valid-btn");
    const existingBtn = document.getElementById("wizard-tab-existing-btn");
    const invalidBtn = document.getElementById("wizard-tab-invalid-btn");

    const validContainer = document.getElementById("wizard-preview-valid-container");
    const existingContainer = document.getElementById("wizard-preview-existing-container");
    const invalidContainer = document.getElementById("wizard-preview-invalid-container");

    // Reset styles
    validBtn.style.color = "var(--text-muted)";
    validBtn.style.borderBottom = "none";
    existingBtn.style.color = "var(--text-muted)";
    existingBtn.style.borderBottom = "none";
    invalidBtn.style.color = "var(--text-muted)";
    invalidBtn.style.borderBottom = "none";

    validContainer.style.display = "none";
    existingContainer.style.display = "none";
    invalidContainer.style.display = "none";

    if (tabType === 'valid' || tabType === true) {
        validBtn.style.color = "var(--success)";
        validBtn.style.borderBottom = "2px solid var(--success)";
        validContainer.style.display = "block";
    } else if (tabType === 'existing') {
        existingBtn.style.color = "var(--accent-color)";
        existingBtn.style.borderBottom = "2px solid var(--accent-color)";
        existingContainer.style.display = "block";
    } else { // 'invalid' or false
        invalidBtn.style.color = "var(--warning)";
        invalidBtn.style.borderBottom = "2px solid var(--warning)";
        invalidContainer.style.display = "block";
    }
}

async function wizardExecuteImport() {
    const msgEl = document.getElementById("wizard-step3-msg");
    const execBtn = document.getElementById("wizard-execute-btn");
    msgEl.textContent = "";

    const model = document.getElementById("wizard-target-model").value;
    const mapping = {};

    document.querySelectorAll(".wizard-field-select").forEach(select => {
        mapping[select.getAttribute("data-field")] = select.value;
    });

    execBtn.disabled = true;
    execBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> İçe Aktarılıyor...`;

    const formData = new FormData();
    formData.append("file", wizardFile);
    formData.append("model", model);
    formData.append("mapping", JSON.stringify(mapping));

    try {
        const res = await fetch(`${API_BASE_URL}/import/execute`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (!res.ok) {
            msgEl.textContent = `❌ Hata: ${data.error || "Aktarım başlatılamadı."}`;
            msgEl.className = "form-message error";
            execBtn.disabled = false;
            execBtn.innerHTML = `<i class="fas fa-cloud-upload-alt"></i> Eşleşenleri İçe Aktar`;
            return;
        }

        // Rapor ekranını güncelle
        document.getElementById("wizard-result-success").textContent = data.stats.success;
        document.getElementById("wizard-result-failed").textContent = data.stats.failed;

        const errorTbody = document.getElementById("wizard-result-errors-tbody");
        errorTbody.innerHTML = "";

        if (data.stats.failed_list && data.stats.failed_list.length > 0) {
            document.getElementById("wizard-result-errors-section").style.display = "block";
            data.stats.failed_list.forEach(errItem => {
                errorTbody.innerHTML += `
                    <tr>
                        <td>${errItem.row_index}</td>
                        <td style="color: var(--warning); font-weight: bold;">${errItem.reason}</td>
                        <td style="font-size: 0.8rem; font-family: monospace;">${JSON.stringify(errItem.mapped)}</td>
                    </tr>
                `;
            });
        } else {
            document.getElementById("wizard-result-errors-section").style.display = "none";
        }

        // İstatistikleri ve tabloları yenile
        loadDashboardStats();
        loadCustomers();
        loadProducts();
        loadPayments();

        changeWizardStep(4);
    } catch (err) {
        msgEl.textContent = `❌ Sunucu hatası: ${err.message}`;
        msgEl.className = "form-message error";
        execBtn.disabled = false;
        execBtn.innerHTML = `<i class="fas fa-cloud-upload-alt"></i> Eşleşenleri İçe Aktar`;
    }
}

function resetWizard() {
    document.getElementById("wizard-file").value = "";
    document.getElementById("wizard-filename").textContent = "Dosya seçilmedi";
    wizardFile = null;
    wizardColumns = [];
    wizardInferredTypes = {};
    wizardPreviewData = [];

    document.getElementById("wizard-step1-msg").textContent = "";
    document.getElementById("wizard-step1-msg").className = "form-message";
    document.getElementById("wizard-step2-msg").textContent = "";
    document.getElementById("wizard-step2-msg").className = "form-message";
    document.getElementById("wizard-step3-msg").textContent = "";
    document.getElementById("wizard-step3-msg").className = "form-message";

    changeWizardStep(1);
}

// =====================
// ÖZEL EXPORT MODALI İŞLEMLERİ
// =====================
let activeExportResource = null;

const resourceExportFields = {
    customers: [
        { key: "id", label: "ID" },
        { key: "name", label: "İsim" },
        { key: "email", label: "E-posta" },
        { key: "created", label: "Kayıt Tarihi" }
    ],
    products: [
        { key: "id", label: "ID" },
        { key: "name", label: "Ürün Adı" },
        { key: "description", label: "Açıklama" },
        { key: "price", label: "Fiyat" },
        { key: "active", label: "Durum" },
        { key: "created", label: "Kayıt Tarihi" }
    ],
    payments: [
        { key: "id", label: "ID" },
        { key: "customer", label: "Müşteri" },
        { key: "amount", label: "Tutar" },
        { key: "currency", label: "Para Birimi" },
        { key: "status", label: "Durum" },
        { key: "created", label: "Kayıt Tarihi" }
    ]
};

function openExportModal(resource) {
    activeExportResource = resource;
    
    // Başlığı belirle
    const titles = {
        customers: "Müşteri Verilerini Dışa Aktar",
        products: "Ürün Verilerini Dışa Aktar",
        payments: "Ödeme Verilerini Dışa Aktar"
    };
    document.getElementById("export-modal-title").innerHTML = 
        `<i class="fas fa-file-export" style="color: var(--accent-color); margin-right: 0.5rem;"></i> ${titles[resource] || 'Veri Dışa Aktar'}`;

    // Varsayılan format ve aralıkları sıfırla
    document.querySelector('input[name="custom-export-format"][value="json"]').checked = true;
    document.querySelector('input[name="custom-export-limit"][value="100"]').checked = true;
    toggleExportDateRange(false);

    // Tarih alanlarını sıfırla
    document.getElementById("custom-export-start").value = "";
    document.getElementById("custom-export-end").value = "";

    // Alan seçim listesini oluştur
    const fieldsContainer = document.getElementById("custom-export-fields");
    fieldsContainer.innerHTML = "";
    
    const fields = resourceExportFields[resource] || [];
    fields.forEach(f => {
        fieldsContainer.innerHTML += `
            <label style="cursor: pointer; display: flex; align-items: center; gap: 0.4rem; font-size: 0.88rem;">
                <input type="checkbox" name="custom-export-field-checkbox" value="${f.key}" checked style="accent-color: var(--accent-color); margin: 0;"> ${f.label}
            </label>
        `;
    });

    // Modalı aç
    document.getElementById("custom-export-modal").style.display = "flex";
}

function closeExportModal() {
    document.getElementById("custom-export-modal").style.display = "none";
    activeExportResource = null;
}

function toggleExportDateRange(show) {
    const container = document.getElementById("custom-export-date-inputs");
    container.style.display = show ? "flex" : "none";
}

function toggleAllExportFields() {
    const checkboxes = document.querySelectorAll('input[name="custom-export-field-checkbox"]');
    if (checkboxes.length === 0) return;
    
    // Herhangi biri unchecked ise tümünü check et, hepsi check ise tümünü uncheck et
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => cb.checked = !allChecked);
}

async function submitCustomExport() {
    if (!activeExportResource) return;

    const formatEl = document.querySelector('input[name="custom-export-format"]:checked');
    const limitEl = document.querySelector('input[name="custom-export-limit"]:checked');
    
    const format = formatEl ? formatEl.value : "json";
    const limit = limitEl ? limitEl.value : "100";

    let created_gte = null;
    let created_lte = null;

    if (limit === "date") {
        const startVal = document.getElementById("custom-export-start").value;
        const endVal = document.getElementById("custom-export-end").value;

        if (!startVal || !endVal) {
            alert("Lütfen başlangıç ve bitiş tarihlerini seçin.");
            return;
        }

        created_gte = Math.floor(new Date(startVal).getTime() / 1000);
        // Bitiş gününün son saniyesine kadar dahil et (23:59:59)
        created_lte = Math.floor(new Date(endVal + 'T23:59:59').getTime() / 1000);
    }

    const checkedBoxes = document.querySelectorAll('input[name="custom-export-field-checkbox"]:checked');
    const fields = Array.from(checkedBoxes).map(cb => cb.value);

    if (fields.length === 0) {
        alert("Lütfen dışa aktarılacak en az bir alan seçin.");
        return;
    }

    const btn = document.getElementById("custom-export-submit-btn");
    btn.disabled = true;
    const origText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İndiriliyor...';

    try {
        const bodyData = {
            resource: activeExportResource,
            format: format,
            limit: limit,
            fields: fields
        };
        if (created_gte !== null) bodyData.created_gte = created_gte;
        if (created_lte !== null) bodyData.created_lte = created_lte;

        const res = await fetch(`${API_BASE_URL}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyData)
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(`Dışa aktarım başarısız: ${err.error || res.status}`);
            return;
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${activeExportResource}_export.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        closeExportModal();
    } catch (e) {
        alert('❌ Sunucu hatası: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

// =========================================================================
// FATURA (INVOICE) YÖNETİMİ MANTIĞI
// =========================================================================

let invoiceCart = [];
let previewTimeout = null;

function loadInvoicesTab() {
    invoiceCart = [];
    updateCartUI();
    clearPreviewSheet();
    
    // Dropdown'ları ve fatura listesini yükle
    loadInvoiceCustomers();
    loadInvoiceProducts();
    loadLocalInvoicesList();
}

function formatInvoiceCurrency(amountCents, currencyCode) {
    const amount = amountCents / 100;
    const code = currencyCode.toLowerCase();
    
    if (code === 'try') {
        return amount.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' });
    } else if (code === 'eur') {
        return amount.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' });
    } else if (code === 'gbp') {
        return amount.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });
    }
    
    return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function loadInvoiceCustomers() {
    const select = document.getElementById("invoice-customer-select");
    select.innerHTML = '<option value="">Müşteri Seçin...</option>';
    
    fetch(`${API_BASE_URL}/customers?limit=100`)
        .then(res => res.json())
        .then(result => {
            if (result && result.data) {
                result.data.forEach(cust => {
                    const option = document.createElement("option");
                    option.value = cust.id;
                    option.textContent = `${cust.name || 'Bilinmiyor'} (${cust.email || 'E-posta yok'})`;
                    option.dataset.name = cust.name || 'Bilinmiyor';
                    option.dataset.email = cust.email || '';
                    select.appendChild(option);
                });
            }
        })
        .catch(err => console.error("Error loading invoice customers:", err));
}

function loadInvoiceProducts() {
    const select = document.getElementById("invoice-product-select");
    select.innerHTML = '<option value="">Ürün Seçin...</option>';
    
    fetch(`${API_BASE_URL}/products?limit=100`)
        .then(res => res.json())
        .then(result => {
            if (result && result.data) {
                // Sadece fiyatı tanımlı olan ve aktif ürünleri listele
                const activeProducts = result.data.filter(p => p.active && p.default_price);
                activeProducts.forEach(prod => {
                    const price = prod.default_price;
                    const amountFormatted = formatInvoiceCurrency(price.unit_amount, price.currency);
                    
                    const option = document.createElement("option");
                    option.value = prod.id;
                    option.textContent = `${prod.name} (${amountFormatted})`;
                    option.dataset.priceId = price.id;
                    option.dataset.priceAmount = price.unit_amount;
                    option.dataset.currency = price.currency;
                    option.dataset.name = prod.name;
                    select.appendChild(option);
                });
            }
        })
        .catch(err => console.error("Error loading invoice products:", err));
}

function addInvoiceItemToList() {
    const select = document.getElementById("invoice-product-select");
    const qtyInput = document.getElementById("invoice-product-qty");
    
    if (!select.value) {
        alert("Lütfen önce bir ürün seçin.");
        return;
    }
    
    const qty = parseInt(qtyInput.value);
    if (isNaN(qty) || qty < 1) {
        alert("Lütfen geçerli bir adet girin.");
        return;
    }
    
    const selectedOption = select.options[select.selectedIndex];
    const productId = select.value;
    const priceId = selectedOption.dataset.priceId;
    const priceAmount = parseInt(selectedOption.dataset.priceAmount);
    const currency = selectedOption.dataset.currency;
    const name = selectedOption.dataset.name;
    
    // Fatura para birimi eşleşme kontrolü
    const chosenCurrency = document.getElementById("invoice-currency-select").value.toLowerCase();
    if (currency.toLowerCase() !== chosenCurrency) {
        alert(`Seçilen ürün para birimi (${currency.toUpperCase()}), fatura para birimi (${chosenCurrency.toUpperCase()}) ile eşleşmelidir.`);
        return;
    }
    
    // Sepet kontrolü
    const existingItem = invoiceCart.find(item => item.productId === productId);
    if (existingItem) {
        existingItem.quantity += qty;
    } else {
        invoiceCart.push({
            productId,
            priceId,
            name,
            priceAmount,
            currency,
            quantity: qty
        });
    }
    
    qtyInput.value = 1;
    updateCartUI();
    debouncePreview();
}

function updateCartUI() {
    const tbody = document.getElementById("invoice-cart-tbody");
    const emptyMsg = document.getElementById("invoice-cart-empty");
    tbody.innerHTML = "";
    
    if (invoiceCart.length === 0) {
        emptyMsg.style.display = "block";
        return;
    }
    emptyMsg.style.display = "none";
    
    invoiceCart.forEach((item, index) => {
        const itemTotal = item.priceAmount * item.quantity;
        const priceFormatted = formatInvoiceCurrency(item.priceAmount, item.currency);
        const totalFormatted = formatInvoiceCurrency(itemTotal, item.currency);
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.name}</td>
            <td>${priceFormatted}</td>
            <td>
                <div style="display:flex; align-items:center; gap:10px;">
                    <button class="btn-sm btn-view" onclick="updateQty(${index}, -1)" style="padding: 2px 6px; font-size:10px; margin:0;"><i class="fas fa-minus"></i></button>
                    <span style="font-weight:bold; min-width:20px; text-align:center;">${item.quantity}</span>
                    <button class="btn-sm btn-view" onclick="updateQty(${index}, 1)" style="padding: 2px 6px; font-size:10px; margin:0;"><i class="fas fa-plus"></i></button>
                </div>
            </td>
            <td>${totalFormatted}</td>
            <td>
                <button class="btn-sm btn-pdf" style="margin:0;" onclick="removeInvoiceItemFromList(${index})"><i class="fas fa-trash-alt"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateQty(index, delta) {
    if (invoiceCart[index]) {
        invoiceCart[index].quantity += delta;
        if (invoiceCart[index].quantity <= 0) {
            invoiceCart.splice(index, 1);
        }
        updateCartUI();
        debouncePreview();
    }
}

function removeInvoiceItemFromList(index) {
    invoiceCart.splice(index, 1);
    updateCartUI();
    debouncePreview();
}

function clearInvoiceCart() {
    invoiceCart = [];
    updateCartUI();
    debouncePreview();
}

function onInvoiceInputChange() {
    debouncePreview();
}

function debouncePreview() {
    if (previewTimeout) clearTimeout(previewTimeout);
    previewTimeout = setTimeout(() => {
        fetchInvoicePreview();
    }, 500);
}

function clearPreviewSheet() {
    document.getElementById("preview-date").textContent = "-";
    document.getElementById("preview-customer-name").textContent = "-";
    document.getElementById("preview-customer-email").textContent = "-";
    document.getElementById("preview-customer-id").textContent = "-";
    document.getElementById("preview-subtotal").textContent = "$0.00";
    document.getElementById("preview-discount-row").style.display = "none";
    document.getElementById("preview-discount").textContent = "-$0.00";
    document.getElementById("preview-tax").textContent = "$0.00";
    document.getElementById("preview-total").textContent = "$0.00";
    
    const tbody = document.getElementById("preview-table-tbody");
    tbody.innerHTML = `
        <tr>
            <td colspan="4" style="text-align: center; padding: 2rem; color: #9ca3af;">Ürün eklenmedi.</td>
        </tr>
    `;
}

function fetchInvoicePreview() {
    const customerSelect = document.getElementById("invoice-customer-select");
    const currencySelect = document.getElementById("invoice-currency-select");
    const badge = document.querySelector(".invoice-preview-badge");
    
    const customerId = customerSelect.value;
    const currency = currencySelect.value;
    
    if (!customerId || invoiceCart.length === 0) {
        clearPreviewSheet();
        return;
    }
    
    badge.textContent = "ANLIK ÖNİZLEME (Güncelleniyor...)";
    badge.style.background = "rgba(245, 158, 11, 0.15)";
    badge.style.color = "#f59e0b";
    badge.style.borderColor = "rgba(245, 158, 11, 0.3)";
    
    const items = invoiceCart.map(item => ({
        price: item.priceId,
        quantity: item.quantity
    }));
    
    fetch(`${API_BASE_URL}/invoices/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            customer: customerId,
            currency: currency,
            items: items
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("Önizleme çekilemedi.");
        return res.json();
    })
    .then(preview => {
        const now = new Date();
        document.getElementById("preview-date").textContent = now.toLocaleDateString("tr-TR");
        
        const opt = customerSelect.options[customerSelect.selectedIndex];
        document.getElementById("preview-customer-name").textContent = opt.dataset.name || "-";
        document.getElementById("preview-customer-email").textContent = opt.dataset.email || "-";
        document.getElementById("preview-customer-id").textContent = customerId;
        
        const tbody = document.getElementById("preview-table-tbody");
        tbody.innerHTML = "";
        
        if (preview.lines && preview.lines.data) {
            preview.lines.data.forEach(line => {
                const tr = document.createElement("tr");
                const desc = line.description || "Ürün Tanımı";
                const unitFormatted = formatInvoiceCurrency(line.price ? line.price.unit_amount : line.amount / line.quantity, preview.currency);
                const totalFormatted = formatInvoiceCurrency(line.amount, preview.currency);
                
                tr.innerHTML = `
                    <td style="padding: 10px 5px; color: #30313d;">${desc}</td>
                    <td style="padding: 10px 5px; text-align: right; color: #30313d;">${unitFormatted}</td>
                    <td style="padding: 10px 5px; text-align: center; color: #30313d;">${line.quantity}</td>
                    <td style="padding: 10px 5px; text-align: right; color: #30313d;">${totalFormatted}</td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        const previewSubtotal = preview.subtotal || 0;
        const previewTax = preview.tax || 0;
        const previewTotal = preview.total || 0;
        const previewCurrency = preview.currency;
        
        document.getElementById("preview-subtotal").textContent = formatInvoiceCurrency(previewSubtotal, previewCurrency);
        document.getElementById("preview-tax").textContent = formatInvoiceCurrency(previewTax, previewCurrency);
        document.getElementById("preview-total").textContent = formatInvoiceCurrency(previewTotal, previewCurrency);
        
        const diff = (previewSubtotal + previewTax) - previewTotal;
        const discountRow = document.getElementById("preview-discount-row");
        if (diff > 0) {
            discountRow.style.display = "flex";
            document.getElementById("preview-discount").textContent = "-" + formatInvoiceCurrency(diff, previewCurrency);
        } else {
            discountRow.style.display = "none";
        }
        
        badge.textContent = "ANLIK ÖNİZLEME";
        badge.style.background = "rgba(99, 91, 255, 0.15)";
        badge.style.color = "#a5b4fc";
        badge.style.borderColor = "rgba(99, 91, 255, 0.3)";
    })
    .catch(err => {
        console.error("Preview fetch error:", err);
        badge.textContent = "HATA (Müşteri Para Birimi Uyuşmazlığı)";
        badge.style.background = "rgba(239, 68, 68, 0.15)";
        badge.style.color = "#ef4444";
        badge.style.borderColor = "rgba(239, 68, 68, 0.3)";
    });
}

function submitFinalizeInvoice() {
    const customerSelect = document.getElementById("invoice-customer-select");
    const currencySelect = document.getElementById("invoice-currency-select");
    
    const customerId = customerSelect.value;
    const currency = currencySelect.value;
    
    if (!customerId) {
        alert("Lütfen önce bir müşteri seçin.");
        return;
    }
    if (invoiceCart.length === 0) {
        alert("Lütfen faturaya en az bir ürün ekleyin.");
        return;
    }
    
    const confirmAction = confirm("Faturayı kesinleştirmek ve Stripe üzerinden oluşturmak istediğinizden emin misiniz?");
    if (!confirmAction) return;
    
    const btn = document.querySelector(".invoice-left-panel button[onclick='submitFinalizeInvoice()']");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fatura Kesiliyor...';
    
    const items = invoiceCart.map(item => ({
        price: item.priceId,
        quantity: item.quantity
    }));
    
    fetch(`${API_BASE_URL}/invoices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            customer: customerId,
            currency: currency,
            items: items
        })
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Fatura oluşturulamadı.");
        return data;
    })
    .then(invoice => {
        showMessage("invoice-action-msg", `✅ Fatura başarıyla oluşturuldu: ${invoice.id}`);
        invoiceCart = [];
        updateCartUI();
        clearPreviewSheet();
        loadLocalInvoicesList();
        loadDashboardStats();
    })
    .catch(err => {
        console.error("Invoice finalization error:", err);
        showMessage("invoice-action-msg", `❌ Hata: ${err.message}`, "error");
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

function loadLocalInvoicesList() {
    const tbody = document.getElementById("invoices-tbody-list");
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">Yükleniyor...</td></tr>';
    
    fetch(`${API_BASE_URL}/invoices`)
        .then(res => res.json())
        .then(result => {
            tbody.innerHTML = "";
            if (result && result.data && result.data.length > 0) {
                result.data.forEach(inv => {
                    const date = inv.olusturma_tarihi ? new Date(inv.olusturma_tarihi).toLocaleString('tr-TR') : '-';
                    const amountFormatted = formatInvoiceCurrency(inv.amount, inv.currency);
                    
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${inv.stripe_invoice_id}</td>
                        <td>${inv.customer_stripe_id}</td>
                        <td>${amountFormatted}</td>
                        <td style="text-transform: uppercase;">${inv.currency}</td>
                        <td><span class="status-badge ${statusClass(inv.status)}">${inv.status.toUpperCase()}</span></td>
                        <td>${date}</td>
                        <td class="action-cell">
                            <a href="${API_BASE_URL}/invoices/${inv.stripe_invoice_id}/pdf" target="_blank" class="btn-sm btn-view" style="text-decoration:none;">
                                <i class="fas fa-file-pdf"></i> PDF Gör
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">Kayıtlı fatura bulunamadı.</td></tr>';
            }
        })
        .catch(err => {
            console.error("Error loading local invoices:", err);
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--warning);">Yüklenirken hata oluştu.</td></tr>';
        });
}