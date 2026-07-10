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

    // Import dosya ismi gösterimi
    const importFileInput = document.getElementById('import-file');
    if (importFileInput) {
        importFileInput.addEventListener('change', () => {
            const nameEl = document.getElementById('import-filename');
            nameEl.textContent = importFileInput.files[0]?.name || 'Dosya seçilmedi';
        });
    }

    // Import formu gönderme
    const importForm = document.getElementById('import-form');
    if (importForm) {
        importForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formatEl = document.querySelector('input[name="import-format"]:checked');
            const fileInput = document.getElementById('import-file');
            const msgEl = 'import-msg';

            if (!fileInput.files[0]) {
                showMessage(msgEl, '❌ Lütfen aktarılacak dosyayı seçin.', 'error');
                return;
            }

            const format = formatEl.value;
            const file = fileInput.files[0];
            const filename = file.name.toLowerCase();

            // Client-side uzantı doğrulaması
            if (format === 'json' && !filename.endsWith('.json')) {
                showMessage(msgEl, '❌ Hata: JSON formatı seçildi ancak dosya .json uzantılı değil.', 'error');
                return;
            }
            if (format === 'csv' && !filename.endsWith('.csv')) {
                showMessage(msgEl, '❌ Hata: CSV formatı seçildi ancak dosya .csv uzantılı değil.', 'error');
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İçe Aktarılıyor...';

            const formData = new FormData();
            formData.append('format', format);
            formData.append('file', file);

            try {
                const res = await fetch(`${API_BASE_URL}/import`, {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if (res.ok) {
                    const stats = data.stats;
                    showMessage(msgEl, `✅ İçe aktarım tamamlandı! Başarılı: ${stats.success}, Başarısız: ${stats.failed}, Atlanan: ${stats.skipped}`, 'success');
                    importForm.reset();
                    document.getElementById('import-filename').textContent = 'Dosya seçilmedi';
                    loadDashboardStats();
                    if (document.getElementById('customers-sec').style.display === 'block') {
                        paginationState.customers = { cursorHistory: [null], currentPage: 0, limit: 10 };
                        loadCustomers();
                    }
                } else {
                    showMessage(msgEl, `❌ Hata: ${data.error || 'Bilinmeyen hata'}`, 'error');
                }
            } catch (err) {
                showMessage(msgEl, `❌ Sunucu hatası: ${err.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-upload"></i> İçe Aktar (Import)';
            }
        });
    }
});

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