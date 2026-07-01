document.addEventListener('DOMContentLoaded', function () {
    const token = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');

    // ================= AUTH GUARD =================
    if (!token) {
        window.location.href = 'admin-dashboard.html';
        return;
    }

    if (userType !== 'admin') {
        window.location.href = 'teacher-login.html';
        return;
    }

    // ================= INIT FORM =================
    initializeForm();
});

// ================= FORM LOGIC =================
function initializeForm() {
    const form = document.getElementById('studentRegisterForm');
    const messageDiv = document.getElementById('message');
    const submitBtn = document.getElementById('submitBtn');
    const loadingDiv = document.getElementById('loading');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        messageDiv.className = "message";
        messageDiv.style.display = "none";

        submitBtn.disabled = true;
        loadingDiv.style.display = "block";

        const payload = {
            roll_no: document.getElementById('rollNo').value,
            name: document.getElementById('name').value,
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            degree: document.getElementById('degree').value,
            branch: document.getElementById('branch').value,
            year: document.getElementById('year').value
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/admin/register-student`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Registration failed");
            }

            messageDiv.className = "message success";
            messageDiv.innerText = "Student registered successfully ✔";
            messageDiv.style.display = "block";

            form.reset();

        } catch (error) {
            messageDiv.className = "message error";
            messageDiv.innerText = error.message;
            messageDiv.style.display = "block";

        } finally {
            submitBtn.disabled = false;
            loadingDiv.style.display = "none";
        }
    });
}