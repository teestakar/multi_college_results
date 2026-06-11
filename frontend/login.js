// ==================== CONFIGURATION ====================
const API_BASE_URL = 'http://localhost:8000';  // Backend URL
const LOGIN_ENDPOINT = `${API_BASE_URL}/api/auth/login`;

// ==================== DOM ELEMENTS ====================
const loginForm = document.getElementById('loginForm');
const collegeSelect = document.getElementById('college');
const rollNoInput = document.getElementById('rollNo');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== EVENT LISTENERS ====================
loginForm.addEventListener('submit', handleLogin);

// ==================== LOGIN HANDLER ====================
async function handleLogin(event) {
    event.preventDefault();  // Stop form from refreshing page
    
    // Get form values
    const collegeCode = collegeSelect.value;
    const rollNo = rollNoInput.value;
    const password = passwordInput.value;
    
    // Validate inputs
    if (!collegeCode || !rollNo || !password) {
        showMessage('Please fill all fields', 'error');
        return;
    }
    
    // Show loading state
    loadingDiv.style.display = 'block';
    loginBtn.disabled = true;
    messageDiv.style.display = 'none';
    
    try {
        // Send login request to backend
        const response = await fetch(LOGIN_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                college_code: collegeCode,
                roll_no: rollNo,
                password: password
            })
        });
        
        const data = await response.json();
        
        // Check if login was successful
        if (response.ok) {
            // Save tokens to localStorage
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            localStorage.setItem('user_roll_no', rollNo);
            localStorage.setItem('college_code', collegeCode);
            localStorage.setItem('user_name', data.user_name);

            // Show success message
            showMessage('✅ Login successful! Redirecting...', 'success');
            
            // Redirect to dashboard after 1.5 seconds
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1500);
        } else {
            // Show error message from backend
            const errorMsg = data.detail || 'Login failed. Please try again.';
            showMessage(`❌ ${errorMsg}`, 'error');
        }
    } catch (error) {
        // Network error or JSON parsing error
        showMessage(`❌ Error: ${error.message}`, 'error');
        console.error('Login error:', error);
    } finally {
        // Hide loading state
        loadingDiv.style.display = 'none';
        loginBtn.disabled = false;
    }
}

// ==================== HELPER FUNCTION ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
}

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    // Optional: Check if already logged in, redirect to dashboard
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        // Uncomment this after we create dashboard.html
        // window.location.href = 'dashboard.html';
    }
});