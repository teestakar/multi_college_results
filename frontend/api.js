// ==================== CONFIGURATION ====================
const API_BASE_URL = 'http://localhost:8000';

// ==================== API CALL WITH AUTO TOKEN REFRESH ====================
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Setup headers
    if (!options.headers) {
        options.headers = {};
    }
    
    // Add auth header if token exists
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        options.headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    // Make request
    let response = await fetch(url, options);
    
    // If 401 (token expired), try to refresh
    if (response.status === 401) {
        console.log('Token expired, attempting refresh...');
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            // Retry with new token
            const newAccessToken = localStorage.getItem('access_token');
            options.headers['Authorization'] = `Bearer ${newAccessToken}`;
            response = await fetch(url, options);
        } else {
            // Refresh failed, go to login
            console.log('Refresh failed, redirecting to login');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = 'index.html';
            return null;
        }
    }
    
    return response;
}

// ==================== REFRESH ACCESS TOKEN ====================
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        return false;  // No refresh token, go to login
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh_token: refreshToken
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            console.log('Token refreshed successfully');
            return true;
        } else {
            console.log('Refresh failed');
            return false;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        return false;
    }
}

// ==================== HELPER: SHOW MESSAGE ====================
function showMessage(elementId, text, type) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = text;
    element.className = `message ${type}`;
    element.style.display = 'block';
    
    // Auto-hide error messages after 5 seconds
    if (type === 'error') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// ==================== HELPER: LOGOUT ====================
function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}