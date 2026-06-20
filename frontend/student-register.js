// ==================== DOM ELEMENTS ====================
const studentRegisterForm = document.getElementById('studentRegisterForm');
const rollNoInput = document.getElementById('rollNo');
const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const degreeInput = document.getElementById('degree');
const branchInput = document.getElementById('branch');
const yearSelect = document.getElementById('year');
const submitBtn = document.getElementById('submitBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Student register page loaded');
    
    // Check if logged in as admin teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
});

// ==================== FORM SUBMIT ====================
studentRegisterForm.addEventListener('submit', handleRegister);

async function handleRegister(event) {
    event.preventDefault();
    
    const rollNo = rollNoInput.value.trim();
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    const degree = degreeInput.value.trim();
    const branch = branchInput.value.trim();
    const year = parseInt(yearSelect.value);
    
    // Validate
    if (!rollNo || !name || !email || !password || !degree || !branch || !year) {
        showMessage('❌ Please fill all fields', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    submitBtn.disabled = true;
    
    try {
        console.log('Student register attempt:', { rollNo, name, email, degree, branch, year });
        
        const response = await apiCall('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                roll_no: rollNo,
                name: name,
                email: email,
                password: password,
                degree: degree,
                branch: branch,
                year: year
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
        studentRegisterForm.reset();
        
        

        // Auto-focus first input
        rollNoInput.focus();
        
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