const statusEl = document.getElementById('status');
const tripContainer = document.getElementById('trip-container');

// ========== УТИЛИТЫ ==========

function apiFetch(path, options = {}) {
    return fetch(path, {
        ...options,
        headers: {
            ...(options.headers || {}),
            'Authorization': `Bearer ${window.__accessToken}`,
        },
    });
}

const TRIP_STATUS_LABELS = {
    pending: 'Ожидает',
    sent: 'Отправлен',
    confirmed: 'Подтверждён',
    partial: 'Частично',
    rejected: 'Отклонён',
};

const ROUTE_ICONS = {
    pending: '⏳',
    confirmed: '✅',
    partial: '⚠️',
    rejected: '❌',
};

const POINT_ICONS = {
    pending: '⏳',
    confirmed: '✅',
    rejected: '❌',
};

function fmtWeight(w) {
    return w ? `${w} кг` : '—';
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// ========== СОСТОЯНИЕ ВЫБОРА ==========
let selectionMode = false;
let selectedItems = { routes: new Set(), points: new Set() };
let currentTripData = null;

// ========== РЕНДЕР ==========

function renderTrip(trip) {
    const routeRows = trip.routes
        .sort((a, b) => a.order_number - b.order_number)
        .map((route, index) => {
            let routeWeight = 0;
            let hasWeight = false;
            route.points.forEach(p => {
                if (p.weight) {
                    routeWeight += parseFloat(p.weight);
                    hasWeight = true;
                }
            });
            const weightStr = hasWeight ? routeWeight.toFixed(3) + ' кг' : '—';

            const routeChecked = selectedItems.routes.has(route.id);

            const pointsHtml = route.points
                .sort((a, b) => a.order_number - b.order_number)
                .map(point => {
                    const pointChecked = selectedItems.points.has(point.id);
                    return `
                    <div class="point-row">
                        ${selectionMode ? `
                            <input type="checkbox" class="select-checkbox" 
                                   ${pointChecked ? 'checked' : ''}
                                   ${routeChecked ? 'disabled' : ''}
                                   onchange="togglePointSelection(${point.id}, this.checked)">
                        ` : ''}
                        <span class="point-icon">${POINT_ICONS[point.status] || '—'}</span>
                        <div class="point-info">
                            <div class="point-address">${escapeHtml(point.address)}</div>
                            <div class="point-meta">${fmtWeight(point.weight)}</div>
                            ${point.rejection_reason ? `<div class="point-reason">${escapeHtml(point.rejection_reason)}</div>` : ''}
                        </div>
                    </div>
                `}).join('');

            const isCollapsed = selectionMode ? false : index !== 0;

            return `
                <div class="route-block ${isCollapsed ? 'collapsed' : ''} ${routeChecked ? 'selected' : ''}" data-route-id="${route.id}">
                    <div class="route-header" ${selectionMode ? '' : `onclick="toggleRouteCollapse(${route.id})"`}>
                        ${selectionMode ? `
                            <input type="checkbox" class="select-checkbox" 
                                   ${routeChecked ? 'checked' : ''}
                                   onchange="toggleRouteSelection(${route.id}, this.checked)">
                        ` : ''}
                        <div class="route-title-group">
                            <span class="icon">${ROUTE_ICONS[route.status] || '—'}</span>
                            <span>${escapeHtml(route.name || `Маршрут #${route.order_number}`)}</span>
                        </div>
                        <span class="route-stats">${route.points.length} точек, ${weightStr}</span>
                        ${selectionMode ? '' : '<span class="route-toggle-icon">▼</span>'}
                    </div>
                    <div class="route-points">
                        ${pointsHtml}
                    </div>
                </div>
            `;
        }).join('');

    const actions = trip.is_actionable && !selectionMode ? `
        <div class="actions">
            <button class="btn btn-confirm" onclick="confirmTrip(${trip.id})">✅ Подтвердить всё</button>
            <button class="btn btn-reject" onclick="rejectTrip(${trip.id})">🚫 Отказаться</button>
        </div>
        <div class="actions" style="margin-top:8px;">
            <button class="btn btn-secondary" onclick="enterSelectionMode(${trip.id})">✏️ Выбрать элементы</button>
        </div>
    ` : '';

    const dateStr = new Date(trip.date).toLocaleDateString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });

    return `
        <div class="trip-card" data-trip-id="${trip.id}">
            <div class="trip-header">
                <div class="trip-title">Рейс на ${dateStr}</div>
                <div class="trip-status ${trip.status}">${TRIP_STATUS_LABELS[trip.status] || trip.status}</div>
            </div>
            <div class="trip-totals">
                Маршрутов: ${trip.routes_count}, точек: ${trip.points_count}, вес: ${fmtWeight(trip.total_weight)}
            </div>
            ${routeRows}
            ${actions}
        </div>
    `;
}

function toggleRouteCollapse(routeId) {
    if (selectionMode) return;
    const block = document.querySelector(`.route-block[data-route-id="${routeId}"]`);
    if (block) {
        block.classList.toggle('collapsed');
    }
}

function renderNoTrips(date) {
    const dateStr = new Date(date).toLocaleDateString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });
    return `
        <div class="empty-state">
            <p>На ${dateStr} рейсов нет.</p>
        </div>
    `;
}

// ========== ЛОГИКА РЕЖИМА ВЫБОРА ==========

function enterSelectionMode(tripId) {
    apiFetch('/api/v1/me/trips').then(r => r.json()).then(trips => {
        const trip = trips.find(t => t.id === tripId);
        if (!trip) return alert('Рейс не найден');

        currentTripData = trip;
        selectionMode = true;
        selectedItems = { routes: new Set(), points: new Set() };

        document.body.classList.add('selection-active');
        tripContainer.classList.add('selection-mode');
        document.getElementById('floating-actions').classList.remove('hidden');

        updateSelectionUI();
        tripContainer.innerHTML = renderTrip(currentTripData);
    });
}

function exitSelectionMode() {
    selectionMode = false;
    selectedItems = { routes: new Set(), points: new Set() };
    currentTripData = null;

    document.body.classList.remove('selection-active');
    tripContainer.classList.remove('selection-mode');
    document.getElementById('floating-actions').classList.add('hidden');

    loadTrips();
}

function toggleRouteSelection(routeId, checked) {
    if (checked) {
        selectedItems.routes.add(routeId);
        const route = currentTripData.routes.find(r => r.id === routeId);
        route.points.forEach(p => selectedItems.points.delete(p.id));
    } else {
        selectedItems.routes.delete(routeId);
    }
    updateSelectionUI();
    tripContainer.innerHTML = renderTrip(currentTripData);
}

function togglePointSelection(pointId, checked) {
    if (checked) {
        selectedItems.points.add(pointId);
    } else {
        selectedItems.points.delete(pointId);
    }
    updateSelectionUI();
    tripContainer.innerHTML = renderTrip(currentTripData);
}

function updateSelectionUI() {
    const routesCount = selectedItems.routes.size;
    const pointsCount = selectedItems.points.size;
    const total = routesCount + pointsCount;

    let text = 'Выбрано: ';
    if (routesCount > 0) text += `${routesCount} маршр., `;
    if (pointsCount > 0) text += `${pointsCount} точек, `;
    if (total === 0) text += '0';
    else text = text.slice(0, -2);

    document.getElementById('selection-info').textContent = text;
}

async function submitSelectedReject() {
    if (selectedItems.routes.size === 0 && selectedItems.points.size === 0) {
        return alert('Выберите хотя бы один элемент');
    }

    rejectState = {
        tripId: currentTripData.id,
        step: 3,
        type: 'partial',
        selectedRoutes: new Set(selectedItems.routes),
        selectedPoints: new Set(selectedItems.points),
        commonRouteReason: null,
        commonPointReason: null,
        trip: currentTripData,
        reasons: { trip: [], route: [], point: [] },
        hadRejections: false,
    };

    try {
        const [tripReasons, routeReasons, pointReasons] = await Promise.all([
            apiFetch('/api/v1/me/rejection-reasons?scope=trip').then(r => r.json()),
            apiFetch('/api/v1/me/rejection-reasons?scope=route').then(r => r.json()),
            apiFetch('/api/v1/me/rejection-reasons?scope=point').then(r => r.json()),
        ]);
        rejectState.reasons.trip = tripReasons;
        rejectState.reasons.route = routeReasons;
        rejectState.reasons.point = pointReasons;
    } catch (e) {
        return alert('Ошибка загрузки причин: ' + e.message);
    }

    document.getElementById('reject-modal').classList.remove('hidden');
    renderRejectModal();
}

// ========== ЗАГРУЗКА ДАННЫХ ==========

async function loadTrips(date) {
    statusEl.textContent = 'Загрузка рейса...';
    statusEl.classList.remove('hidden');
    tripContainer.classList.add('hidden');
    tripContainer.innerHTML = '';

    const dateControls = document.getElementById('date-controls');
    const dateInput = document.getElementById('date-input');
    const tomorrowBtn = document.getElementById('tomorrow-btn');
    dateControls.classList.remove('hidden');

    const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];

    if (!date) {
        dateInput.value = tomorrow;
    } else {
        dateInput.value = date;
    }

    if (dateInput.value === tomorrow) {
        tomorrowBtn.textContent = 'Завтра';
        tomorrowBtn.disabled = true;
        tomorrowBtn.style.opacity = '0.5';
    } else {
        tomorrowBtn.textContent = 'Вернуться на завтра';
        tomorrowBtn.disabled = false;
        tomorrowBtn.style.opacity = '1';
    }

    try {
        const url = date ? `/api/v1/me/trips?date=${date}` : '/api/v1/me/trips';
        const resp = await apiFetch(url);

        if (!resp.ok) {
            const err = await resp.json();
            statusEl.textContent = `Ошибка: ${err.detail || 'Неизвестная'}`;
            return;
        }

        const trips = await resp.json();
        statusEl.classList.add('hidden');

        if (trips.length === 0) {
            const activeDate = date || tomorrow;
            tripContainer.innerHTML = renderNoTrips(activeDate);
        } else {
            tripContainer.innerHTML = trips.map(renderTrip).join('');
        }

        tripContainer.classList.remove('hidden');
    } catch (e) {
        statusEl.textContent = `Сетевая ошибка: ${e.message}`;
    }
}

function onDateChange() {
    const dateInput = document.getElementById('date-input');
    if (dateInput.value) {
        loadTrips(dateInput.value);
    }
}

function resetToTomorrow() {
    loadTrips();
}

// ========== ДЕЙСТВИЯ ==========

async function confirmTrip(tripId) {
    if (!confirm('Подтвердить весь рейс?')) return;

    try {
        const resp = await apiFetch(`/api/v1/me/trips/${tripId}/confirm`, {
            method: 'POST',
        });

        if (!resp.ok) {
            const err = await resp.json();
            alert(`Ошибка: ${err.detail || 'Неизвестная'}`);
            return;
        }

        await loadTrips();
    } catch (e) {
        alert(`Сетевая ошибка: ${e.message}`);
    }
}

// ========== СОСТОЯНИЕ ОТКАЗА ==========
let rejectState = {
    tripId: null,
    step: 1,
    type: null,
    selectedRoutes: new Set(),
    selectedPoints: new Set(),
    commonRouteReason: null,
    commonPointReason: null,
    trip: null,
    reasons: { trip: [], route: [], point: [] },
    hadRejections: false,
};

async function rejectTrip(tripId) {
    const resp = await apiFetch('/api/v1/me/trips');
    const trips = await resp.json();
    const trip = trips.find(t => t.id === tripId);
    if (!trip) return alert('Рейс не найден');

    const preSelectedRoutes = new Set();
    const preSelectedPoints = new Set();

    trip.routes.forEach(route => {
        if (route.status === 'rejected') {
            preSelectedRoutes.add(route.id);
        } else {
            route.points.forEach(point => {
                if (point.status === 'rejected') {
                    preSelectedPoints.add(point.id);
                }
            });
        }
    });

    rejectState = {
        tripId: tripId,
        step: 1,
        type: null,
        selectedRoutes: preSelectedRoutes,
        selectedPoints: preSelectedPoints,
        commonRouteReason: null,
        commonPointReason: null,
        trip: trip,
        reasons: { trip: [], route: [], point: [] },
        hadRejections: preSelectedRoutes.size > 0 || preSelectedPoints.size > 0,
    };

    try {
        const [tripReasons, routeReasons, pointReasons] = await Promise.all([
            apiFetch('/api/v1/me/rejection-reasons?scope=trip').then(r => r.json()),
            apiFetch('/api/v1/me/rejection-reasons?scope=route').then(r => r.json()),
            apiFetch('/api/v1/me/rejection-reasons?scope=point').then(r => r.json()),
        ]);
        rejectState.reasons.trip = tripReasons;
        rejectState.reasons.route = routeReasons;
        rejectState.reasons.point = pointReasons;
    } catch (e) {
        return alert('Ошибка загрузки причин: ' + e.message);
    }

    document.getElementById('reject-modal').classList.remove('hidden');
    renderRejectModal();
}

function closeRejectModal() {
    document.getElementById('reject-modal').classList.add('hidden');
}

function renderRejectModal() {
    const body = document.getElementById('modal-body');
    const footer = document.getElementById('modal-footer');
    const title = document.getElementById('modal-title');

    if (rejectState.step === 1) {
        title.textContent = 'Отказ от рейса';
        body.innerHTML = `
            <div style="display:flex;flex-direction:column;gap:12px;">
                <button class="btn btn-reject" onclick="setRejectType('trip')">🚫 Отказаться от всего</button>
                <button class="btn btn-secondary" onclick="setRejectType('partial')">✏️ Частично</button>
            </div>
        `;
        footer.innerHTML = `<button class="btn btn-secondary" onclick="closeRejectModal()">Отмена</button>`;
    }
    else if (rejectState.step === 2) {
        title.textContent = 'Что отклонить?';
        body.innerHTML = renderPartialSelection();
        footer.innerHTML = `
            <button class="btn btn-secondary" onclick="rejectState.step=1;renderRejectModal()">← Назад</button>
            <button class="btn btn-reject" onclick="goToReasons()">Далее</button>
        `;
    }
    else if (rejectState.step === 3) {
        title.textContent = 'Причины отказа';
        body.innerHTML = renderReasonsSelection();
        footer.innerHTML = `
            <button class="btn btn-secondary" onclick="rejectState.step=2;renderRejectModal()">← Назад</button>
            <button class="btn btn-reject" onclick="submitReject()">Отправить отказ</button>
        `;
    }
    else if (rejectState.step === 4) {
        title.textContent = 'Причина отказа';
        body.innerHTML = renderTripReasons();
        footer.innerHTML = `
            <button class="btn btn-secondary" onclick="rejectState.step=1;renderRejectModal()">← Назад</button>
            <button class="btn btn-reject" onclick="submitReject()">Отправить отказ</button>
        `;
    }
}

function setRejectType(type) {
    rejectState.type = type;
    if (type === 'trip') {
        rejectState.step = 4;
    } else {
        rejectState.step = 2;
    }
    renderRejectModal();
}

function renderPartialSelection() {
    let html = '<p style="color:#888;font-size:13px;margin-bottom:12px;">Снимите галочку, чтобы отменить отказ.</p>';
    const trip = rejectState.trip;

    trip.routes.sort((a, b) => a.order_number - b.order_number).forEach(route => {
        const routeSelected = rejectState.selectedRoutes.has(route.id);
        const disabled = routeSelected;

        html += `
            <div style="margin-bottom:16px;">
                <label class="select-item ${routeSelected ? 'selected' : ''}">
                    <input type="checkbox" ${routeSelected ? 'checked' : ''} 
                           onchange="toggleRoute(${route.id}, this.checked)">
                    <div class="select-item-content">
                        <strong>Маршрут: ${escapeHtml(route.name || '#' + route.order_number)}</strong>
                    </div>
                </label>
        `;

        route.points.sort((a, b) => a.order_number - b.order_number).forEach(point => {
            const pointSelected = rejectState.selectedPoints.has(point.id);
            html += `
                <label class="select-item ${pointSelected ? 'selected' : ''}" 
                       style="margin-left: 20px; ${disabled ? 'opacity:0.5;pointer-events:none;' : ''}">
                    <input type="checkbox" ${pointSelected ? 'checked' : ''} 
                           ${disabled ? 'disabled' : ''}
                           onchange="togglePoint(${point.id}, this.checked)">
                    <div class="select-item-content">
                        ${escapeHtml(point.address)} <br>
                        <small style="color:#888;">${fmtWeight(point.weight)}</small>
                    </div>
                </label>
            `;
        });

        html += `</div>`;
    });

    return html;
}

function toggleRoute(routeId, checked) {
    if (checked) {
        rejectState.selectedRoutes.add(routeId);
        const route = rejectState.trip.routes.find(r => r.id === routeId);
        route.points.forEach(p => rejectState.selectedPoints.delete(p.id));
    } else {
        rejectState.selectedRoutes.delete(routeId);
    }
    renderRejectModal();
}

function togglePoint(pointId, checked) {
    if (checked) {
        rejectState.selectedPoints.add(pointId);
    } else {
        rejectState.selectedPoints.delete(pointId);
    }
    renderRejectModal();
}

function goToReasons() {
    const nothingSelected = rejectState.selectedRoutes.size === 0 && rejectState.selectedPoints.size === 0;

    if (nothingSelected) {
        if (rejectState.hadRejections) {
            submitEmptyReject();
            return;
        }
        return alert('Выберите хотя бы один маршрут или точку');
    }
    rejectState.step = 3;
    renderRejectModal();
}

async function submitEmptyReject() {
    if (!confirm('Снять все отказы и подтвердить весь рейс?')) return;

    try {
        const resp = await apiFetch(`/api/v1/me/trips/${rejectState.tripId}/confirm`, {
            method: 'POST',
        });

        if (!resp.ok) {
            const err = await resp.json();
            return alert(`Ошибка: ${err.detail || 'Неизвестная'}`);
        }

        closeRejectModal();
        if (selectionMode) {
            exitSelectionMode();
        } else {
            await loadTrips();
        }
    } catch (e) {
        alert(`Сетевая ошибка: ${e.message}`);
    }
}

function renderReasonsSelection() {
    let html = '';

    if (rejectState.selectedRoutes.size > 0) {
        html += `
            <div style="margin-bottom:16px; padding:12px; background:#f5f5f5; border-radius:8px;">
                <label style="display:block; margin-bottom:8px; font-weight:600;">
                    Причина для всех маршрутов (${rejectState.selectedRoutes.size} шт.):
                </label>
                <select class="reason-select" onchange="rejectState.commonRouteReason = this.value">
                    <option value="">-- Без причины --</option>
                    ${rejectState.reasons.route.map(r => `<option value="${r.id}">${escapeHtml(r.text)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    if (rejectState.selectedPoints.size > 0) {
        html += `
            <div style="margin-bottom:16px; padding:12px; background:#f5f5f5; border-radius:8px;">
                <label style="display:block; margin-bottom:8px; font-weight:600;">
                    Причина для всех точек (${rejectState.selectedPoints.size} шт.):
                </label>
                <select class="reason-select" onchange="rejectState.commonPointReason = this.value">
                    <option value="">-- Без причины --</option>
                    ${rejectState.reasons.point.map(r => `<option value="${r.id}">${escapeHtml(r.text)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    return html;
}

function renderTripReasons() {
    return `
        <div style="margin-bottom:12px;">
            <label>Причина отказа от всего рейса:</label>
            <select class="reason-select" id="trip-reason-select">
                <option value="">-- Без причины --</option>
                ${rejectState.reasons.trip.map(r => `<option value="${r.id}">${escapeHtml(r.text)}</option>`).join('')}
            </select>
        </div>
    `;
}

async function submitReject() {
    const payload = {
        trip_reason_id: null,
        routes: [],
        points: []
    };

    if (rejectState.type === 'trip') {
        const sel = document.getElementById('trip-reason-select');
        payload.trip_reason_id = sel.value ? parseInt(sel.value) : null;
    } else {
        const routeReasonId = rejectState.commonRouteReason
            ? parseInt(rejectState.commonRouteReason)
            : null;
        rejectState.selectedRoutes.forEach(routeId => {
            payload.routes.push({
                route_id: routeId,
                reason_id: routeReasonId
            });
        });

        const pointReasonId = rejectState.commonPointReason
            ? parseInt(rejectState.commonPointReason)
            : null;
        rejectState.selectedPoints.forEach(pointId => {
            payload.points.push({
                point_id: pointId,
                reason_id: pointReasonId
            });
        });
    }

    try {
        const resp = await apiFetch(`/api/v1/me/trips/${rejectState.tripId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json();
            return alert(`Ошибка: ${err.detail || 'Неизвестная'}`);
        }

        closeRejectModal();
        if (selectionMode) {
            exitSelectionMode();
        } else {
            await loadTrips();
        }
    } catch (e) {
        alert(`Сетевая ошибка: ${e.message}`);
    }
}

// ========== ИНИЦИАЛИЗАЦИЯ ==========

if (!window.WebApp) {
    statusEl.textContent = 'Откройте это приложение внутри MAX.';
} else {
    window.WebApp.ready();

    (async () => {
        const initData = window.WebApp.initData;
        if (!initData) {
            statusEl.textContent = 'Нет данных авторизации от MAX.';
            return;
        }

        statusEl.textContent = 'Авторизация...';

        try {
            const resp = await fetch('/api/v1/auth/max/bind', {
                method: 'POST',
                headers: { 'X-Max-InitData': initData },
            });

            if (resp.ok) {
                const data = await resp.json();
                window.__accessToken = data.access_token;
                await loadTrips();
            } else if (resp.status === 401) {
                showContactButton();
            } else {
                const err = await resp.json();
                statusEl.textContent = `Ошибка: ${err.detail || 'Неизвестная'}`;
            }
        } catch (e) {
            statusEl.textContent = `Сетевая ошибка: ${e.message}`;
        }
    })();
}

function showContactButton() {
    const initDataUnsafe = window.WebApp.initDataUnsafe || {};
    const user = initDataUnsafe.user || {};
    const userId = user.id || '—';
    const userName = [user.first_name, user.last_name].filter(Boolean).join(' ') || '—';

    const knownPhone = window.__lastContactPhone || '—';

    const copyText = `ID в MAX: ${userId}\nИмя: ${userName}\nТелефон: ${knownPhone}`;
    window.__fallbackCopyText = copyText;

    statusEl.innerHTML = `
        <p style="margin-bottom: 16px;">Вы не зарегистрированы в системе.</p>
        
        <button class="btn btn-confirm" style="width: 100%; margin-bottom: 12px;" onclick="requestContactAndBind()">
            📱 Поделиться номером телефона
        </button>

        <div style="padding: 16px; background: #f0f0f0; border-radius: 8px; text-align: left; margin-bottom: 12px;">
            <p style="font-size: 13px; color: #666; margin-bottom: 8px;">Ваши данные для логиста:</p>
            <div style="font-size: 14px; line-height: 1.5;">
                <b>Имя:</b> ${escapeHtml(userName)}<br>
                <b>ID в MAX:</b> <span style="font-family: monospace;">${userId}</span>
            </div>
        </div>

        <button class="btn btn-secondary" style="width: 100%;" onclick="copyFallbackData()">
            📋 Скопировать данные для логиста
        </button>
        
        <p style="font-size: 12px; color: #888; margin-top: 12px; text-align: center;">
            Вы можете поделиться номером автоматически или скопировать данные и переслать их логисту вручную.
        </p>
    `;
}

async function requestContactAndBind() {
    if (!window.WebApp.requestContact) {
        showFallbackScreen();
        return;
    }

    try {
        const contact = await window.WebApp.requestContact();

        if (contact.error) {
            console.warn('requestContact error:', contact.error);
            showFallbackScreen();
            return;
        }

        window.__lastContactPhone = contact.phone || '—';

        const initDataUnsafe = window.WebApp.initDataUnsafe || {};
        const userId = initDataUnsafe.user ? initDataUnsafe.user.id : null;

        if (!userId) {
            console.error('Не удалось получить userId из initData');
            showFallbackScreen();
            return;
        }

        const resp = await fetch('/api/v1/auth/max/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: contact.phone,
                auth_date: contact.authDate,
                user_id: String(userId),
                hash: contact.hash,
            }),
        });

        if (resp.ok) {
            const data = await resp.json();
            window.__accessToken = data.access_token;
            location.reload();
        } else {
            const err = await resp.json();
            if (resp.status === 401) {
                showFallbackScreen();
            } else {
                alert(`Ошибка: ${err.detail || 'Неизвестная'}`);
            }
        }
    } catch (e) {
        console.warn('requestContact exception:', e);
        showFallbackScreen();
    }
}

function showFallbackScreen() {
    const initDataUnsafe = window.WebApp.initDataUnsafe || {};
    const user = initDataUnsafe.user || {};
    const userId = user.id || null;
    const userName = [user.first_name, user.last_name].filter(Boolean).join(' ') || '—';
    const userPhone = window.__lastContactPhone || '—';

    const container = document.getElementById('trip-container');
    container.classList.remove('hidden');

    const copyText = `ID в MAX: ${userId || '—'}\nТелефон: ${userPhone}\nИмя: ${userName}`;

    container.innerHTML = `
        <div class="trip-card" style="padding: 20px;">
            <h3 style="margin-bottom: 16px;">Не удалось привязать аккаунт автоматически</h3>
            <p style="margin-bottom: 16px; color: #666;">
                Передайте эти данные логисту, чтобы он добавил вас в систему:
            </p>
            
            <div style="margin-bottom: 16px; padding: 16px; background: #f0f0f0; border-radius: 8px;">
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #888;">ID в MAX:</span>
                    <div style="font-size: 18px; font-weight: bold; font-family: monospace;">${userId || '—'}</div>
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #888;">Телефон:</span>
                    <div style="font-size: 16px; font-weight: 600;">${userPhone}</div>
                </div>
                <div>
                    <span style="font-size: 12px; color: #888;">Имя:</span>
                    <div style="font-size: 16px;">${escapeHtml(userName)}</div>
                </div>
            </div>
            
            <button class="btn btn-confirm" style="width: 100%; margin-bottom: 12px;" onclick="copyFallbackData()">
                📋 Скопировать все данные
            </button>
            
            <p style="font-size: 13px; color: #888; text-align: center; margin-top: 16px;">
                Перешлите эти данные логисту в MAX или сообщите по телефону.
            </p>
        </div>
    `;

    window.__fallbackCopyText = copyText;

    const oldBtn = statusEl.nextElementSibling;
    if (oldBtn && oldBtn.tagName === 'BUTTON') {
        oldBtn.remove();
    }
    statusEl.classList.add('hidden');
}

function copyFallbackData() {
    const text = window.__fallbackCopyText || '';
    navigator.clipboard.writeText(text).then(() => {
        alert('Данные скопированы в буфер обмена');
    }).catch(() => {
        const input = document.createElement('textarea');
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        alert('Данные скопированы в буфер обмена');
    });
}


// Выводим имя из MAX
const initDataUnsafe = window.WebApp.initDataUnsafe || {};
const user = initDataUnsafe.user || {};
const userName = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Водитель';
document.getElementById('user-name-display').textContent = userName;
document.getElementById('user-greeting').classList.remove('hidden');