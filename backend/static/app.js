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

// ========== РЕНДЕР ==========

function renderTrip(trip) {
    const routeRows = trip.routes
        .sort((a, b) => a.order_number - b.order_number)
        .map(route => {
            const points = route.points
                .sort((a, b) => a.order_number - b.order_number)
                .map(point => `
                    <div class="point-row">
                        <span class="point-icon">${POINT_ICONS[point.status] || '—'}</span>
                        <div class="point-info">
                            <div class="point-address">${escapeHtml(point.address)}</div>
                            <div class="point-meta">${fmtWeight(point.weight)}</div>
                            ${point.rejection_reason ? `<div class="point-reason">${escapeHtml(point.rejection_reason)}</div>` : ''}
                        </div>
                    </div>
                `).join('');

            return `
                <div class="route-block">
                    <div class="route-header">
                        <span>
                            <span class="icon">${ROUTE_ICONS[route.status] || '—'}</span>
                            ${escapeHtml(route.name || `Маршрут #${route.order_number}`)}
                        </span>
                        <span>${route.points.length} точек</span>
                    </div>
                    ${points}
                </div>
            `;
        }).join('');

    const actions = trip.is_actionable ? `
        <div class="actions">
            <button class="btn btn-confirm" onclick="confirmTrip(${trip.id})">✅ Подтвердить всё</button>
            <button class="btn btn-reject" onclick="rejectTrip(${trip.id})">🚫 Отказаться</button>
        </div>
    ` : '';

    const dateStr = new Date(trip.date).toLocaleDateString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });

    return `
        <div class="trip-card">
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

    // Меняем текст и состояние кнопки в зависимости от выбранной даты
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
    loadTrips(); // Загружаем завтра, кнопка сама скроется/сменит текст
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
    routeReasons: {},
    pointReasons: {},
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
    const preRouteReasons = {};
    const prePointReasons = {};

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
        routeReasons: preRouteReasons,
        pointReasons: prePointReasons,
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
        await loadTrips();
    } catch (e) {
        alert(`Сетевая ошибка: ${e.message}`);
    }
}

function renderReasonsSelection() {
    let html = '';

    rejectState.selectedRoutes.forEach(routeId => {
        const route = rejectState.trip.routes.find(r => r.id === routeId);
        html += `
            <div style="margin-bottom:12px;">
                <label>Причина для маршрута "${escapeHtml(route.name || '#' + route.order_number)}":</label>
                <select class="reason-select" onchange="rejectState.routeReasons[${routeId}] = this.value">
                    <option value="">-- Без причины --</option>
                    ${rejectState.reasons.route.map(r => `<option value="${r.id}">${escapeHtml(r.text)}</option>`).join('')}
                </select>
            </div>
        `;
    });

    rejectState.selectedPoints.forEach(pointId => {
        let point = null;
        for (const r of rejectState.trip.routes) {
            const p = r.points.find(p => p.id === pointId);
            if (p) { point = p; break; }
        }
        if (!point) return;

        html += `
            <div style="margin-bottom:12px;">
                <label>Причина для точки "${escapeHtml(point.address)}":</label>
                <select class="reason-select" onchange="rejectState.pointReasons[${pointId}] = this.value">
                    <option value="">-- Без причины --</option>
                    ${rejectState.reasons.point.map(r => `<option value="${r.id}">${escapeHtml(r.text)}</option>`).join('')}
                </select>
            </div>
        `;
    });

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
        rejectState.selectedRoutes.forEach(routeId => {
            const reasonId = rejectState.routeReasons[routeId];
            payload.routes.push({
                route_id: routeId,
                reason_id: reasonId ? parseInt(reasonId) : null
            });
        });
        rejectState.selectedPoints.forEach(pointId => {
            const reasonId = rejectState.pointReasons[pointId];
            payload.points.push({
                point_id: pointId,
                reason_id: reasonId ? parseInt(reasonId) : null
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
        await loadTrips();
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
            } else {
                const err = await resp.json();
                statusEl.textContent = `Ошибка: ${err.detail || 'Неизвестная'}`;
            }
        } catch (e) {
            statusEl.textContent = `Сетевая ошибка: ${e.message}`;
        }
    })();
}