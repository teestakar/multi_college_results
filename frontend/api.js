// ==================== CONFIGURATION ====================
const API_BASE_URL = 'http://localhost:8000';

// ==================== API CALL WITH AUTO TOKEN REFRESH ====================

async function apiCall(endpoint, options = {}) {
    try {

        const headers = {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            ...options.headers
        };

        // Don't set Content-Type for FormData
        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (!response.ok) {

            const error = await response.json();

            let errorMessage = "An error occurred";

            if (error.detail) {
                if (typeof error.detail === "object") {

                    errorMessage = error.detail.message || "Unknown error";

                    if (error.detail.details) {
                        errorMessage += `\n\n${error.detail.details}`;
                    }

                } else {
                    errorMessage = error.detail;
                }
            }

            // Token expired
            if (response.status === 401) {

                const code = error.detail?.code;

                if (code === "TOKEN_EXPIRED") {

                    const refreshed = await refreshAccessToken();

                    if (refreshed) {
                        return apiCall(endpoint, options);
                    }
                }

                localStorage.clear();
                window.location.href = "index.html";
                return;
            }

            showMessage(errorMessage, "error");
            throw new Error(errorMessage);
        }

        return await response.json();

    } catch (error) {
        console.error("API Error:", error);

        showMessage(`Error: ${error.message}`, "error");

        throw error;
    }
}

// ==================== HELPER FUNCTION ====================

async function refreshAccessToken() {
    //"""Refresh the access token using refresh token"""
    console.log("REFRESH CALLED");
    try {
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
            return false;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
            return false;
        }
        
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        return true;
        
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

// ==================== HELPER: SHOW MESSAGE ====================
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    
    if (!messageDiv) return;
    
    // Convert object to string if needed
    let displayText = text;
    if (typeof text === 'object') {
        displayText = text.message || JSON.stringify(text);
    }
    
    messageDiv.textContent = displayText;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}

// ==================== HELPER: LOGOUT ====================
function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}