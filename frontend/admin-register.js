// ==================== DOM ELEMENTS ====================
const registerForm = document.getElementById('registerForm');
const collegeNameInput = document.getElementById('collegeName');
const collegeCodeInput = document.getElementById('collegeCode');
const adminNameInput = document.getElementById('adminName');
const adminEmailInput = document.getElementById('adminEmail');
const adminPasswordInput = document.getElementById('adminPassword');
const registerBtn = document.getElementById('registerBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin register page loaded');
    
    // If already logged in, redirect
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        const userType = localStorage.getItem('user_type');
        if (userType === 'student') {
            window.location.href = 'student-dashboard.html';
        } else if (userType === 'teacher') {
            window.location.href = 'teacher-dashboard.html';
        } else if (userType === 'admin') {
            window.location.href = 'admin-dashboard.html';
        }
    }
});

// ==================== REGISTER HANDLER ====================
registerForm.addEventListener('submit', handleRegister);

async function handleRegister(event) {
    event.preventDefault();
    
    const collegeName = collegeNameInput.value;
    const collegeCode = collegeCodeInput.value.toUpperCase();
    const adminName = adminNameInput.value;
    const adminEmail = adminEmailInput.value;
    const adminPassword = adminPasswordInput.value;
    
    // Validation
    if (!collegeName || !collegeCode || !adminName || !adminEmail || !adminPassword) {
        showMessage('message', '❌ Please fill all fields', 'error');
        return;
    }
    
    if (adminPassword.length < 6) {
        showMessage('message', '❌ Password must be at least 6 characters', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    registerBtn.disabled = true;
    
    try {
        console.log('College registration attempt:', { collegeName, collegeCode });
        
        const response = await fetch(`${API_BASE_URL}/api/auth/college-register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                college_name: collegeName,
                college_code: collegeCode,
                admin_name: adminName,
                admin_email: adminEmail,
                admin_password: adminPassword
            })
        });
        
        console.log('Registration response status:', response.status);
        
        const data = await response.json();
        console.log('Registration response:', data);
        
        if (response.ok) {
            showMessage('message', '✅ College registered successfully! Redirecting to login...', 'success');
            
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } else {
            const errorMsg = data.detail || 'Registration failed';
            showMessage('message', `❌ ${errorMsg}`, 'error');
        }
    } catch (error) {
        showMessage('message', `❌ Error: ${error.message}`, 'error');
        console.error('Registration error:', error);
    } finally {
        loadingDiv.style.display = 'none';
        registerBtn.disabled = false;
    }
}