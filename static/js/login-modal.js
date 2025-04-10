document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            fetch(this.action, {
                method: 'POST',
                body: new FormData(this),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // If next URL is provided, redirect there, otherwise reload page
                    if (data.next) {
                        window.location.href = data.next;
                    } else {
                        window.location.reload();
                    }
                } else {
                    // Show error message
                    document.getElementById('loginError').classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('loginError').classList.remove('d-none');
            });
        });
    }
});