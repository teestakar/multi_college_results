// ==================== DOM ELEMENTS ====================
const teacherLoginForm = document.getElementById('teacherLoginForm');
const teacherIdInput = document.getElementById('teacherId');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Teacher login page loaded');
    
    // If already logged in as teacher, go to dashboard
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (accessToken && userType === 'teacher') {
        console.log('Already logged in as teacher, redirecting...');
        window.location.href = 'teacher-dashboard.html';
    }
});

// ==================== LOGIN HANDLER ====================
teacherLoginForm.addEventListener('submit', handleTeacherLogin);

async function handleTeacherLogin(event) {
    event.preventDefault();
    
    const teacherId = teacherIdInput.value;
    const password = passwordInput.value;
    
    if (!teacherId || !password) {
        showMessage('❌ Please fill all fields', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    loginBtn.disabled = true;
    
    try {
        console.log('Teacher login attempt:', { teacherId });
        
        const response = await fetch(`${API_BASE_URL}/api/auth/teacher/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                teacher_id: teacherId,
                password: password
            })
        });
        
        console.log('Teacher login response status:', response.status);
        
        const data = await response.json();
        console.log('Teacher login response:', data);
        
        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            localStorage.setItem('user_name', data.user_name);
            localStorage.setItem('teacher_id', teacherId);
            localStorage.setItem('user_type', data.user_type); // "teacher" or "admin"

            showMessage('✅ Login successful! Redirecting...', 'success');

            setTimeout(async () => {
                try {
                    const profile = await apiCall("/api/auth/teacher/me");
                    console.log("PROFILE:", profile);

                    localStorage.setItem("user_type", profile.role);

                    if (profile.role === "admin") {
                        window.location.href = "admin-dashboard.html";
                    } else {
                        window.location.href = "teacher-dashboard.html";
                    }

                } catch (err) {
                    console.error(err);
                    showMessage("❌ Login failed. Try again.", "error");
                }
            }, 1500);

        } else {
            const errorMsg =
                data.detail?.message ||
                data.detail ||
                'Login failed';

            showMessage(`❌ ${errorMsg}`, 'error');
        }
    } catch (error) {
        showMessage(`❌ Error: ${error.message}`, 'error');
        console.error('Teacher login error:', error);
    } finally {
        loadingDiv.style.display = 'none';
        loginBtn.disabled = false;
    }
}