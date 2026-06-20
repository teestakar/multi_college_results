// ==================== DOM ELEMENTS ====================
const teacherRegisterForm = document.getElementById('teacherRegisterForm');
const teacherIdInput = document.getElementById('teacherId');
const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Teacher register page loaded');
    
    // Check if logged in as admin teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
});

// ==================== FORM SUBMIT ====================
teacherRegisterForm.addEventListener('submit', handleRegister);

async function handleRegister(event) {
    event.preventDefault();
    
    const teacherId = teacherIdInput.value.trim();
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    
    // Validate
    if (!teacherId || !name || !email || !password) {
        showMessage('❌ Please fill all fields', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    submitBtn.disabled = true;
    
    try {
        console.log('Teacher register attempt:', { teacherId, name, email });
        
        const response = await apiCall('/api/auth/teacher/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                teacher_id: teacherId,
                name: name,
                email: email,
                password: password
            })
        });
        
        if (!response || !response.ok) {
            const error = await response.json();
            showMessage(`❌ ${error.detail || 'Registration failed'}`, 'error');
            loadingDiv.style.display = 'none';
            submitBtn.disabled = false;
            return;
        }
        
        const data = await response.json();
        console.log('Registration response:', data);
        
        showMessage(`✅ ${data.message}`, 'success');

        loadingDiv.style.display = 'none';
        submitBtn.disabled = false;
        
        // Clear form
        teacherRegisterForm.reset();
        
    

        // Auto-focus first input
        teacherIdInput.focus();
        
    } catch (error) {
        console.error('Registration error:', error);
        showMessage(`❌ Error: ${error.message}`, 'error');
        loadingDiv.style.display = 'none';
        submitBtn.disabled = false;
    }
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}