// ==================== DOM ELEMENTS ====================
const loginForm = document.getElementById('loginForm');
const collegeSelect = document.getElementById('college');
const rollNoInput = document.getElementById('rollNo');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    // If already logged in as student, go to dashboard
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (accessToken && userType === 'student') {
        window.location.href = 'student-dashboard.html';
    }
    
    // Load colleges (hardcoded for now)
    loadColleges();
});

// ==================== LOAD COLLEGES ====================
// ==================== LOAD COLLEGES FROM DATABASE ====================
async function loadColleges() {
    try {
        // Fetch colleges from backend
        const response = await fetch(`${API_BASE_URL}/api/auth/colleges`);
        
        if (!response.ok) {
            throw new Error('Failed to load colleges');
        }
        
        const colleges = await response.json();
        
        collegeSelect.innerHTML = '<option value="">-- Select College --</option>';
        
        if (!colleges || colleges.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No colleges registered yet';
            option.disabled = true;
            collegeSelect.appendChild(option);
            return;
        }
        
        // Add each college as option
        colleges.forEach(college => {
            const option = document.createElement('option');
            option.value = college.code;
            option.textContent = college.name;
            collegeSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading colleges:', error);
        showMessage('message', '⚠️ Could not load colleges. Please refresh.', 'error');
    }
}

// ==================== LOGIN HANDLER ====================
loginForm.addEventListener('submit', handleLogin);

async function handleLogin(event) {
    event.preventDefault();
    
    const collegeCode = collegeSelect.value;
    const rollNo = rollNoInput.value;
    const password = passwordInput.value;
    
    if (!collegeCode || !rollNo || !password) {
        showMessage('message', '❌ Please fill all fields', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    loginBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
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
        
        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            localStorage.setItem('user_roll_no', rollNo);
            localStorage.setItem('user_name', data.user_name);
            localStorage.setItem('college_code', collegeCode);
            localStorage.setItem('user_type', 'student');
            
            showMessage('message', '✅ Login successful! Redirecting...', 'success');
            
            setTimeout(() => {
                window.location.href = 'student-dashboard.html';
            }, 1500);
        } else {
            const errorMsg = data.detail || 'Login failed';
            showMessage('message', `❌ ${errorMsg}`, 'error');
        }
    } catch (error) {
        showMessage('message', `❌ Error: ${error.message}`, 'error');
        console.error('Login error:', error);
    } finally {
        loadingDiv.style.display = 'none';
        loginBtn.disabled = false;
    }
}