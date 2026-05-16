// Add Website Form
document.getElementById('addWebsiteForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    let formConfig;
    try {
        const raw = document.getElementById('form_config').value.trim();
        formConfig = raw ? JSON.parse(raw) : {};
    } catch {
        alert('Invalid JSON in Form Configuration');
        return;
    }

    const payload = {
        name: document.getElementById('name').value,
        url: document.getElementById('url').value,
        form_config: formConfig,
        requires_email_otp: document.getElementById('requires_email_otp').checked,
        requires_mobile_otp: document.getElementById('requires_mobile_otp').checked,
        max_registrations_per_day: parseInt(document.getElementById('max_daily').value) || 100,
    };

    try {
        const resp = await fetch('/api/websites/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (resp.ok) {
            window.location.reload();
        } else {
            const err = await resp.json();
            alert('Error: ' + (err.detail || 'Failed to add website'));
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
});

// Trigger Registration
function triggerRegistration(websiteId) {
    document.getElementById('registerSection').style.display = 'block';
    document.getElementById('reg_website_id').value = websiteId;
    document.getElementById('registerResult').style.display = 'none';
    document.getElementById('registerSection').scrollIntoView({ behavior: 'smooth' });
}

function closeRegister() {
    document.getElementById('registerSection').style.display = 'none';
}

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const websiteId = parseInt(document.getElementById('reg_website_id').value);
    const count = parseInt(document.getElementById('reg_count').value) || 1;

    const resultBox = document.getElementById('registerResult');
    resultBox.style.display = 'block';
    resultBox.textContent = 'Queuing registrations...';

    try {
        const resp = await fetch('/api/registrations/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ website_id: websiteId, count: count }),
        });

        const data = await resp.json();

        if (resp.ok) {
            resultBox.textContent = JSON.stringify(data, null, 2);
            setTimeout(() => window.location.reload(), 5000);
        } else {
            resultBox.textContent = 'Error: ' + (data.detail || JSON.stringify(data));
        }
    } catch (err) {
        resultBox.textContent = 'Network error: ' + err.message;
    }
});

// Delete Website
async function deleteWebsite(websiteId) {
    if (!confirm('Are you sure you want to delete this website?')) return;

    try {
        const resp = await fetch(`/api/websites/${websiteId}`, { method: 'DELETE' });
        if (resp.ok) {
            window.location.reload();
        } else {
            const err = await resp.json();
            alert('Error: ' + (err.detail || 'Failed to delete'));
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

// Auto-refresh registrations table every 10 seconds
setInterval(async () => {
    try {
        const resp = await fetch('/api/registrations/?limit=50');
        if (!resp.ok) return;
        const data = await resp.json();

        const tbody = document.getElementById('registrationsTable');
        if (!tbody || data.length === 0) return;

        tbody.innerHTML = data.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.website_id}</td>
                <td><span class="badge badge-${r.status}">${r.status}</span></td>
                <td>${r.email_used || '-'}</td>
                <td>${r.phone_used || '-'}</td>
                <td>${r.email_otp_verified ? 'Yes' : 'No'}</td>
                <td>${r.mobile_otp_verified ? 'Yes' : 'No'}</td>
                <td class="error-cell">${(r.error_message || '-').substring(0, 50)}</td>
                <td>${new Date(r.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch {
        // Silently ignore polling errors
    }
}, 10000);
