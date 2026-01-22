// API Configuration
const API_BASE = '/api/v1';

// State
let map;
let poiMarkers = [];
let routePolyline = null;
let waypointMarkers = [];
let selectedWaypoints = [];
let accessToken = localStorage.getItem('accessToken');
let refreshToken = localStorage.getItem('refreshToken');
let currentUser = null;
let searchTimeout = null;
let lastComputedRoute = null;  // Store computed route for saving

// Initialize map
function initMap() {
    // Center on Corfu
    map = L.map('map').setView([39.6243, 19.9217], 11);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Load initial POIs
    loadPOIs();
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Safe text escaping
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        // Handle rate limiting
        if (response.status === 418) {
            const data = await response.json();
            showToast(data.message, 'warning');
            return null;
        }

        // Handle auth errors
        if (response.status === 401 && refreshToken) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${accessToken}`;
                return fetch(`${API_BASE}${endpoint}`, { ...options, headers }).then(r => r.json());
            }
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Request failed');
        }

        return response.json();
    } catch (error) {
        showToast(error.message, 'error');
        return null;
    }
}

// Auth functions
function showRegister() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
}

function showLogin() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
}

async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        showToast('Please enter username and password', 'error');
        return;
    }

    const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });

    if (data) {
        accessToken = data.access_token;
        refreshToken = data.refresh_token;
        currentUser = data.user;
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        updateAuthUI();
        showToast('Login successful!', 'success');
        loadAllRoutes();
    }
}

async function register() {
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    if (!username || !email || !password) {
        showToast('Please fill all fields', 'error');
        return;
    }

    const data = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, email, password })
    });

    if (data) {
        accessToken = data.access_token;
        refreshToken = data.refresh_token;
        currentUser = data.user;
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        updateAuthUI();
        showToast('Registration successful!', 'success');
        loadAllRoutes();
    }
}

function logout() {
    accessToken = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    updateAuthUI();
    loadAllRoutes(); // Update routes display after logout
    showToast('Logged out', 'info');
}

async function refreshAccessToken() {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            localStorage.setItem('accessToken', accessToken);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }

    logout();
    return false;
}

function updateAuthUI() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const userInfo = document.getElementById('user-info');
    const usernameDisplay = document.getElementById('username-display');

    if (currentUser) {
        loginForm.classList.add('hidden');
        registerForm.classList.add('hidden');
        userInfo.classList.remove('hidden');
        usernameDisplay.textContent = currentUser.username;
    } else {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        userInfo.classList.add('hidden');
    }
}

// Check existing auth on load
async function checkAuth() {
    if (accessToken) {
        const data = await apiRequest('/auth/me');
        if (data) {
            currentUser = data;
            updateAuthUI();
        }
    }
}

// POI functions
async function loadPOIs(query = '', category = '') {
    let endpoint = '/pois?limit=100';
    if (query) endpoint += `&q=${encodeURIComponent(query)}`;
    if (category) endpoint += `&category=${encodeURIComponent(category)}`;

    const data = await apiRequest(endpoint);
    if (data && data.results) {
        displayPOIs(data.results);
    }
}

function displayPOIs(pois) {
    // Clear existing markers
    poiMarkers.forEach(marker => map.removeLayer(marker));
    poiMarkers = [];

    pois.forEach(poi => {
        // API returns location as { lat, lon } object
        const lat = poi.location?.lat || poi.lat;
        const lon = poi.location?.lon || poi.lon;

        if (!lat || !lon) return;

        const marker = L.marker([lat, lon], {
            icon: L.divIcon({
                className: 'custom-marker',
                iconSize: [12, 12],
                iconAnchor: [6, 6]
            })
        }).addTo(map);

        marker.poi = poi;

        // Create popup with safe content
        const popupContent = document.createElement('div');
        popupContent.className = 'poi-popup';

        const title = document.createElement('h3');
        title.textContent = poi.name;
        popupContent.appendChild(title);

        const category = document.createElement('p');
        category.className = 'category';
        category.textContent = poi.category || 'Unknown';
        popupContent.appendChild(category);

        if (poi.description) {
            const desc = document.createElement('p');
            desc.className = 'description';
            desc.textContent = poi.description;
            popupContent.appendChild(desc);
        }

        const btn = document.createElement('button');
        btn.textContent = 'Add to Route';
        btn.onclick = () => addToRoute(poi.id, poi.name, lat, lon);
        popupContent.appendChild(btn);

        marker.bindPopup(popupContent);
        poiMarkers.push(marker);
    });
}

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(searchPOIs, 300);
}

function searchPOIs() {
    const query = document.getElementById('search-query').value;
    const category = document.getElementById('category-filter').value;
    loadPOIs(query, category);
}

// Route functions
function addToRoute(poiId, name, lat, lon) {
    // Check if already added
    if (selectedWaypoints.find(w => w.id === poiId)) {
        showToast('POI already in route', 'warning');
        return;
    }

    selectedWaypoints.push({ id: poiId, name, lat, lon });
    updateWaypointsUI();
    updateRouteMarkers();

    // Close popup
    map.closePopup();
}

function removeFromRoute(index) {
    selectedWaypoints.splice(index, 1);
    updateWaypointsUI();
    updateRouteMarkers();

    // Clear route if less than 2 waypoints
    if (selectedWaypoints.length < 2 && routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
        document.getElementById('route-info').classList.add('hidden');
        document.getElementById('save-route-section').classList.add('hidden');
    }
}

function updateWaypointsUI() {
    const container = document.getElementById('route-waypoints');
    const computeBtn = document.getElementById('compute-btn');

    if (selectedWaypoints.length === 0) {
        container.textContent = '';
        const msg = document.createElement('p');
        msg.className = 'empty-message';
        msg.textContent = 'Click POIs on map to add waypoints';
        container.appendChild(msg);
        computeBtn.disabled = true;
        return;
    }

    computeBtn.disabled = selectedWaypoints.length < 2;
    container.textContent = '';

    selectedWaypoints.forEach((wp, i) => {
        const item = document.createElement('div');
        item.className = 'waypoint-item';

        const num = document.createElement('span');
        num.className = 'number';
        num.textContent = i + 1;

        const name = document.createElement('span');
        name.className = 'name';
        name.textContent = wp.name;

        const remove = document.createElement('span');
        remove.className = 'remove';
        remove.textContent = '\u00D7';
        remove.onclick = () => removeFromRoute(i);

        item.appendChild(num);
        item.appendChild(name);
        item.appendChild(remove);
        container.appendChild(item);
    });
}

function updateRouteMarkers() {
    // Clear existing waypoint markers
    waypointMarkers.forEach(m => map.removeLayer(m));
    waypointMarkers = [];

    // Add numbered markers for waypoints
    selectedWaypoints.forEach((wp, i) => {
        const marker = L.marker([wp.lat, wp.lon], {
            icon: L.divIcon({
                className: 'waypoint-marker',
                html: String(i + 1),
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            })
        }).addTo(map);
        waypointMarkers.push(marker);
    });

    // Fit bounds if we have waypoints
    if (selectedWaypoints.length > 0) {
        const bounds = L.latLngBounds(selectedWaypoints.map(wp => [wp.lat, wp.lon]));
        map.fitBounds(bounds, { padding: [50, 50] });
    }
}

async function computeRoute() {
    if (selectedWaypoints.length < 2) {
        showToast('Add at least 2 waypoints', 'error');
        return;
    }

    // Build locations array with lat/lon coordinates
    const locations = selectedWaypoints.map(wp => ({
        lat: wp.lat,
        lon: wp.lon
    }));

    showToast('Computing route...', 'info');

    const data = await apiRequest('/routes/compute', {
        method: 'POST',
        body: JSON.stringify({ locations })
    });

    if (data) {
        displayRoute(data);
        showToast('Route computed!', 'success');
    }
}

function displayRoute(routeData) {
    // Store for saving
    lastComputedRoute = routeData;

    // Remove existing route
    if (routePolyline) {
        map.removeLayer(routePolyline);
    }

    // Draw route polyline
    if (routeData.geometry && routeData.geometry.coordinates) {
        const coords = routeData.geometry.coordinates.map(c => [c[1], c[0]]);
        routePolyline = L.polyline(coords, {
            color: '#2563eb',
            weight: 5,
            opacity: 0.8
        }).addTo(map);

        map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });
    }

    // Show route info - handle both old and new field names
    const routeInfo = document.getElementById('route-info');
    const distance = routeData.distanceMeters || routeData.distance || 0;
    const duration = routeData.durationMillis ? routeData.durationMillis / 1000 : (routeData.time || 0);
    document.getElementById('route-distance').textContent = formatDistance(distance);
    document.getElementById('route-duration').textContent = formatDuration(duration);
    routeInfo.classList.remove('hidden');

    // Show save section if logged in
    if (currentUser) {
        document.getElementById('save-route-section').classList.remove('hidden');
    }
}

function formatDistance(meters) {
    if (meters >= 1000) {
        return (meters / 1000).toFixed(1) + ' km';
    }
    return Math.round(meters) + ' m';
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
}

function clearRoute() {
    selectedWaypoints = [];
    lastComputedRoute = null;
    updateWaypointsUI();
    updateRouteMarkers();

    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }

    document.getElementById('route-info').classList.add('hidden');
    document.getElementById('save-route-section').classList.add('hidden');
    document.getElementById('route-name').value = '';
    document.getElementById('route-public').checked = false;
}

async function saveRoute() {
    const name = document.getElementById('route-name').value;
    const isPublic = document.getElementById('route-public').checked;

    if (!name) {
        showToast('Please enter a route name', 'error');
        return;
    }

    if (!currentUser) {
        showToast('Please login to save routes', 'error');
        return;
    }

    if (!lastComputedRoute || !lastComputedRoute.geometry) {
        showToast('Please compute a route first', 'error');
        return;
    }

    // Use poiSequence (array of POI IDs) as per API spec
    const poiSequence = selectedWaypoints.map(wp => wp.id);

    const data = await apiRequest('/routes', {
        method: 'POST',
        body: JSON.stringify({
            name,
            public: isPublic,
            poiSequence,
            geometry: lastComputedRoute.geometry,
            distanceMeters: lastComputedRoute.distanceMeters,
            durationMillis: lastComputedRoute.durationMillis,
            vehicle: lastComputedRoute.vehicle || 'car'
        })
    });

    if (data) {
        showToast('Route saved!', 'success');
        loadAllRoutes();
        document.getElementById('route-name').value = '';
    }
}

// Load current user's routes (requires login)
async function loadMyRoutes() {
    const container = document.getElementById('my-routes-list');
    const section = document.getElementById('my-routes-section');
    container.textContent = '';

    if (!currentUser) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    const data = await apiRequest(`/routes?ownerId=${currentUser.id}`);

    if (data && data.results && data.results.length > 0) {
        data.results.forEach(route => {
            const card = createRouteCard(route, true); // true = is owner
            container.appendChild(card);
        });
    } else {
        const msg = document.createElement('p');
        msg.className = 'empty-message';
        msg.textContent = 'No saved routes';
        container.appendChild(msg);
    }
}

// Load public routes from other users
async function loadPublicRoutes() {
    const container = document.getElementById('public-routes-list');
    container.textContent = '';

    const data = await apiRequest('/routes?public=true');

    if (data && data.results && data.results.length > 0) {
        // Filter out current user's routes if logged in
        const otherUsersRoutes = currentUser
            ? data.results.filter(r => r.ownerId !== currentUser.id)
            : data.results;

        if (otherUsersRoutes.length > 0) {
            otherUsersRoutes.forEach(route => {
                const card = createRouteCard(route, false); // false = not owner
                container.appendChild(card);
            });
        } else {
            const msg = document.createElement('p');
            msg.className = 'empty-message';
            msg.textContent = 'No public routes from other users';
            container.appendChild(msg);
        }
    } else {
        const msg = document.createElement('p');
        msg.className = 'empty-message';
        msg.textContent = 'No public routes';
        container.appendChild(msg);
    }
}

// Create a route card element
function createRouteCard(route, isOwner) {
    const card = document.createElement('div');
    card.className = 'route-card';

    const cardHeader = document.createElement('div');
    cardHeader.className = 'route-card-header';
    cardHeader.onclick = () => loadRoute(route.id);
    cardHeader.style.cursor = 'pointer';

    const title = document.createElement('h4');
    title.textContent = route.name;

    const distance = route.distanceMeters || route.distance;
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = `${distance ? formatDistance(distance) : 'Unknown'} | ${route.public ? 'Public' : 'Private'}`;

    cardHeader.appendChild(title);
    cardHeader.appendChild(meta);
    card.appendChild(cardHeader);

    // Add edit/delete buttons for owner's routes
    if (isOwner) {
        const actions = document.createElement('div');
        actions.className = 'route-actions-btns';

        const editBtn = document.createElement('button');
        editBtn.className = 'btn-small btn-edit';
        editBtn.textContent = 'Edit';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            editRoute(route);
        };

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-small btn-delete';
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteRoute(route.id, route.name);
        };

        actions.appendChild(editBtn);
        actions.appendChild(deleteBtn);
        card.appendChild(actions);
    }

    return card;
}

// Edit route dialog
function editRoute(route) {
    const newName = prompt('Enter new route name:', route.name);
    if (newName === null) return; // Cancelled

    const makePublic = confirm('Make this route public?');

    updateRoute(route.id, { name: newName, public: makePublic });
}

// Update route via API
async function updateRoute(routeId, updates) {
    const data = await apiRequest(`/routes/${routeId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
    });

    if (data) {
        showToast('Route updated!', 'success');
        loadMyRoutes();
        loadPublicRoutes();
    }
}

// Delete route
async function deleteRoute(routeId, routeName) {
    if (!confirm(`Delete route "${routeName}"?`)) return;

    const response = await fetch(`${API_BASE}/routes/${routeId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });

    if (response.ok) {
        showToast('Route deleted!', 'success');
        loadMyRoutes();
        loadPublicRoutes();
    } else {
        showToast('Failed to delete route', 'error');
    }
}

// Load all routes (both sections)
function loadAllRoutes() {
    loadMyRoutes();
    loadPublicRoutes();
}

async function loadRoute(routeId) {
    const data = await apiRequest(`/routes/${routeId}`);

    if (data) {
        // Clear current route
        clearRoute();

        // Load waypoints - API returns poiSequence with {poiId, name}
        const poiSeq = data.poiSequence || data.poi_sequence || [];
        if (poiSeq.length > 0) {
            // Fetch POI details to get coordinates
            for (const item of poiSeq) {
                const poiId = item.poiId || item.id;
                if (poiId) {
                    const poiData = await apiRequest(`/pois/${poiId}`);
                    if (poiData) {
                        const lat = poiData.location?.lat || poiData.lat;
                        const lon = poiData.location?.lon || poiData.lon;
                        selectedWaypoints.push({
                            id: poiId,
                            name: item.name || poiData.name,
                            lat: lat,
                            lon: lon
                        });
                    }
                }
            }
            updateWaypointsUI();
            updateRouteMarkers();
        }

        // Display route if geometry exists
        if (data.geometry) {
            displayRoute(data);
        }

        showToast(`Loaded: ${data.name}`, 'success');
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await checkAuth();
    loadAllRoutes(); // Load routes for everyone (My Routes hidden if not logged in)
});
